# Safe Merge Instructions — QUAN AI BRAIN Sprint 1

This package is a starter overlay, not a replacement of the entire existing workspace.

## Before merging

1. Keep the current workspace at `E:\AI\QUAN AI BRAIN` unchanged until a backup exists.
2. Extract this ZIP into a separate staging folder first.
3. Compare the files in the extracted package with the current workspace. Do not overwrite any existing file without reviewing a diff.
4. Only merge the new package files into the project root after review. Do not copy `.venv`, `data`, `logs`, database files, or archived handoff reports from the staging environment.
5. Preserve the existing `docs\SYSTEM_BASELINE.md`, `docs\ARCHITECTURE_GAP_ANALYSIS.md`, `docs\NEXT_STEPS.md`, and detailed technical report. The handoff generator can include these allowlisted Markdown files when they are present in the actual workspace.

## Suggested PowerShell sequence

Run from the actual workspace only after the package has been extracted to a reviewed staging directory:

```powershell
Set-Location 'E:\AI\QUAN AI BRAIN'
Get-Location
Test-Path '.git'
Test-Path 'pyproject.toml'
Test-Path '.venv\Scripts\python.exe'
```

Do not run `git init` blindly. If `.git` already exists, review `git status` first. If the workspace has no repository, confirm with the owner before initializing it.

## Install and verify after merge

Use the existing Python 3.11 x64 installation if available. Create the virtual environment only if one does not already exist and has been confirmed to belong to this project.

```powershell
py -3.11 --version
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe tools\validate_and_report.py
```

If `.venv` already exists, do not recreate it automatically; inspect its Python version and dependencies first.

## Report for ChatGPT continuity

After each completed coding session, review the diff, then run:

```powershell
.\.venv\Scripts\python.exe tools\validate_and_report.py
```

Send `reports\HANDOFF_LATEST.md` back through the chat. The report includes the test result, safe file inventory, Git status, project status and allowlisted project documents. Review the report before sharing it. Never put credentials or secret values into Markdown project documents.
