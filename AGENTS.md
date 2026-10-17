# QUAN AI BRAIN — Persistent Engineering Rules

## Mission
Build QUAN AI BRAIN as a safety-first Digital Executive Assistant with persistent memory, auditable planning, bounded tool use, evidence-based verification, and owner-controlled learning.

## Non-negotiable constraints
- Work only inside this QUAN AI BRAIN workspace unless the owner explicitly authorizes a specific external target.
- Preserve `os_kernel`, `SKILL_BAT_AI`, `BATTERY_AI_V4`, `DC-COMMAND`, BOT projects, and all other sibling systems. Do not edit them directly.
- Never open, print, copy, or log secret values. Do not read `.env`, credentials stores, private keys/certificates, production databases, or environment variables for reporting.
- Do not add hard-coded credentials or an override secret. R5 remains hard-blocked.
- R4 requires separately verified owner approval. If an authenticated approval verifier is not configured, do not implement or simulate approval.
- Do not add real production executors, write APIs, device control, or a Windows 24/7 service without an explicit reviewed design and approval.
- Learning is not deployment. New knowledge must remain quarantined until evidence, regression tests, and the configured owner-approval path all pass.
- Never claim a feature is implemented, integrated, or verified merely because a file exists.

## Work procedure
1. Read `docs/PROJECT_STATUS.md` and the existing architecture/baseline documents before each significant change.
2. Propose the smallest safe, testable change and identify which files it will touch.
3. Inspect existing files and show a diff before replacing or overwriting them.
4. Make changes only after the plan is accepted. Prefer standard-library code until additional dependencies are justified.
5. Run focused tests; after reviewing the diff, run `python tools/validate_and_report.py`.
6. Confirm that `reports/HANDOFF_LATEST.md` exists and truthfully records the test outcome, changed files, project inventory, current status, relevant source documentation, unresolved issues, and next steps.
7. Report the handoff file path and a concise summary to the owner. The owner must upload that report back to ChatGPT to continue work with continuity.
8. Update `docs/PROJECT_STATUS.md` only when supported by test evidence. Keep implemented, tested, inferred, and not implemented states distinct.
9. If tests fail, the report must still be generated, the failure must remain visible, and no release or production action may occur.

## Current milestone
Sprint 1 safety-first walking skeleton. The initial package has not yet been validated on the owner's Windows machine. Ollama, Kernel L3, DC-COMMAND/CLAE, SKILL_BAT_AI, Battery AI V4, VDCIM, NetChat, voice, vector search, and always-on daemon integration are not yet verified by this package.
