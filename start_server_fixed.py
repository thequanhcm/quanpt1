"""Start QUAN AI BRAIN server with NETMIND_EXTERNAL_DATA_ALLOWED=true."""
import os
import sys

# Set env var BEFORE importing server
os.environ["NETMIND_EXTERNAL_DATA_ALLOWED"] = "true"

# Now import and run server
from quan_ai_brain.web.server import run_web_server

if __name__ == "__main__":
    run_web_server()