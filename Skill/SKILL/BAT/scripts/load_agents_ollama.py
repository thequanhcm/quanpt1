import os
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

# Đường dẫn tới thư mục chứa các kỹ năng (Skills) của hệ thống V3/V4
WORKFORCE_DIR = r"e:\AI\Skill\BAT\ai_workforce"

def load_skill_prompt(agent_name: str) -> str:
    """Đọc file SKILL.md của agent và trả về nội dung làm System Prompt."""
    skill_path = os.path.join(WORKFORCE_DIR, agent_name, "SKILL.md")
    if not os.path.exists(skill_path):
        raise FileNotFoundError(f"Không tìm thấy file SKILL.md cho agent: {agent_name} tại {skill_path}")
    
    with open(skill_path, "r", encoding="utf-8") as f:
        return f.read()

class BatteryWorkforceOllamaAgent:
    def __init__(self, agent_name: str, model_name: str = "llama3"):
        """Khởi tạo một Agent dựa trên SKILL.md, sử dụng local model qua Ollama"""
        self.agent_name = agent_name
        self.system_prompt = load_skill_prompt(agent_name)
        
        # Khởi tạo ChatOllama trỏ về localhost mặc định (http://localhost:11434)
        print(f"Khởi tạo [{agent_name}] với mô hình cục bộ: {model_name}...")
        try:
            self.llm = ChatOllama(model=model_name, temperature=0.1)
        except Exception as e:
            print(f"Cảnh báo: Không thể kết nối tới Ollama. Lỗi: {e}")
            self.llm = None
            
    def invoke(self, user_message: str):
        """Gửi tin nhắn đến Agent"""
        if not self.llm:
            return "Model chưa được kết nối. Hãy đảm bảo Ollama đang chạy."
            
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message)
        ]
        
        print(f"\n[{self.agent_name.upper()}] đang suy nghĩ xử lý...")
        
        try:
            # invoke() sẽ gọi qua API nội bộ của Ollama tại cổng 11434
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            return f"Lỗi khi xử lý qua Ollama: {e}\n(Hãy kiểm tra xem model '{self.llm.model}' đã được tải (pull) về Ollama chưa)"

def main():
    print("Khởi tạo BAT Workforce bằng Llama 3 (Ollama Local)...\n")
    
    try:
        model_to_use = "llama3"
        
        # 1. Khởi tạo Orchestrator & Memory Agent
        orchestrator = BatteryWorkforceOllamaAgent("vibe-bat-intelligence-orchestrator", model_name=model_to_use)
        memory_agent = BatteryWorkforceOllamaAgent("vibe-bat-memory-agent", model_name=model_to_use)
        
        print("\nĐã tải thành công các Agents Local!")
        
        # --- LUỒNG CHẠY TỰ ĐỘNG (WORKFLOW) ---
        print("\n--- BƯỚC 1: Gửi báo cáo cho Orchestrator ---")
        alert_message = "Kết quả xả tải thực tế hôm nay: Chuỗi ắc quy số 2 còn SOH 82%, nội trở tăng."
        print(f"NOC Operator: {alert_message}")
        
        orchestrator_response = orchestrator.invoke(alert_message)
        print(f"\n[PHẢN HỒI TỪ ORCHESTRATOR]:\n{orchestrator_response}")
        
        # BƯỚC 2: Tự động trích xuất lệnh để chuyển cho Memory Agent
        # Trong thực tế sẽ dùng JSON parser, ở đây mô phỏng việc Orchestrator gọi Memory Agent
        print("\n--- BƯỚC 2: Orchestrator tự động kích hoạt Memory Agent ---")
        if "vibe-bat-memory-agent" in orchestrator_response.lower() or "memory" in orchestrator_response.lower():
            memory_payload = f"Hãy ghi nhớ sự kiện này vào Episodic Memory: {alert_message}"
            memory_response = memory_agent.invoke(memory_payload)
            print(f"\n[PHẢN HỒI TỪ MEMORY AGENT]:\n{memory_response}")
        else:
            print("Orchestrator không yêu cầu lưu bộ nhớ lúc này.")
            
    except FileNotFoundError as e:
        print(f"Lỗi tải file: {e}")
        
if __name__ == "__main__":
    main()
