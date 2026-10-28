"""Scaling package (V30) — horizontal scaling, performance, DR, monitoring, BI.

SIMULATION NOTICE: all modules in this package are in-process, stdlib-only
simulations. They do NOT open ports, run servers, or touch Docker/K8s/Redis.
Disaster recovery only writes to caller-provided directories (tests use
tmp_path); it never touches brain.db or the real data/ directory.
"""

__version__ = "V30.0"
