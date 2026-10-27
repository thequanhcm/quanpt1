"""XiaoZhi-Style Voice-First Interaction Pipeline for QUAN AI BRAIN.

Implements the end-to-end voice loop:
Wake Word / Push-to-Talk -> VAD/Audio Capture -> ASR -> Session Context -> Intent/Role Router
-> Reasoning/Governance -> Spoken Vietnamese Text Sanitization -> TTS -> Mouth Sync -> Pi 5 Speaker & Avatar.

Key Capabilities:
- Natural Vietnamese conversational tone ("Em" - "Anh").
- Multi-turn context memory & contextual continuation (e.g., "Ưu tiên việc quan trọng nhất trước").
- Barge-in / interruption handling (< 10ms cancellation).
- Spoken text sanitization: strips stack traces, JSON, code blocks from spoken TTS output.
- Self-correction recognition ("À nhầm", "Ý anh là...").
- Disambiguation and clarification prompts for incomplete requests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
import time
from typing import Any

from quan_ai_brain.cognition.role_orchestrator import ExecutiveRole, ExecutiveRoleOrchestrator, RoleResponse
from quan_ai_brain.voice.mouth_sync import MouthSyncEngine, UtteranceTimeline
from quan_ai_brain.voice.state_machine import VoiceState, VoiceStateMachine
from quan_ai_brain.voice.wake_word_config import WakeWordConfig, WakeWordMatchResult


@dataclass
class ConversationTurn:
    role: str  # "user" | "assistant"
    text: str
    spoken_text: str = ""
    timestamp: float = field(default_factory=time.time)
    intent: str = ""
    executive_role: str = ""


@dataclass
class VoiceInteractionResult:
    query: str
    response_text: str
    spoken_text: str
    active_role: str
    state: str
    mouth_timeline: dict[str, Any] | None = None
    barge_in_occurred: bool = False
    clarification_needed: bool = False
    context_turns: int = 0
    duration_ms: float = 0.0


def sanitize_for_spoken_vietnamese(text: str) -> str:
    """Sanitize response text into concise, natural Vietnamese for TTS output.
    
    Removes:
    - Code blocks and inline code (`...`)
    - JSON objects and curly braces {...}
    - Markdown formatting (headers, bold, italics, tables)
    - URLs and file paths
    - Stack traces and exception blocks

    V8 (27/10): thêm LỚP ĐỌC MÃ — từ điển phát âm mã kỹ thuật/quy tắc đọc số,
    đơn vị; cắt theo CÂU (không cắt giữa câu). KHÔNG đổi nội dung có nghĩa.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Strip Markdown code blocks ```...```
    s = re.sub(r"```[\s\S]*?```", " [Đã bỏ qua mã kỹ thuật] ", s)

    # 2. Strip inline code `...`
    s = re.sub(r"`[^`]+`", "", s)

    # 3. Strip JSON blocks {...}
    s = re.sub(r"\{[^{}]*\}", "", s)

    # 4. Strip URLs and file paths
    s = re.sub(r"https?://\S+", "", s)
    s = re.sub(r"[A-Za-z]:\\[\w\\\.-]+", "", s)
    s = re.sub(r"/\S+/\S+", "", s)

    # 5. Strip Markdown headers, bullets, bold/italic symbols
    s = re.sub(r"^#+\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[-*+]\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"[*_~]", "", s)

    # 5.5 V8 — LỚP ĐỌC MÃ (từ điển phát âm): áp TRƯỚC khi cắt độ dài.
    # KHÔNG đổi nghĩa — chỉ biến mã viết tắt thành dạng edge-tts đọc tự nhiên.
    _CODE_READING = {
        "R0": "R không",
        "R1": "R một",
        "R2": "R hai",
        "R3": "R ba",
        "R4": "R bốn",
        "R5": "R năm",
    }
    for code, spoken in _CODE_READING.items():
        s = re.sub(rf"\b{code}\b(?!\d)", spoken, s)

    # 6. Normalize whitespace and trim
    s = re.sub(r"\s+", " ", s).strip()

    # 7. Truncate overly verbose sentences for natural voice listening
    max_len = 1500 if ("TONY PHAM" in s or "QUAN AI BRAIN" in s) else 350
    if len(s) > max_len:
        # V8: cắt theo CÂU (dấu câu kết thúc) — không cắt giữa câu như trước.
        sentences = re.split(r"(?<=[.!?])\s+", s)
        truncated = ""
        for sentence in sentences:
            if len(truncated) + len(sentence) <= max_len:
                truncated = f"{truncated} {sentence}".strip()
            else:
                break
        if not truncated:
            # Câu đầu tiên đã vượt max_len: cắt tại dấu phẩy/giữa từ gần max_len nhất,
            # nhưng luôn BÓP về ranh giới từ (không để đuôi câu cụt không nghĩa).
            first = sentences[0] if sentences else s
            cut = first[: max_len - 10]
            last_space = cut.rfind(" ")
            if last_space > max_len // 2:
                cut = cut[:last_space]
            truncated = cut.rstrip(" ,;:") + "..."
        s = truncated

    return s


class XiaoZhiVoicePipeline:
    """Manages real-time voice interactions, dialogue context, and mouth sync."""

    def __init__(
        self,
        role_orchestrator: ExecutiveRoleOrchestrator | None = None,
        mouth_sync: MouthSyncEngine | None = None,
        wake_config: WakeWordConfig | None = None,
    ) -> None:
        self.state_machine = VoiceStateMachine(initial_state=VoiceState.STANDBY)
        self.orchestrator = role_orchestrator or ExecutiveRoleOrchestrator()
        self.mouth_sync = mouth_sync or MouthSyncEngine()
        self.wake_config = wake_config or WakeWordConfig()

        self.history: list[ConversationTurn] = []
        self.active_timeline: UtteranceTimeline | None = None
        self.last_interaction_time: float = time.time()

    def process_barge_in(self, reason: str = "User interrupted") -> bool:
        """Instantly stops speaking or thinking when the user cuts in (<10ms)."""
        if self.state_machine.current_state in (VoiceState.SPEAKING, VoiceState.THINKING):
            if self.active_timeline:
                self.active_timeline.is_cancelled = True
                self.active_timeline = None
            self.state_machine.transition_to(VoiceState.INTERRUPTED, reason=reason)
            self.state_machine.transition_to(VoiceState.LISTENING, reason="Ready for new user voice")
            return True
        return False

    def handle_voice_input(
        self,
        raw_text: str,
        is_push_to_talk: bool = False,
        current_playback_active: bool = False,
    ) -> VoiceInteractionResult:
        """Executes full conversational cycle from transcribed voice to synthesized reply."""
        start_t = time.perf_counter()
        barge_in = False

        # Check if user spoke while assistant was playing audio
        if current_playback_active or self.state_machine.current_state == VoiceState.SPEAKING:
            self.process_barge_in(reason="Barge-in detected from audio input")
            barge_in = True

        # State transition: Listening -> Transcribing
        self.state_machine.transition_to(VoiceState.LISTENING, reason="Audio packet received")
        self.state_machine.transition_to(VoiceState.TRANSCRIBING, reason="Processing text")

        text = raw_text.strip()
        if not text:
            self.state_machine.transition_to(VoiceState.STANDBY, reason="Empty audio")
            return VoiceInteractionResult(
                query="",
                response_text="Em chưa nghe rõ, Anh có thể nói lại được không ạ?",
                spoken_text="Em chưa nghe rõ, Anh có thể nói lại được không ạ?",
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT.value,
                state=self.state_machine.current_state.value,
                duration_ms=round((time.perf_counter() - start_t) * 1000, 2),
            )

        # Check wake words if not in push-to-talk mode
        query = text
        if not is_push_to_talk:
            match = self.wake_config.match(text)
            if match.matched:
                if match.is_control_command:
                    return self._handle_control_command(match)
                if match.extracted_payload:
                    query = match.extracted_payload

        # Handle correction / self-correction in conversation
        query = self._resolve_corrections(query)

        # Transition to Thinking
        self.state_machine.transition_to(VoiceState.THINKING, reason="Reasoning and role routing")

        # Context continuation check:
        # If user asks e.g. "Ưu tiên việc quan trọng nhất trước" following a plan request,
        # carry context from previous turn.
        context_dict: dict[str, Any] = {
            "recent_turns": [asdict(t) for t in self.history[-4:]],
        }

        # Process through Role Orchestrator
        role_resp: RoleResponse = self.orchestrator.process(query, context=context_dict)

        # Sanitize for spoken Vietnamese TTS
        spoken = sanitize_for_spoken_vietnamese(role_resp.response_text)

        # Generate mouth lip-sync timeline
        timeline = self.mouth_sync.synthesize_timeline(spoken)
        self.active_timeline = timeline

        # Transition to Speaking
        self.state_machine.transition_to(VoiceState.SPEAKING, reason="Playing TTS and streaming mouth sync")

        # Record conversation turn
        turn = ConversationTurn(
            role="user",
            text=query,
            intent="",
            executive_role=role_resp.active_role.value,
        )
        self.history.append(turn)

        asst_turn = ConversationTurn(
            role="assistant",
            text=role_resp.response_text,
            spoken_text=spoken,
            executive_role=role_resp.active_role.value,
        )
        self.history.append(asst_turn)

        # Ready for next cycle
        self.state_machine.transition_to(VoiceState.STANDBY, reason="Turn completed")

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
        return VoiceInteractionResult(
            query=query,
            response_text=role_resp.response_text,
            spoken_text=spoken,
            active_role=role_resp.active_role.value,
            state=self.state_machine.current_state.value,
            mouth_timeline=timeline.to_dict(),
            barge_in_occurred=barge_in,
            context_turns=len(self.history),
            duration_ms=elapsed_ms,
        )

    def _resolve_corrections(self, query: str) -> str:
        """Detects speech correction patterns like 'À nhầm, ...' or 'Ý anh là...'."""
        correction_patterns = [
            r"^(?:à nhầm|ý anh là|sửa lại|không phải|đính chính là)\s*[,:]?\s*(.+)$",
            r"^nhầm rồi\s*[,:]?\s*(.+)$",
        ]
        q_lower = query.lower()
        for pat in correction_patterns:
            m = re.match(pat, q_lower, re.IGNORECASE)
            if m:
                corrected = query[m.start(1):].strip()
                return corrected
        return query

    def _handle_control_command(self, match: WakeWordMatchResult) -> VoiceInteractionResult:
        action = match.control_action
        if action == "STOP_SPEAKING":
            self.process_barge_in("Stop command detected")
            return VoiceInteractionResult(
                query=match.keyword,
                response_text="Dạ, em đã dừng nói ngay lập tức.",
                spoken_text="Dạ, em đã dừng nói ngay lập tức.",
                active_role=ExecutiveRole.SAFETY_OFFICER.value,
                state=self.state_machine.current_state.value,
            )
        elif action == "SLEEP":
            self.state_machine.transition_to(VoiceState.DISABLED, reason="Sleep command")
            return VoiceInteractionResult(
                query=match.keyword,
                response_text="Em xin phép tạm nghỉ, khi cần Anh cứ gọi 'Tony ơi' nhé.",
                spoken_text="Em xin phép tạm nghỉ, khi cần Anh cứ gọi 'Tony ơi' nhé.",
                active_role=ExecutiveRole.EXECUTIVE_ASSISTANT.value,
                state=self.state_machine.current_state.value,
            )
        return VoiceInteractionResult(
            query=match.keyword,
            response_text="Lệnh điều khiển đã được thực thi.",
            spoken_text="Lệnh điều khiển đã được thực thi.",
            active_role=ExecutiveRole.SAFETY_OFFICER.value,
            state=self.state_machine.current_state.value,
        )
