"""Deterministic Mock LLM Provider for offline testing and diagnostics."""
from __future__ import annotations

import time
from typing import Any

from quan_ai_brain.llm.models import LLMRequest, LLMResponse, ModelInfo

DEFAULT_MOCK_MODELS = [
    ModelInfo(
        name="qwen2.5:7b",
        tag="qwen2.5:7b:latest",
        size_bytes=4661224676,
        modified_at="2026-10-17T00:00:00Z",
        digest="sha256:mock_qwen25_7b_digest",
        details={"family": "qwen2", "parameter_size": "7B", "quantization_level": "Q4_K_M"},
    ),
    ModelInfo(
        name="qwen2.5:1.5b",
        tag="qwen2.5:1.5b:latest",
        size_bytes=986122467,
        modified_at="2026-10-17T00:00:00Z",
        digest="sha256:mock_qwen25_15b_digest",
        details={"family": "qwen2", "parameter_size": "1.5B", "quantization_level": "Q4_K_M"},
    ),
]


class MockLLMProvider:
    """Offline mock provider. Produces deterministic test responses with explicit mock markers."""

    def __init__(
        self,
        canned_responses: dict[str, str] | None = None,
        default_models: list[ModelInfo] | None = None,
    ) -> None:
        self.canned_responses = canned_responses or {}
        self.models = default_models or list(DEFAULT_MOCK_MODELS)
        self.call_history: list[dict[str, Any]] = []

    def ping(self, timeout: float = 2.0) -> bool:
        """Mock provider is always available."""
        return True

    def list_models(self, timeout: float = 5.0) -> list[ModelInfo]:
        """Return predefined list of mock models."""
        return list(self.models)

    def has_model(self, model_name: str = "qwen2.5:7b", timeout: float = 5.0) -> bool:
        """Check if model is registered in mock list."""
        target = model_name.lower().strip()
        for m in self.models:
            m_name = m.name.lower()
            if m_name == target or m_name.startswith(f"{target}:"):
                return True
        return False

    def generate(self, request: LLMRequest | str, **kwargs: Any) -> LLMResponse:
        """Return deterministic mock response with required mock safety indicators."""
        if isinstance(request, str):
            request = LLMRequest(prompt=request, **kwargs)

        start = time.perf_counter()

        # Check if canned response matches exactly
        prompt_text = request.prompt.strip()
        if prompt_text in self.canned_responses:
            generated_text = f"[MOCK] {self.canned_responses[prompt_text]}"
        elif "Executive Planning Coordinator" in request.system_prompt or "JSON object following this exact schema" in prompt_text:
            generated_text = (
                '{\n'
                '  "summary": "Mô phỏng kế hoạch phân tích và kiểm tra an toàn hệ thống",\n'
                '  "steps": [\n'
                '    {\n'
                '      "step_id": "step-1",\n'
                '      "name": "read_system_status",\n'
                '      "description": "Đọc trạng thái hiện tại của hệ thống từ tệp nhật ký",\n'
                '      "expected_output": "Báo cáo trạng thái đọc được",\n'
                '      "risk_level": 0,\n'
                '      "preconditions": ["Hệ thống trong trạng thái hoạt động"],\n'
                '      "verification_method": "Kiểm tra exit code và dữ liệu đầu ra",\n'
                '      "dependencies": []\n'
                '    },\n'
                '    {\n'
                '      "step_id": "step-2",\n'
                '      "name": "analyze_telemetry",\n'
                '      "description": "Phân tích các thông số kỹ thuật trong bộ nhớ",\n'
                '      "expected_output": "Bảng tổng hợp chỉ số hiệu năng",\n'
                '      "risk_level": 1,\n'
                '      "preconditions": ["Đã có dữ liệu từ bước 1"],\n'
                '      "verification_method": "Đối chiếu ngưỡng an toàn",\n'
                '      "dependencies": ["step-1"]\n'
                '    }\n'
                '  ]\n'
                '}'
            )
        else:
            generated_text = (
                f"[MOCK] Deterministic response for model '{request.model}'. "
                f"Prompt received {len(request.prompt)} characters. "
                "Warning: This is a synthetic mock output, not actual LLM inference."
            )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        record = {
            "prompt": request.prompt,
            "model": request.model,
            "temperature": request.temperature,
            "timestamp": time.time(),
        }
        self.call_history.append(record)

        return LLMResponse(
            text=generated_text,
            model=request.model,
            provider="mock",
            is_mock=True,
            elapsed_ms=elapsed_ms,
            success=True,
            error_code=None,
            error_message=None,
            warning="MOCK MODE — NO REAL LLM INFERENCE",
            raw_metadata={"mock": True, "history_index": len(self.call_history) - 1},
        )
