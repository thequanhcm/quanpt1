# Antigravity workflow for QUAN AI BRAIN

At the end of each work session, the coding agent must:

1. Restrict file changes to the `QUAN AI BRAIN` workspace unless the owner explicitly approves otherwise.
2. Show the proposed diff before applying changes that affect existing files.
3. Never open, echo, copy, or report secret values from `.env`, keys, certificates, credential stores, databases, or environment variables.
4. Run the smallest relevant tests, then run:
   `python tools/validate_and_report.py`
5. Review `reports/HANDOFF_LATEST.md` and verify that it truthfully distinguishes implemented, tested, inferred, and not implemented features.
6. Provide the owner the report file path, test summary, changed-file summary, known failures, risks, and next recommended task.
7. Do not state a test passed unless output shows it passed. Do not state integration is complete until the actual external system has been tested.

## Standard handoff prompt

"Review the current QUAN AI BRAIN code and project status. Work only on the next smallest safe and testable increment. Do not touch sibling projects, do not open or log secrets, and do not run production-changing tools. Before modifying existing files, show the plan and diff. After changes, run tests and `python tools/validate_and_report.py`. Ensure `reports/HANDOFF_LATEST.md` includes the true test result, changed files, implementation status, unresolved issues, and next steps. Stop and report if evidence or permissions are missing."
