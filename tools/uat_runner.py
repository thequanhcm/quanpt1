"""UAT (User Acceptance Testing) Script for QUAN AI BRAIN.

Run this script daily during UAT week to log issues and track progress.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

UAT_LOG_DIR = Path("data/uat_logs")
UAT_LOG_DIR.mkdir(exist_ok=True)

class UATLogger:
    """UAT logging and issue tracking."""
    
    def __init__(self, date: str = None):
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        self.date = date
        self.log_file = UAT_LOG_DIR / f"uat_{date}.json"
        self.sessions = []
        self.issues = []
        self.metrics = {
            "voice_latency": [],
            "memory_retrieval_accuracy": [],
            "command_success_rate": [],
            "errors": []
        }
        
        # Load existing log if exists
        if self.log_file.exists():
            with open(self.log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.sessions = data.get("sessions", [])
                self.issues = data.get("issues", [])
                self.metrics = data.get("metrics", self.metrics)
    
    def start_session(self, session_id: str, user: str = "Quanpt1"):
        """Start a new UAT session."""
        session = {
            "session_id": session_id,
            "user": user,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "end_time": None,
            "interactions": [],
            "status": "active"
        }
        self.sessions.append(session)
        print(f"✅ Session {session_id} started")
        return session
    
    def end_session(self, session_id: str):
        """End a UAT session."""
        for session in reversed(self.sessions):
            if session["session_id"] == session_id and session["status"] == "active":
                session["end_time"] = datetime.now(timezone.utc).isoformat()
                session["status"] = "completed"
                print(f"✅ Session {session_id} ended")
                break
    
    def log_interaction(self, session_id: str, user_input: str, bot_response: str, 
                       latency_ms: int = None, success: bool = True):
        """Log a single interaction."""
        for session in reversed(self.sessions):
            if session["session_id"] == session_id and session["status"] == "active":
                interaction = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_input": user_input,
                    "bot_response": bot_response,
                    "latency_ms": latency_ms,
                    "success": success
                }
                session["interactions"].append(interaction)
                
                # Track metrics
                if latency_ms:
                    self.metrics["voice_latency"].append(latency_ms)
                if not success:
                    self.metrics["errors"].append({
                        "input": user_input,
                        "response": bot_response,
                        "timestamp": interaction["timestamp"]
                    })
                
                break
    
    def report_issue(self, session_id: str, issue_type: str, description: str, 
                    severity: str = "medium", steps_to_reproduce: str = ""):
        """Report an issue found during UAT."""
        issue = {
            "issue_id": f"UAT-{len(self.issues)+1:03d}",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": issue_type,
            "description": description,
            "severity": severity,
            "steps_to_reproduce": steps_to_reproduce,
            "status": "open"
        }
        self.issues.append(issue)
        print(f"⚠️ Issue reported: {issue['issue_id']} - {description}")
        return issue
    
    def save(self):
        """Save UAT log to file."""
        data = {
            "date": self.date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sessions": self.sessions,
            "issues": self.issues,
            "metrics": self.metrics,
            "summary": self.generate_summary()
        }
        
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 UAT log saved to: {self.log_file}")
    
    def generate_summary(self) -> dict:
        """Generate UAT summary."""
        completed_sessions = [s for s in self.sessions if s["status"] == "completed"]
        total_interactions = sum(len(s["interactions"]) for s in completed_sessions)
        successful_interactions = sum(
            len([i for i in s["interactions"] if i.get("success", True)])
            for s in completed_sessions
        )
        
        avg_latency = (
            sum(self.metrics["voice_latency"]) / len(self.metrics["voice_latency"])
            if self.metrics["voice_latency"] else 0
        )
        
        open_issues = len([i for i in self.issues if i["status"] == "open"])
        
        return {
            "total_sessions": len(completed_sessions),
            "total_interactions": total_interactions,
            "successful_interactions": successful_interactions,
            "success_rate": successful_interactions / max(1, total_interactions) * 100,
            "avg_voice_latency_ms": avg_latency,
            "open_issues": open_issues,
            "critical_issues": len([i for i in self.issues if i["severity"] == "critical" and i["status"] == "open"])
        }


def run_uat_demo():
    """Run a demo UAT session."""
    print("=" * 60)
    print("QUAN AI BRAIN — UAT Demo Session")
    print("=" * 60)
    print()
    
    # Initialize logger
    uat = UATLogger()
    
    # Start session
    session = uat.start_session("UAT-2026-10-28-001")
    
    # Simulate interactions
    print("Simulating interactions...")
    
    interactions = [
        ("Trí nhớ của em lưu ở đâu?", "Dạ, trí nhớ em lưu theo 3 tầng...", 1200, True),
        ("Kiểm tra trạng thái UPS", "✅ UPS đang hoạt động bình thường", 800, True),
        ("Dừng tất cả", "🛑 Đã dừng các tác vụ", 200, True),
        ("Phân tích bình 17", "⚠️ Thiếu dữ liệu nội trở", 1500, False),
        ("Tạo báo cáo tuần", "📊 Báo cáo đã tạo", 2000, True),
    ]
    
    for user_input, bot_response, latency, success in interactions:
        print(f"\n👤 User: {user_input}")
        print(f"🤖 Bot: {bot_response}")
        print(f"⏱️ Latency: {latency}ms")
        
        uat.log_interaction(
            session["session_id"],
            user_input,
            bot_response,
            latency,
            success
        )
        
        if not success:
            uat.report_issue(
                session["session_id"],
                "functionality",
                f"Failed to process: {user_input}",
                "medium",
                "1. Send command\n2. Check response"
            )
    
    # End session
    uat.end_session(session["session_id"])
    
    # Save log
    uat.save()
    
    # Print summary
    print("\n" + "=" * 60)
    print("UAT SUMMARY")
    print("=" * 60)
    
    summary = uat.generate_summary()
    print(f"Sessions: {summary['total_sessions']}")
    print(f"Interactions: {summary['total_interactions']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    print(f"Avg latency: {summary['avg_voice_latency_ms']:.0f}ms")
    print(f"Open issues: {summary['open_issues']}")
    print(f"Critical issues: {summary['critical_issues']}")
    print()
    
    return summary


if __name__ == "__main__":
    run_uat_demo()