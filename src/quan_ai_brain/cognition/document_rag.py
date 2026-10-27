"""Document RAG — Sprint 6-GOP hạng mục (1).

Áp dụng Module 3 Bài 4/5 (RAG Pipeline) cho trợ lý:
  Ingestion → Chunking (size+overlap, metadata nguồn/version/ngày/loại) →
  Embedding (BGE-M3 có sẵn, fallback keyword khi Ollama chết) →
  Retrieval (top_k + threshold, dưới ngưỡng trả "không tìm thấy bằng chứng").

An toàn:
- KHÔNG ingest .env/credentials/DB — chỉ file .txt/.md trong kho chỉ định.
- Index SQLite riêng data/document_index.db — KHÔNG đụng brain.db/memory.
- Fail-closed: embedding lỗi → keyword scoring; mọi lỗi retrieval → [].
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quan_ai_brain.cognition.embedding import BGEEmbeddingService

_DEFAULT_CHUNK_SIZE = 700      # ký tự — tiếng Việt ~120-150 từ
_DEFAULT_OVERLAP = 120         # giữ ngữ cảnh biên chunk
_DEFAULT_TOP_K = 4
_DEFAULT_THRESHOLD = 0.45      # hybrid score tối thiểu để coi là có bằng chứng

_DOC_EXTS = {".txt", ".md"}
_FORBIDDEN_NAMES = {".env", "credentials", "secret", "token"}


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    section: str
    version: str
    content: str
    source_path: str
    score: float = 0.0
    score_reason: str = ""


@dataclass
class RetrievalResult:
    query: str
    chunks: list[Chunk] = field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def has_evidence(self) -> bool:
        return bool(self.chunks)

    def render_evidence_block(self) -> str:
        """Block đưa vào system prompt — có nguồn [tài liệu §mục]."""
        if not self.chunks:
            return ""
        parts = [
            "[EVIDENCE TÀI LIỆU NỘI BỘ — chỉ trả lời dựa trên các đoạn dưới đây; "
            "mỗi khẳng định phải dẫn nguồn [tài liệu §mục]; nếu không đủ căn cứ "
            "phải nói rõ 'chưa tìm thấy căn cứ trong kho tài liệu']"
        ]
        for c in self.chunks:
            parts.append(
                f"— [{c.doc_title} §{c.section} | v{c.version}]\n{c.content}"
            )
        return "\n\n".join(parts)


class DocumentRAG:
    """RAG pipeline cho tài liệu nội bộ — index riêng, read-only retrieval."""

    def __init__(
        self,
        workspace: str | Path,
        embedding_service: BGEEmbeddingService | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self.workspace = Path(workspace)
        self.db_path = Path(db_path) if db_path else self.workspace / "data" / "document_index.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_service = embedding_service
        self._ensure_schema()

    # ---------------- schema ----------------

    def _ensure_schema(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS doc_chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                doc_title TEXT NOT NULL,
                section TEXT NOT NULL,
                version TEXT NOT NULL,
                content TEXT NOT NULL,
                source_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                indexed_at_utc TEXT NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc ON doc_chunks(doc_id)"
        )
        conn.commit()
        conn.close()

    def count_chunks(self) -> int:
        conn = sqlite3.connect(self.db_path)
        n = conn.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()[0]
        conn.close()
        return n

    # ---------------- ingestion + chunking ----------------

    def _is_forbidden(self, path: Path) -> bool:
        low = path.name.lower()
        if any(f in low for f in _FORBIDDEN_NAMES):
            return True
        return path.suffix.lower() not in _DOC_EXTS

    def ingest_document(
        self,
        path: str | Path,
        *,
        version: str = "1.0",
        doc_type: str = "SOP",
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        overlap: int = _DEFAULT_OVERLAP,
    ) -> int:
        """Chunk 1 tài liệu + lưu index. Trả số chunk đã index.

        Chunk theo PARAGRAPH trước (giữ ngữ cảnh), gộp tới chunk_size,
        overlap = lặp lại cuối chunk trước. Metadata: tên file = doc_title,
        section = heading markdown nếu có.
        """
        p = Path(path)
        if self._is_forbidden(p):
            raise ValueError(f"Tài liệu bị cấm ingest (secret/sai định dạng): {p.name}")
        text = p.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            return 0

        doc_id = hashlib.sha1(str(p).encode()).hexdigest()[:12]
        doc_title = p.stem

        # Xoá chunk cũ của doc này (re-index idempotent)
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM doc_chunks WHERE doc_id = ?", (doc_id,))

        # Chunking: split paragraph, gộp tới chunk_size với overlap
        paragraphs = [s.strip() for s in re.split(r"\n\s*\n", text) if s.strip()]
        chunks: list[tuple[str, str]] = []  # (section, content)
        cur_section = "Mở đầu"
        buf = ""
        for para in paragraphs:
            m = re.match(r"^#{1,3}\s+(.+)$", para)
            if m:
                # flush buffer trước khi đổi section
                if buf.strip():
                    chunks.append((cur_section, buf.strip()))
                cur_section = m.group(1).strip()
                buf = ""
            if len(buf) + len(para) + 2 <= chunk_size or not buf:
                buf = (buf + "\n\n" + para).strip()
            else:
                chunks.append((cur_section, buf.strip()))
                # overlap: giữ phần đuôi của chunk trước
                tail = buf[-overlap:] if overlap > 0 else ""
                buf = (tail + "\n\n" + para).strip()
        if buf.strip():
            chunks.append((cur_section, buf.strip()))

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        n = 0
        for i, (section, content) in enumerate(chunks):
            chunk_id = f"{doc_id}_{i:04d}"
            content_hash = hashlib.sha1(content.encode()).hexdigest()
            conn.execute(
                "INSERT OR REPLACE INTO doc_chunks VALUES (?,?,?,?,?,?,?,?,?)",
                (chunk_id, doc_id, doc_title, section, version, content,
                 str(p), content_hash, now),
            )
            n += 1
        conn.commit()
        conn.close()
        return n

    def ingest_folder(
        self, folder: str | Path, **kwargs: Any
    ) -> dict[str, int]:
        """Ingest tất cả .txt/.md trong thư mục (1 mức). Trả {file: n_chunks}."""
        folder = Path(folder)
        if not folder.exists():
            raise FileNotFoundError(f"Kho tài liệu không tồn tại: {folder}")
        results: dict[str, int] = {}
        for f in sorted(folder.iterdir()):
            if f.is_file() and not self._is_forbidden(f):
                try:
                    results[f.name] = self.ingest_document(f, **kwargs)
                except ValueError:
                    raise
        return results

    # ---------------- retrieval ----------------

    def retrieve(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> RetrievalResult:
        """Tìm top-k chunk liên quan; dưới threshold → không có bằng chứng.

        Hybrid: keyword overlap (0.4) + BGE-M3 cosine (0.6) khi embedding
        khả dụng; chỉ keyword khi không. Mọi lỗi → result rỗng (fail-closed).
        """
        start = time.perf_counter()
        result = RetrievalResult(query=query)
        if not query or not query.strip():
            return result
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT chunk_id, doc_id, doc_title, section, version, content, "
                "source_path FROM doc_chunks"
            ).fetchall()
            conn.close()
        except Exception:
            return result
        if not rows:
            return result

        query_lower = query.lower()
        q_tokens = set(re.findall(r"[\w\u00C0-\u1EF9]{2,}", query_lower))

        # đồng nghĩa phổ biến tiếng Việt (paraphrase support) — expand 1 lần/query
        _SYN = {
            "thay mật khẩu": "đổi mật khẩu",
            "mất kết nối": "mất đồng bộ",
            "chập chờn": "mất đồng bộ",
            "thiết bị mất": "site alarm",
        }
        for src_k, dst_k in _SYN.items():
            if src_k in query_lower:
                q_tokens |= set(re.findall(r"[\w\u00C0-\u1EF9]{2,}", dst_k))

        # dense similarity của query với từng chunk (1 lần nếu có service)
        dense: dict[str, float] = {}
        if self.embedding_service is not None:
            try:
                q_vec = self.embedding_service.get_embedding(query)
                if q_vec:
                    for r in rows:
                        c_vec = self.embedding_service.get_embedding(r[5])
                        if c_vec:
                            from quan_ai_brain.cognition.embedding import (
                                cosine_similarity,
                            )

                            dense[r[0]] = max(0.0, cosine_similarity(q_vec, c_vec))
            except Exception:
                dense = {}

        scored: list[Chunk] = []
        for chunk_id, doc_id, title, section, version, content, src in rows:
            content_lower = content.lower()
            kw_matched = sum(1 for t in q_tokens if t in content_lower)
            kw_score = kw_matched / len(q_tokens) if q_tokens else 0.0
            ds = dense.get(chunk_id, 0.0)
            if self.embedding_service is not None and dense:
                score = kw_score * 0.4 + ds * 0.6
                reason = f"kw={kw_score:.2f}, dense={ds:.2f}"
            else:
                score = kw_score
                reason = f"kw={kw_score:.2f} (keyword-only)"
            if score >= threshold or kw_score >= 0.5:
                scored.append(Chunk(
                    chunk_id=chunk_id, doc_id=doc_id, doc_title=title,
                    section=section, version=version, content=content,
                    source_path=src, score=round(score, 4), score_reason=reason,
                ))

        scored.sort(key=lambda c: c.score, reverse=True)
        result.chunks = scored[:top_k]
        result.elapsed_ms = (time.perf_counter() - start) * 1000
        return result

    def answer_not_found_message(self) -> str:
        return (
            "Em chưa tìm thấy căn cứ trong kho tài liệu nội bộ cho câu hỏi này. "
            "Anh có thể cung cấp thêm tài liệu, hoặc hỏi theo cách khác ạ."
        )
