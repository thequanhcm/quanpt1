#!/usr/bin/env python
"""Patch server.py to add CLO V1 API endpoints."""

# Read file
with open('src/quan_ai_brain/web/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add routes after cognitive-state
old_routes = '''        # Sprint 15 (b): evidence traceability — cognitive state của task (GET, read-only)
        if path == "/api/executive/tasks/cognitive-state":
            self._handle_api_task_cognitive_state(parsed.query)
            return'''

new_routes = '''        # Sprint 15 (b): evidence traceability — cognitive state của task (GET, read-only)
        if path == "/api/executive/tasks/cognitive-state":
            self._handle_api_task_cognitive_state(parsed.query)
            return
        
        # CLO V1: Continuous Learning API endpoints
        if path == "/api/learning/status":
            self._handle_api_learning_status()
            return
        elif path == "/api/learning/start":
            self._handle_api_learning_start(parsed.query)
            return
        elif path == "/api/learning/stop":
            self._handle_api_learning_stop(parsed.query)
            return
        elif path == "/api/learning/pause":
            self._handle_api_learning_pause(parsed.query)
            return
        elif path == "/api/learning/resume":
            self._handle_api_learning_resume()
            return'''

if old_routes not in content:
    print("ERROR: Target routes block not found!")
    exit(1)

content = content.replace(old_routes, new_routes)

# Write file
with open('src/quan_ai_brain/web/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Added CLO V1 API routes")