r"""SEC-S2: TONY Lõi Liên bang — node registry + LAN scanner + cloud connector.

Kiến trúc (owner directive 02/11/2026): PC (E:\BRAIN) = LÕI toàn quyền;
Pi5/thiết bị = nút EDGE đăng ký vào lõi; AI cloud = đầu nối CONNECTOR có
hạn ngạch. Mọi trạng thái nằm ở data/federation_nodes.db, audit đầy đủ.
"""
from quan_ai_brain.federation.node_registry import FedNode, NodeRegistry

__all__ = ["FedNode", "NodeRegistry"]
