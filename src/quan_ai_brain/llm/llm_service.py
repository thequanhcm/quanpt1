"""Simple LLM Service wrapper for server."""

from quan_ai_brain.llm.router import LLMRouter


class LLMService:
    """Simple LLM service for chat responses."""
    
    def __init__(self):
        self.router = LLMRouter()
    
    def generate(self, prompt: str, model: str = "zai-org/GLM-5.3-Flash", 
                 reasoning_effort: str = "low", max_tokens: int = 1000) -> dict:
        """Generate response using LLM router."""
        try:
            # Use router.route() with explicit_model
            response = self.router.route(
                query=prompt,
                task_hint="chat",
                explicit_model=model
            )
            # response is RoutingDecision, need to execute it
            # For now, return a simple answer
            return {"answer": f"Đã nhận câu hỏi: {prompt[:50]}... (LLM routing: {response.model})"}
        except Exception as e:
            return {"answer": f"⚠️ Lỗi LLM: {str(e)}"}