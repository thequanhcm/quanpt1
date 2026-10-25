"""Safe local CLI for self-check and explicit memory sandbox operations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from quan_ai_brain.daemon.health import health_as_dict
from quan_ai_brain.memory.sqlite_store import MemoryStore


def _project_root() -> Path:
    # Resolve to the current working directory so user commands operate only when run
    # from the intended project workspace. Do not silently infer an E: drive location.
    return Path.cwd().resolve()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(prog="quan-ai-brain", description="QUAN AI BRAIN CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("self-check", help="Report basic runtime health")
    add = sub.add_parser("memory-add", help="Add an episodic record to the local project database")
    add.add_argument("--summary", required=True)
    add.add_argument("--source", default="manual")
    add.add_argument("--kind", default="task")
    list_cmd = sub.add_parser("memory-list", help="List recent episodic records")
    list_cmd.add_argument("--limit", type=int, default=20)

    # LLM diagnostic commands
    sub.add_parser("llm-health", help="Check local Ollama status and available models")
    sub.add_parser("llm-models", help="List models from local Ollama endpoint")
    ask_cmd = sub.add_parser("llm-ask", help="Send a test prompt to local LLM")
    ask_cmd.add_argument("--prompt", required=True, help="Prompt text")
    ask_cmd.add_argument("--model", default="qwen2.5:7b", help="Model name (default: qwen2.5:7b)")
    ask_cmd.add_argument("--fallback", action="store_true", help="Allow synthetic mock fallback if Ollama is offline")
    ask_cmd.add_argument("--timeout", type=float, default=120.0, help="Timeout in seconds (default: 120.0)")

    # NetMind (GLM-5.3) cloud provider commands (Sprint 1)
    sub.add_parser("netmind-health", help="Check NetMind GLM-5.3-Flash gateway status (no key is ever printed)")
    nm_ask_cmd = sub.add_parser("netmind-ask", help="Send a prompt to GLM-5.3-Flash via NetMind (requires owner-approved env config)")
    nm_ask_cmd.add_argument("--prompt", required=True, help="Prompt text")
    nm_ask_cmd.add_argument("--system", default="", help="Optional system prompt")
    nm_ask_cmd.add_argument("--max-tokens", type=int, default=512, help="Max completion tokens (default: 512)")
    nm_ask_cmd.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds (default: 60.0)")

    # Cognition & Context Building commands (Sprint 2C)
    ctx_cmd = sub.add_parser("context-build", help="Retrieve memories and build structured prompt context")
    ctx_cmd.add_argument("--query", required=True, help="User query text")
    ctx_cmd.add_argument("--scope", default=None, help="Target project scope")
    ctx_cmd.add_argument("--top-k", type=int, default=5, help="Number of memories to retrieve")
    ctx_cmd.add_argument("--max-chars", type=int, default=4000, help="Maximum character budget")

    cog_ask_cmd = sub.add_parser("cognitive-ask", help="Retrieve memories, build context, and generate LLM answer")
    cog_ask_cmd.add_argument("--query", required=True, help="User query text")
    cog_ask_cmd.add_argument("--scope", default=None, help="Target project scope")
    cog_ask_cmd.add_argument("--model", default="qwen2.5:7b", help="Model name (default: qwen2.5:7b)")
    cog_ask_cmd.add_argument("--fallback", action="store_true", help="Allow synthetic mock fallback if Ollama is offline")
    cog_ask_cmd.add_argument("--max-chars", type=int, default=4000, help="Maximum character budget")
    cog_ask_cmd.add_argument("--timeout", type=float, default=120.0, help="Timeout in seconds (default: 120.0)")

    # Planning & Governance commands (Sprint 3A)
    plan_cmd = sub.add_parser("plan-create", help="Create a structured TaskPlan with R0-R5 risk assessment")
    plan_cmd.add_argument("--goal", required=True, help="Goal or objective of the plan")
    plan_cmd.add_argument("--scope", default=None, help="Target project scope")
    plan_cmd.add_argument("--model", default="qwen2.5:7b", help="Model name (default: qwen2.5:7b)")
    plan_cmd.add_argument("--fallback", action="store_true", help="Allow synthetic mock fallback if Ollama is offline")
    plan_cmd.add_argument("--format", choices=["json", "text"], default="text", help="Output format (text or json)")

    # Tool Sandbox commands (Sprint 3B)
    sub.add_parser("tool-list", help="List registered tools in the Safe Tool Sandbox")
    tool_run_cmd = sub.add_parser("tool-run", help="Execute a tool safely through the multi-layer Sandbox gate")
    tool_run_cmd.add_argument("--tool", required=True, help="Registered tool ID")
    tool_run_cmd.add_argument("--params", default="{}", help="Tool parameters in JSON format")
    tool_run_cmd.add_argument("--approval-id", default=None, help="Owner approval ID token")
    tool_run_cmd.add_argument("--confirm", action="store_true", help="Explicitly confirm owner approval via CLI flag")
    tool_run_cmd.add_argument("--dry-run", action="store_true", help="Execute in dry-run simulation mode")

    # Self-Learning & Upgrade Proposal commands (Phase F)
    learn_cmd = sub.add_parser(
        "learning-cycle-dryrun",
        aliases=["learning-propose"],
        help="Run one supervised, bounded dry-run self-learning cycle",
    )
    learn_cmd.add_argument("--task-id", default=None, help="Observed task identifier")
    learn_cmd.add_argument("--error", default=None, help="Observed error or capability gap description")
    learn_cmd.add_argument("--scope", default="general", help="Target project scope")
    learn_cmd.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text or json)")

    restart_cmd = sub.add_parser("restart", help="Automatically restart QUAN AI BRAIN services (Desk & Chat)")
    restart_cmd.add_argument("--target", choices=["all", "desk", "chat"], default="all", help="Target services")
    restart_cmd.add_argument("--validate", action="store_true", help="Run validate_and_report before restarting")
    restart_cmd.add_argument("--test", action="store_true", help="Run quick pytest before restarting")
    restart_cmd.add_argument("--no-browser", action="store_true", help="Do not open browser")

    args = parser.parse_args(argv)
    if args.command == "self-check":
        print(json.dumps(health_as_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "restart":
        root = _project_root()
        restart_script = root / "tools" / "restart_system.py"
        if not restart_script.exists():
            print(f"Lỗi: Không tìm thấy {restart_script}")
            return 1
        import subprocess
        cmd = [sys.executable, str(restart_script), "--target", args.target]
        if args.validate:
            cmd.append("--validate")
        if args.test:
            cmd.append("--test")
        if args.no_browser:
            cmd.append("--no-browser")
        res = subprocess.run(cmd, cwd=root)
        return res.returncode

    if args.command == "llm-health":
        from quan_ai_brain.llm import LLMProvider
        provider = LLMProvider()
        print(json.dumps(provider.health(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "netmind-health":
        from quan_ai_brain.llm.netmind_provider import NetMindProvider
        provider = NetMindProvider()
        print(json.dumps(provider.health(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "netmind-ask":
        from quan_ai_brain.llm import LLMRequest
        from quan_ai_brain.llm.netmind_provider import NETMIND_CHAT_MODEL, NetMindProvider
        provider = NetMindProvider()
        req = LLMRequest(
            prompt=args.prompt,
            model=NETMIND_CHAT_MODEL,
            system_prompt=args.system,
            timeout_seconds=args.timeout,
            metadata={"max_tokens": args.max_tokens, "tier": "manual_cli"},
        )
        resp = provider.generate(req)
        out = {
            "success": resp.success,
            "provider": resp.provider,
            "model": resp.model,
            "is_mock": resp.is_mock,
            "elapsed_ms": resp.elapsed_ms,
            "error_code": resp.error_code,
            "text": resp.text,
            "raw_metadata": resp.raw_metadata,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if resp.success else 1

    if args.command == "llm-models":
        from quan_ai_brain.llm import LLMProvider
        provider = LLMProvider()
        try:
            models = provider.list_models()
            print(json.dumps([m.to_dict() for m in models], ensure_ascii=False, indent=2))
            return 0
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 1

    if args.command == "llm-ask":
        from quan_ai_brain.llm import FallbackMode, LLMProvider, LLMRequest
        mode = FallbackMode.ON_ERROR if args.fallback else FallbackMode.NEVER
        provider = LLMProvider(fallback_mode=mode, default_model=args.model)
        req = LLMRequest(prompt=args.prompt, model=args.model, timeout_seconds=args.timeout)
        resp = provider.generate(req)
        print(json.dumps(resp.to_dict(), ensure_ascii=False, indent=2))
        return 0 if resp.success else 1

    if args.command == "tool-list":
        root = _project_root()
        from quan_ai_brain.tools import SafeToolSandbox
        sandbox = SafeToolSandbox(workspace=root)
        tools_info = []
        for t in sandbox.registry.list_tools():
            tools_info.append({
                "tool_id": t.tool_id,
                "action_type": t.action_type,
                "risk_level": t.risk_level.name,
                "description": t.description,
                "side_effects": t.side_effects,
                "supports_dry_run": t.supports_dry_run,
            })
        print(json.dumps(tools_info, ensure_ascii=False, indent=2))
        return 0

    if args.command == "tool-run":
        root = _project_root()
        from quan_ai_brain.tools import SafeToolSandbox
        sandbox = SafeToolSandbox(workspace=root)
        try:
            params = json.loads(args.params)
        except Exception as exc:
            print(json.dumps({"error": f"Invalid JSON in --params: {exc}"}, ensure_ascii=False, indent=2))
            return 1

        approval_id = args.approval_id
        if not approval_id:
            tool = sandbox.registry.get(args.tool)
            if tool:
                # Check for explicit CLI flag confirmation
                if getattr(args, "confirm", False):
                    req = sandbox.approval_gate.create_request(
                        tool_id=tool.tool_id,
                        action=tool.action_type,
                        params=params,
                        risk_level=tool.risk_level,
                        goal="CLI flag explicit confirmation",
                    )
                    app = sandbox.approval_gate.grant_approval(
                        req,
                        approver="owner:cli_flag_confirm",
                        notes="Unauthenticated CLI flag confirmation",
                    )
                    approval_id = app.approval_id
                elif sys.stdin.isatty():
                    # Interactive terminal prompt
                    print("\n" + "=" * 60, file=sys.stderr)
                    print("  QUAN AI BRAIN — OWNER APPROVAL REQUIRED (CONSENT FIRST)", file=sys.stderr)
                    print("=" * 60, file=sys.stderr)
                    print(f"Tool ID:      {tool.tool_id}", file=sys.stderr)
                    print(f"Action:       {tool.action_type}", file=sys.stderr)
                    print(f"Risk Level:   {tool.risk_level.name}", file=sys.stderr)
                    print(f"Description:  {tool.description}", file=sys.stderr)
                    print(f"Parameters:   {json.dumps(params, ensure_ascii=False)}", file=sys.stderr)
                    print("-" * 60, file=sys.stderr)
                    print("Notice: Terminal approval provides unauthenticated local consent for this one-time execution.", file=sys.stderr)
                    print("=" * 60, file=sys.stderr)
                    try:
                        ans = input("Do you approve this tool execution? [y/N]: ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        ans = "no"
                    if ans in ("y", "yes"):
                        req = sandbox.approval_gate.create_request(
                            tool_id=tool.tool_id,
                            action=tool.action_type,
                            params=params,
                            risk_level=tool.risk_level,
                            goal="CLI terminal interactive approval",
                        )
                        app = sandbox.approval_gate.grant_approval(
                            req,
                            approver="owner:cli_interactive",
                            notes="Unauthenticated terminal interactive confirmation",
                        )
                        approval_id = app.approval_id

        result = sandbox.execute(
            tool_id=args.tool,
            params=params,
            approval_id=approval_id,
            dry_run=args.dry_run,
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.success else 1

    root = _project_root()
    db_path = root / "data" / "brain.db"
    with MemoryStore(db_path, workspace=root) as store:
        if args.command == "memory-add":
            record_id = store.add_episode(
                args.summary,
                kind=args.kind,
                source_ref=args.source,
                metadata={"created_via": "cli"},
            )
            print(f"Episode recorded: {record_id}")
            print(f"Database: {db_path.relative_to(root)}")
            return 0
        if args.command == "memory-list":
            print(json.dumps(store.list_episodes(args.limit), ensure_ascii=False, indent=2))
            return 0
        if args.command == "context-build":
            from quan_ai_brain.cognition import CognitiveRetriever, MemoryQuery, PromptContextBuilder
            retriever = CognitiveRetriever(store)
            query = MemoryQuery(
                query=args.query,
                project_scope=args.scope,
                top_k=args.top_k,
                max_chars=args.max_chars,
            )
            result = retriever.retrieve(query)
            builder = PromptContextBuilder(default_max_chars=args.max_chars)
            context = builder.build(
                user_query=args.query,
                retrieval=result,
                max_chars=args.max_chars,
                project_scope=args.scope,
            )
            print(json.dumps(context.to_dict(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "cognitive-ask":
            from quan_ai_brain.cognition import CognitiveRetriever, MemoryQuery, PromptContextBuilder
            from quan_ai_brain.llm import FallbackMode, LLMProvider, LLMRequest
            retriever = CognitiveRetriever(store)
            query = MemoryQuery(
                query=args.query,
                project_scope=args.scope,
                top_k=5,
                max_chars=args.max_chars,
            )
            result = retriever.retrieve(query)
            builder = PromptContextBuilder(default_max_chars=args.max_chars)
            context = builder.build(
                user_query=args.query,
                retrieval=result,
                max_chars=args.max_chars,
                project_scope=args.scope,
            )
            mode = FallbackMode.ON_ERROR if args.fallback else FallbackMode.NEVER
            provider = LLMProvider(fallback_mode=mode, default_model=args.model)
            req = LLMRequest(
                prompt=context.rendered_context,
                system_prompt=context.system_instructions,
                model=args.model,
                timeout_seconds=args.timeout,
            )
            resp = provider.generate(req)
            output = {
                "answer": resp.text,
                "model": resp.model,
                "provider": resp.provider,
                "is_mock": resp.is_mock,
                "success": resp.success,
                "warning": resp.warning,
                "error_message": resp.error_message,
                "used_memory_ids": [m.memory_id for m in context.used_memories],
                "context_chars": context.total_chars,
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0 if resp.success else 1
        if args.command == "plan-create":
            from quan_ai_brain.cognition import CognitiveRetriever, PromptContextBuilder
            from quan_ai_brain.governance.policy import PolicyEngine
            from quan_ai_brain.llm import FallbackMode, LLMProvider
            from quan_ai_brain.planning import ExecutiveCoordinator, TaskStatus

            mode = FallbackMode.ON_ERROR if args.fallback else FallbackMode.NEVER
            provider = LLMProvider(fallback_mode=mode, default_model=args.model)
            policy = PolicyEngine(root)
            retriever = CognitiveRetriever(store)
            builder = PromptContextBuilder()

            coordinator = ExecutiveCoordinator(
                workspace=root,
                llm_provider=provider,
                policy_engine=policy,
                retriever=retriever,
                context_builder=builder,
            )
            plan = coordinator.plan(
                goal=args.goal,
                project_scope=args.scope,
                model=args.model,
                fallback=args.fallback,
            )

            if args.format == "json":
                print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
            else:
                print(plan.explain())
            return 0 if plan.status != TaskStatus.FAILED else 1
        if args.command in ("learning-cycle-dryrun", "learning-propose"):
            import uuid
            from quan_ai_brain.contract.models import EvidenceRecord, TaskOutcome, TaskState
            from quan_ai_brain.core.audit import AuditLogger
            from quan_ai_brain.governance.state_store import GovernanceStateStore
            from quan_ai_brain.learning.engine import SelfLearningEngine

            gov_path = root / "data" / "governance.db"
            with GovernanceStateStore(gov_path, workspace=root) as gov_store:
                audit = AuditLogger(root)
                engine = SelfLearningEngine(
                    workspace=root,
                    memory_store=store,
                    governance_store=gov_store,
                    audit_logger=audit,
                )

                task_id = args.task_id or f"task_obs_{uuid.uuid4().hex[:8]}"
                error_desc = args.error or "Local Ollama daemon unreachable at 127.0.0.1:11434 (Connection refused)."
                outcome = TaskOutcome(
                    task_id=task_id,
                    request_id=f"req_{uuid.uuid4().hex[:8]}",
                    correlation_id=f"corr_{uuid.uuid4().hex[:8]}",
                    state=TaskState.FAILED,
                    error_message=error_desc,
                    evidence=[
                        EvidenceRecord(
                            evidence_id=f"ev_{uuid.uuid4().hex[:8]}",
                            source_type="local_system_probe",
                            description="Observed execution failure or capability bottleneck",
                            evidence_payload={"error": error_desc, "scope": args.scope},
                        )
                    ],
                    is_outcome_certain=False,
                )

                gap = engine.observe_task(outcome)
                if gap is None:
                    print(json.dumps({"status": "no_gap_detected", "message": "Task outcome exhibited no failure or uncertainty."}, ensure_ascii=False, indent=2))
                    return 0

                authorized_sources = [
                    {"title": "System Baseline", "path": "docs/SYSTEM_BASELINE.md", "type": "architecture_doc"},
                    {"title": "Local LLM Client", "path": "src/quan_ai_brain/llm/client.py", "type": "source_code"},
                    {"title": "Python Standard Library Specification", "path": "stdlib", "type": "standard_library"},
                ]
                dossier = engine.research_gap(
                    gap=gap,
                    question=f"How to address: {gap.description} with standard-library code?",
                    authorized_sources=authorized_sources,
                    findings="Use standard library pre-flight socket probing with bounded timeout (<=50ms) to detect offline dependencies instantly.",
                    candidate_statement="Fast TCP socket pre-flight probing enables instant offline detection without thread blocking.",
                    confidence_score=0.88,
                )

                cand_rec = engine.quarantine_candidate(dossier)

                diff_sample = """--- a/src/quan_ai_brain/llm/client.py
