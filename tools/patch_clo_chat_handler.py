#!/usr/bin/env python
"""Patch server.py to integrate CLO V1 into chat handler."""
import re

# Read file
with open('src/quan_ai_brain/web/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the target block (after plan_note line)
old_block = '''                    for _pw in (getattr(task_plan, "warnings", None) or []):
                        if _pw and _pw not in all_warnings:
                            all_warnings.append(f"Plan: {_pw}")
                    durable_task_dict = task_rec.to_dict()
                    plan_note = f"\\n\\n📋 *Nhiệm vụ đã được tự động phân rã và đăng ký bền vững vào DurableTaskRegistry: `{task_rec.task_id}` (Rủi ro: {task_rec.risk_level}, Tiến trình: {len(task_rec.approved_scope)} bước DAG).* "
                    sanitized_reply += plan_note'''

new_block = '''                    for _pw in (getattr(task_plan, "warnings", None) or []):
                        if _pw and _pw not in all_warnings:
                            all_warnings.append(f"Plan: {_pw}")
                    durable_task_dict = task_rec.to_dict()
                    plan_note = f"\\n\\n📋 *Nhiệm vụ đã được tự động phân rã và đăng ký bền vững vào DurableTaskRegistry: `{task_rec.task_id}` (Rủi ro: {task_rec.risk_level}, Tiến trình: {len(task_rec.approved_scope)} bước DAG).* "
                    sanitized_reply += plan_note
                    
                    # CLO V1: Trigger learning session when task created
                    try:
                        from quan_ai_brain.cognition.continuous_learning_engine import ContinuousLearningEngine
                        
                        # Check if CLO is enabled
                        with MemoryStore(db_path, workspace=workspace) as clo_store:
                            clo_engine = ContinuousLearningEngine(clo_store, workspace=workspace)
                            if clo_engine.session_manager.is_clo_enabled():
                                # End current session if running, create next session
                                current_session = clo_engine.session_manager.get_current_session()
                                if current_session and current_session.status.value in ["RUNNING", "PLANNING", "EVALUATING"]:
                                    # End current session with task info
                                    next_plan = {
                                        "objectives": ["Continue learning from task execution"],
                                        "source_manifest": {"task_id": task_rec.task_id, "source": "chat_task"}
                                    }
                                    ended_session = clo_engine.end_session(
                                        session_id=current_session.session_id,
                                        evaluation_result={"task_created": True, "task_id": task_rec.task_id},
                                        unresolved_questions=[],
                                        next_plan=next_plan
                                    )
                                    learning_session_info = {
                                        "session_ended": current_session.session_id,
                                        "next_session": ended_session.session_id if ended_session.session_id != current_session.session_id else None,
                                        "cycle_number": ended_session.cycle_number
                                    }
                    except Exception as clo_err:
                        # Non-blocking: log but don't fail the request
                        all_warnings.append(f"CLO session trigger: {str(clo_err)[:100]}")'''

if old_block not in content:
    print("ERROR: Target block not found!")
    # Try to find similar block
    if "plan_note = f" in content:
        print("Found plan_note line, but block doesn't match exactly")
    exit(1)

content = content.replace(old_block, new_block)

# Write file
with open('src/quan_ai_brain/web/server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Patched server.py with CLO V1 integration")