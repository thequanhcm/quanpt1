#!/usr/bin/env python
"""Add CLO V1 API handlers to server.py."""

# Read file
with open('src/quan_ai_brain/web/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Handlers to add
handlers = '''
    # ========== CLO V1: Continuous Learning API Handlers ==========

    def _handle_api_learning_status(self) -> None:
        """GET /api/learning/status — Get current CLO status."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                status = clo_engine.get_learning_status()
            
            self._send_json({"success": True, "status": status})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_start(self, parsed_query) -> None:
        """POST /api/learning/start — Start continuous learning mode."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            # Parse request body
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            objectives = body.get("objectives", ["Learn from tasks and interactions"])
            source_manifest = body.get("source_manifest", {"sources": ["chat", "tasks", "memory"]})
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                session = clo_engine.start_continuous_learning(objectives, source_manifest)
            
            self._send_json({
                "success": True,
                "message": "Continuous learning started",
                "session": session.to_dict()
            })
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_stop(self, parsed_query) -> None:
        """POST /api/learning/stop — Stop continuous learning permanently."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            reason = body.get("reason", "Owner requested stop")
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.stop_continuous_learning(reason)
            
            self._send_json({"success": True, "message": f"Continuous learning stopped: {reason}"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_pause(self, parsed_query) -> None:
        """POST /api/learning/pause — Pause continuous learning."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            import json
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length).decode('utf-8')) if content_length > 0 else {}
            
            reason = body.get("reason", "Temporary pause")
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.pause_continuous_learning(reason)
            
            self._send_json({"success": True, "message": f"Continuous learning paused: {reason}"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

    def _handle_api_learning_resume(self) -> None:
        """POST /api/learning/resume — Resume from pause."""
        try:
            from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
            
            with MemoryStore(self.workspace / "data" / "brain.db", workspace=self.workspace) as store:
                clo_engine = ContinuousLearningEngine(store, workspace=self.workspace)
                clo_engine.resume_continuous_learning()
            
            self._send_json({"success": True, "message": "Continuous learning resumed"})
        except Exception as e:
            self._send_json({"success": False, "error": str(e)[:200]})

'''

# Find insertion point (before def run_executive_server)
insert_marker = "def run_executive_server(port: int = 8766"
if insert_marker not in content:
    print("ERROR: Insertion point not found!")
    exit(1)

# Insert handlers
content = content.replace(insert_marker, handlers + insert_marker)

# Write file
with open('src/quan_ai_brain/web/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Added CLO V1 API handlers")