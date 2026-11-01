# Prompt to apply the Sprint 1 starter in Antigravity

Paste the following instruction into Antigravity after adding the extracted starter files to the reviewed `E:\AI\QUAN AI BRAIN` workspace. Do not grant it access to the parent `E:\AI` folder as a workspace.

---

You are working on QUAN AI BRAIN. First inspect the current workspace and read `AGENTS.md`, `docs/PROJECT_STATUS.md`, `docs/WORKSPACE_MERGE_INSTRUCTIONS.md`, and the existing baseline/architecture documents. Compare the staged Sprint 1 starter files with the current project. Do not overwrite any existing files automatically and do not touch sibling projects. Show me a merge plan and conflicts before applying changes.

After the merge is explicitly approved:
1. Check whether `.git` or `.venv` already exists before suggesting creation or replacement.
2. Use the project's Python 3.11 environment if available; do not change the machine-wide Python installation.
3. Run the Sprint 1 tests and resolve failures only within this workspace.
4. Verify the report generator excludes secrets, databases, runtime logs, and files outside this project.
5. Review the code diff and run `python tools/validate_and_report.py`.
6. Open `reports/HANDOFF_LATEST.md` and confirm it reports the real Windows workspace, actual test results, source documents, known gaps, and next steps. Do not claim hardware/integration checks were done unless tests prove them.
7. Return the report path, test count/result, changed files, unresolved issues, and next safe milestone. Stop if you find a conflicting existing file, a secret-like file, or any intended write outside the workspace.
