#!/usr/bin/env python3
"""
Battery AI — Quick Health Check Script
Kiểm tra nhanh trạng thái hệ thống Battery AI đang chạy

Usage:
    python health_check.py [--host localhost] [--port 9090]
"""

import sys
import json
import urllib.request
import urllib.error

def check(host="localhost", port=9090):
    url = f"http://{host}:{port}/api/health"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"✅ Battery AI is RUNNING at {host}:{port}")
            print(f"   Timestamp : {data.get('timestamp', 'N/A')}")
            print(f"   Database  : {'✅' if data.get('database') else '❌'}")
            services = data.get("services", {})
            for svc, ok in services.items():
                status = "✅" if ok else "⚠️ OFF"
                print(f"   {svc:12s}: {status}")
            return True
    except urllib.error.URLError as e:
        print(f"❌ Battery AI is NOT running at {host}:{port}")
        print(f"   Error: {e.reason}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    host = "localhost"
    port = 9090
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--host" and i < len(sys.argv) - 1:
            host = sys.argv[i + 1]
        elif arg == "--port" and i < len(sys.argv) - 1:
            port = int(sys.argv[i + 1])
    ok = check(host, port)
    sys.exit(0 if ok else 1)
