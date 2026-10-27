"""V6 workflow memory — tái sử dụng cho Cấp 3 (§5.4).

Lưu quy trình đã kiểm chứng thành bản ghi truy xuất được; VERIFIED chỉ khi
có bằng chứng lần chạy đạt tiêu chí. Không tái sử dụng mù quáng — mọi lần
dùng phải kiểm tra điều kiện áp dụng.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowRecord:
    """Verified Workflow Memory — V7 §5.4."""

    workflow_id: str
    version: str
    task_type: str
    preconditions: list[str]
    input_schema: dict[str, str]
    step_sequence: list[str]
    tools_required: list[str]
    evidence_requirements: list[str]
    validation_rules: list[str]
    failure_modes: list[str]
    expected_outputs: list[str]
    test_refs: list[str]
    verified_runs: list[dict[str, Any]] = field(default_factory=list)  # [{'run_id','task_ref','passed','measured','at'}]
    known_limitations: list[str] = field(default_factory=list)
    last_verified_at: str = ""
    status: str = "PROPOSED"  # PROPOSED | VERIFIED | NEEDS_REVIEW | RETIRED
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "WorkflowRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class WorkflowMemory:
    """Lưu JSON file — không tạo DB mới; fail-honest."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._workflows: dict[str, WorkflowRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._workflows = {w["workflow_id"]: WorkflowRecord.from_dict(w) for w in data.get("workflows", [])}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            backup = self.path.with_suffix(".json.corrupt")
            backup.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
            raise ValueError(f"Workflow memory corrupt; backup saved: {exc}") from exc

    def _save(self) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({"version": 1, "workflows": [w.to_dict() for w in self._workflows.values()]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def save_workflow(
        self,
        task_type: str,
        preconditions: list[str],
        input_schema: dict[str, str],
        step_sequence: list[str],
        tools_required: list[str],
        evidence_requirements: list[str],
        validation_rules: list[str],
        failure_modes: list[str],
        expected_outputs: list[str],
        test_refs: list[str],
        source_task_ref: str = "",
        known_limitations: list[str] | None = None,
    ) -> WorkflowRecord:
        if not task_type.strip() or not step_sequence:
            raise ValueError("task_type and step_sequence are required")
        now = now_utc()
        wf = WorkflowRecord(
            workflow_id=f"wf_{uuid.uuid4().hex[:10]}",
            version="1.0.0",
            task_type=task_type.strip(),
            preconditions=list(preconditions),
            input_schema=dict(input_schema),
            step_sequence=list(step_sequence),
            tools_required=list(tools_required),
            evidence_requirements=list(evidence_requirements),
            validation_rules=list(validation_rules),
            failure_modes=list(failure_modes),
            expected_outputs=list(expected_outputs),
            test_refs=list(test_refs),
            known_limitations=list(known_limitations or []),
            status="PROPOSED",
            created_at=now,
            updated_at=now,
        )
        if source_task_ref:
            wf.verified_runs.append({
                "run_id": f"run_{uuid.uuid4().hex[:8]}",
                "task_ref": source_task_ref,
                "passed": None,  # chưa đánh giá — fail-honest
                "measured": {},
                "at": now,
            })
        self._workflows[wf.workflow_id] = wf
        self._save()
        return wf

    def record_verified_run(self, workflow_id: str, task_ref: str, passed: bool, measured: dict[str, Any]) -> WorkflowRecord:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise KeyError(f"Unknown workflow: {workflow_id}")
        wf.verified_runs.append({
            "run_id": f"run_{uuid.uuid4().hex[:8]}",
            "task_ref": task_ref,
            "passed": bool(passed),
            "measured": dict(measured),
            "at": now_utc(),
        })
        if passed:
            wf.status = "VERIFIED"
            wf.last_verified_at = now_utc()
        else:
            wf.status = "NEEDS_REVIEW"
        wf.updated_at = now_utc()
        self._save()
        return wf

    def find_reusable(self, task_type: str) -> list[WorkflowRecord]:
        """Chỉ trả workflow VERIFIED (không ép dùng bản chưa kiểm chứng)."""
        tt = (task_type or "").lower()
        return [w for w in self._workflows.values() if w.status == "VERIFIED" and (tt in w.task_type.lower() or w.task_type.lower() in tt)]

    def check_preconditions(self, workflow_id: str, available_sources: list[str], available_permissions: list[str]) -> dict[str, Any]:
        """§5.5: kiểm tra điều kiện áp dụng trước khi tái sử dụng — không mù quáng."""
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise KeyError(f"Unknown workflow: {workflow_id}")
        missing_sources = [p for p in wf.preconditions if p.startswith("source:") and p[7:] not in available_sources]
        missing_permissions = [p for p in wf.preconditions if p.startswith("perm:") and p[5:] not in available_permissions]
        return {
            "workflow_id": workflow_id,
            "reusable": wf.status == "VERIFIED" and not missing_sources and not missing_permissions,
            "missing_sources": missing_sources,
            "missing_permissions": missing_permissions,
            "status": wf.status,
        }

    def get(self, workflow_id: str) -> WorkflowRecord | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[WorkflowRecord]:
        return list(self._workflows.values())
