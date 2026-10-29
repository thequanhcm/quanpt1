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
            # Use router to call appropriate provider
            response = self.router.chat(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                reasoning_effort=reasoning_effort
            )
            return {"answer": response.get("content", "")}
        except Exception as e:
            return {"answer": f"⚠️ Lỗi LLM: {str(e)}"}