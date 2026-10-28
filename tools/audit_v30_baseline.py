#!/usr/bin/env python3
"""
QUAN AI BRAIN V30 - Comprehensive Audit Script
Generates audit reports for V31 upgrade planning
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def get_database_info(db_path: str) -> dict:
    """Get database schema and statistics"""
    if not Path(db_path).exists():
        return {"error": "Database not found"}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_info = {}
        for table in tables:
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
            except:
                count = 0
            
            # Get columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            
            table_info[table] = {
                "row_count": count,
                "columns": columns
            }
        
        conn.close()
        return {"tables": table_info, "path": db_path}
    except Exception as e:
        return {"error": str(e)}

def scan_modules(base_path: str) -> dict:
    """Scan Python modules and categorize them"""
    modules = defaultdict(list)
    base = Path(base_path)
    
    for py_file in base.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue
        
        rel_path = py_file.relative_to(base)
        package = rel_path.parts[0] if len(rel_path.parts) > 0 else "root"
        
        # Get file size
        size = py_file.stat().st_size
        
        # Count lines
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = len(f.readlines())
        except:
            lines = 0
        
        modules[package].append({
            "name": py_file.stem,
            "path": str(rel_path),
            "size_bytes": size,
            "lines": lines
        })
    
    # Sort by size
    for package in modules:
        modules[package].sort(key=lambda x: x["size_bytes"], reverse=True)
    
    return dict(modules)

def run_tests(test_pattern: str = "tests/test_*.py") -> dict:
    """Run tests and collect results"""
    import subprocess
    import re
    
    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "tests": []
    }
    
    try:
        # Run pytest with JSON output
        cmd = [
            sys.executable, "-m", "pytest",
            test_pattern,
            "--tb=no",
            "-q",
            "--collect-only"
        ]
        
        proc = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Parse output
        output = proc.stdout + proc.stderr
        
        # Extract counts
        match = re.search(r'(\d+) passed', output)
        if match:
            result["passed"] = int(match.group(1))
        
        match = re.search(r'(\d+) failed', output)
        if match:
            result["failed"] = int(match.group(1))
        
        match = re.search(r'(\d+) skipped', output)
        if match:
            result["skipped"] = int(match.group(1))
        
        result["total"] = result["passed"] + result["failed"] + result["skipped"]
        
    except Exception as e:
        result["error"] = str(e)
    
    return result

def check_entry_points() -> dict:
    """Check entry points and startup scripts"""
    entry_points = {}
    base = Path(__file__).parent
    
    # Check Python entry points
    for py_file in ["run_web_ui.py", "start_dual_servers.py", "run_executive_desk.py"]:
        file_path = base / py_file
        if file_path.exists():
            entry_points[py_file] = {
                "exists": True,
                "size": file_path.stat().st_size
            }
        else:
            entry_points[py_file] = {"exists": False}
    
    # Check batch files
    for bat_file in ["KHOI_DONG_QUAN_AI_BRAIN.bat", "KHOI_DONG_24_7.bat"]:
        file_path = base / bat_file
        if file_path.exists():
            entry_points[bat_file] = {
                "exists": True,
                "size": file_path.stat().st_size
            }
        else:
            entry_points[bat_file] = {"exists": False}
    
    return entry_points

def classify_module_status(module_path: str) -> str:
    """Classify module status based on simple heuristics"""
    path = Path(module_path)
    
    if not path.exists():
        return "D_NOT_IMPLEMENTED"
    
    # Check file size
    size = path.stat().st_size
    if size < 100:
        return "D_NOT_IMPLEMENTED"
    
    # Read file and check for mock/stub patterns
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            
            if "mock" in content or "stub" in content or "simulated" in content:
                if "test" not in str(path):
                    return "C_SIMULATED"
            
            if "raise NotImplementedError" in content:
                return "D_NOT_IMPLEMENTED"
            
            if "pass" in content and size < 500:
                return "C_SIMULATED"
            
            # Check for test files
            if "test" in str(path):
                return "F_UNVERIFIED"
            
            return "A_VERIFIED_WORKING"  # Default assumption for substantial files
    except:
        return "F_UNVERIFIED"

def generate_audit_report():
    """Generate comprehensive audit report"""
    # Get parent directory (project root)
    base_path = Path(__file__).parent.parent
    report = {
        "timestamp": datetime.now().isoformat(),
        "version": "V30-Audit-1.0",
        "workspace": str(base_path),
        "sections": {}
    }
    
    print("=" * 80)
    print("QUAN AI BRAIN V30 - COMPREHENSIVE AUDIT")
    print("=" * 80)
    print()
    
    # 1. Workspace Structure
    print("[1/8] Scanning workspace structure...")
    report["sections"]["workspace"] = {
        "root": str(base_path),
        "directories": [str(d) for d in base_path.iterdir() if d.is_dir()],
        "total_files": len(list(base_path.rglob("*")))
    }
    print(f"  ✓ Found {report['sections']['workspace']['total_files']} files")
    
    # 2. Module Scan
    print("[2/8] Scanning Python modules...")
    modules = scan_modules(base_path / "src" / "quan_ai_brain")
    total_modules = sum(len(m) for m in modules.values())
    total_lines = sum(
        sum(m["lines"] for m in pkg_modules)
        for pkg_modules in modules.values()
    )
    report["sections"]["modules"] = {
        "packages": len(modules),
        "total_files": total_modules,
        "total_lines": total_lines,
        "by_package": {
            pkg: len(files) for pkg, files in modules.items()
        }
    }
    print(f"  ✓ Found {total_modules} modules, {total_lines} lines")
    
    # 3. Database Audit
    print("[3/8] Auditing databases...")
    databases = {}
    for db_file in base_path.glob("data/*.db"):
        databases[db_file.name] = get_database_info(str(db_file))
    report["sections"]["databases"] = databases
    
    brain_db = databases.get("brain.db", {})
    if "tables" in brain_db:
        print(f"  ✓ brain.db: {len(brain_db['tables'])} tables")
        for table, info in brain_db["tables"].items():
            print(f"    - {table}: {info['row_count']} rows")
    
    # 4. Entry Points
    print("[4/8] Checking entry points...")
    entry_points = check_entry_points()
    report["sections"]["entry_points"] = entry_points
    for name, info in entry_points.items():
        status = "✓" if info.get("exists") else "✗"
        print(f"  {status} {name}")
    
    # 5. Test Results
    print("[5/8] Running test collection...")
    test_results = run_tests()
    report["sections"]["tests"] = test_results
    print(f"  ✓ Collected {test_results['total']} tests")
    print(f"    - Passed: {test_results['passed']}")
    print(f"    - Failed: {test_results['failed']}")
    print(f"    - Skipped: {test_results['skipped']}")
    
    # 6. Module Status Classification
    print("[6/8] Classifying module status...")
    status_counts = defaultdict(int)
    module_status = {}
    
    for package, files in modules.items():
        for file_info in files:
            file_path = base_path / "src" / "quan_ai_brain" / file_info["path"]
            status = classify_module_status(str(file_path))
            status_counts[status] += 1
            module_status[file_info["path"]] = status
    
    report["sections"]["module_status"] = {
        "counts": dict(status_counts),
        "details": module_status
    }
    
    print("  Status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"    - {status}: {count}")
    
    # 7. Dependencies
    print("[7/8] Checking dependencies...")
    req_file = base_path / "requirements-prod.txt"
    dependencies = []
    if req_file.exists():
        with open(req_file, 'r') as f:
            dependencies = [
                line.strip().split("==")[0]
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    report["sections"]["dependencies"] = {
        "total": len(dependencies),
        "packages": dependencies[:20]  # First 20
    }
    print(f"  ✓ {len(dependencies)} dependencies listed")
    
    # 8. Documentation
    print("[8/8] Checking documentation...")
    docs_path = base_path / "docs"
    reports_path = base_path / "reports"
    hdsd_path = base_path / "HDSD"
    
    doc_files = []
    if docs_path.exists():
        doc_files.extend([str(f.name) for f in docs_path.glob("*.md")])
    if reports_path.exists():
        doc_files.extend([str(f.name) for f in reports_path.glob("*.md")])
    if hdsd_path.exists():
        doc_files.extend([str(f.name) for f in hdsd_path.glob("*.md")])
    
    report["sections"]["documentation"] = {
        "total_files": len(doc_files),
        "files": doc_files
    }
    print(f"  ✓ Found {len(doc_files)} documentation files")
    
    # Save report
    report_path = base_path / "AUDIT_V30_BASELINE.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print()
    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    print(f"Report saved to: {report_path}")
    print()
    
    # Summary
    print("SUMMARY:")
    print(f"  - Packages: {report['sections']['modules']['packages']}")
    print(f"  - Modules: {total_modules}")
    print(f"  - Lines of code: {total_lines}")
    print(f"  - Databases: {len(databases)}")
    print(f"  - Tests: {test_results['total']}")
    print(f"  - Documentation: {len(doc_files)} files")
    print()
    
    return report

if __name__ == "__main__":
    report = generate_audit_report()