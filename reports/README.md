# Automated handoff reports

The project writes `HANDOFF_LATEST.md`, a timestamped archive, and `TEST_RUN_LATEST.txt` here whenever `python tools/validate_and_report.py` runs.

Do not copy sample report files from the build environment into the actual Windows workspace. Generate a fresh report on the target machine after merging the code and running tests. Review the report before sharing it.
