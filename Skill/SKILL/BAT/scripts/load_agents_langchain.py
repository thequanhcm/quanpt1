import os
from langchain.chat_models import init_chat_model
from langchain.schema import SystemMessage, HumanMessage

# Đường dẫn tới thư mục chứa các kỹ năng (Skills)
WORKFORCE_DIR = r"e:\AI\Skill\BAT\ai_workforce"

def load_skill_prompt(agent_name: str) -> str:
    """Đọc file SKILL.md của agent và trả về nội dung làm System Prompt."""
    skill_path = os.path.join(WORKFORCE_DIR, agent_name, "SKILL.md")
    if not os.path.exists(skill_path):
        raise FileNotFoundError(f"Không tìm thấy file SKILL.md cho agent: {agent_name} tại {skill_path}")
    
    with open(skill_path, "r", encoding="utf-8") as f:
        return f.read()

class BatteryWorkforceAgent:
    def __init__(self, agent_name: str, model_name: str = "claude-3-5-sonnet-latest"):
        """Khởi tạo một Agent dựa trên SKILL.md"""
        self.agent_name = agent_name
        self.system_prompt = load_skill_prompt(agent_name)
        
        # Khởi tạo LLM model (Cần cài đặt langchain và thư viện model tương ứng, vd: langchain-anthropic)
        # Lưu ý: Cần set biến môi trường ANTHROPIC_API_KEY hoặc truyền key vào đây
        try:
            self.llm = init_chat_model(model_name)
        except Exception as e:
            print(f"Cảnh báo: Không thể khởi tạo model {model_name}. Lỗi: {e}")
            self.llm = None
            
    def invoke(self, user_message: str):
        """Gửi tin nhắn đến Agent"""
        if not self.llm:
            return "Model chưa được khởi tạo thành công."
            
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_message)
        ]
        
        print(f"\n[{self.agent_name.upper()}] đang suy nghĩ...")
        response = self.llm.invoke(messages)
        return response.content

def main():
    print("Khởi tạo BAT Workforce bằng LangChain...\n")
    
    try:
        # 1. Khởi tạo Orchestrator (Tổng chỉ huy)
        orchestrator = BatteryWorkforceAgent("vibe-bat-intelligence-orchestrator")
        
        # 2. Khởi tạo các Agent chuyên biệt
        prognostics_agent = BatteryWorkforceAgent("vibe-bat-prognostics-agent")
        memory_agent = BatteryWorkforceAgent("vibe-bat-memory-agent")
        
        print("Đã tải thành công các Agents!")
        
        # Ví dụ một luồng gọi cơ bản:
        print("\n--- TEST: Gửi cảnh báo lỗi cho Orchestrator ---")
        alert_message = "Cảnh báo: Chuỗi ắc quy số 2 có dấu hiệu tăng nội trở 5% và xả sâu 2 lần trong tuần qua."
        print(f"NOC Operator: {alert_message}")
        
        # Chú ý: Cần có API Key thực tế để chạy lệnh invoke dưới đây
        # response = orchestrator.invoke(alert_message)
        # print(f"\nPhản hồi từ Orchestrator:\n{response}")
        
    except FileNotFoundError as e:
        print(f"Lỗi tải file: {e}")
        
if __name__ == "__main__":
    main()