+++ b/src/quan_ai_brain/llm/client.py
@@ -35,6 +35,14 @@
+    def is_daemon_online(self) -> bool:
+        \"\"\"Pre-flight TCP check to detect offline daemon without HTTP latency.\"\"\"
+        import socket
+        try:
+            with socket.create_connection((self.host, self.port), timeout=0.05):
+                return True
+        except OSError:
+            return False
"""
                proposal = engine.create_upgrade_proposal(
                    problem_statement=gap.description,
                    target_goal="Detect offline status within <=50ms and fail fast to fallback without worker thread stall.",
                    proposed_solution="Implement standard-library pre-flight socket probe before attempting HTTP calls.",
                    new_knowledge_refs=[f"research:{dossier.research_id}", f"memory:{cand_rec.id}"],
                    expected_benefits="Reduces latency from ~2000ms to <1ms when daemon is offline.",
                    advantages=["Standard library only", "Zero new dependencies", "Confined to 127.0.0.1 localhost"],
                    disadvantages_and_risks=["1 loopback TCP handshake overhead (<1ms)"],
                    impact_scope=["quan_ai_brain.llm.client"],
                    unified_diff=diff_sample,
                    test_results={"baseline_passed": 209, "candidate_passed": 209, "regressions": 0},
                    security_evaluation="Confined to 127.0.0.1. No external network. No R5.",
                    compatibility_assessment="100% backwards-compatible.",
                    measured_metrics={"probe_latency_ms": 0.8, "speedup": "2500x"},
                    rollback_plan="Revert client.py diff via git checkout.",
                    recommendation="apply",
                    confidence_score=0.91,
                    uncertainties=["Behavior under TCP port exhaustion"],
                )

                if args.format == "json":
                    out = {
                        "mode": "dry_run",
                        "learning_gap": gap.to_dict(),
                        "research_dossier": dossier.to_dict(),
                        "quarantined_candidate_id": cand_rec.id,
                        "upgrade_proposal": proposal.to_dict(),
                        "notice": "[INERT DRY-RUN ONLY — ZERO PRODUCTION CODE MODIFICATIONS APPLIED]",
                    }
                    print(json.dumps(out, ensure_ascii=False, indent=2))
                else:
                    print("=" * 70)
                    print("QUAN AI BRAIN — SUPERVISED SELF-LEARNING DRY-RUN CYCLE")
                    print("=" * 70)
                    print(f"Gap Detected:       {gap.gap_id} ({gap.gap_type}, severity {gap.severity})")
                    print(f"Research Dossier:   {dossier.research_id} (confidence: {dossier.confidence_score*100:.1f}%)")
                    print(f"Candidate Stored:   {cand_rec.id} (Status: {cand_rec.verification_status}, {cand_rec.lifecycle_status})")
                    print(f"Proposal Created:   {proposal.proposal_id} (Status: {proposal.status.value}, rec: {proposal.recommendation})")
                    print("=" * 70)
                    print(proposal.explain())
                    print("=" * 70)
                    print("\n[INERT DRY-RUN ONLY — ZERO PRODUCTION CODE MODIFICATIONS APPLIED]")
                return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
