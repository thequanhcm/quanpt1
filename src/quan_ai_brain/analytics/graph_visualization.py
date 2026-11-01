"""
Knowledge Graph Visualization Module (V25.4)

Provides:
- force-directed layout for nodes/edges given as plain list-of-dict input
  (fixed iteration count, repulsion + spring attraction, seedable RNG)
- positions export structure and JSON export
- degree / centrality computation
- shortest path (BFS) helper

Standard library only (no networkx, no numpy).

Version: V25.4
Author: QUAN AI BRAIN Team
"""

import json
import logging
import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


class KnowledgeGraphVisualizer:
    """
    Force-directed layout + analytics over a graph given as plain dicts.

    Input shapes (list of dict):
    - nodes: ``{"id": str, "label": str, "type": str, ...}``
    - edges: ``{"source": str, "target": str, "weight": float, ...}``

    Duplicate node ids and duplicate edges are ignored. Self-loops are
    ignored for layout/centrality (they contribute no distance/degree).
    """

    def __init__(
        self,
        nodes: Optional[Sequence[Dict[str, Any]]] = None,
        edges: Optional[Sequence[Dict[str, Any]]] = None,
        width: float = 800.0,
        height: float = 600.0,
        link_distance: float = 100.0,
        charge: float = 300.0,
        iterations: int = 100,
        seed: Optional[int] = 42,
    ):
        self.width = float(width)
        self.height = float(height)
        self.link_distance = float(link_distance)
        self.charge = float(charge)
        self.iterations = int(iterations)
        self.seed = seed

        self.node_ids: List[str] = []
        self.node_meta: Dict[str, Dict[str, Any]] = {}
        self._edge_set: set = set()
        self.edges: List[Tuple[str, str, float]] = []
        self.adjacency: Dict[str, List[str]] = {}
        self.undirected: Dict[str, set] = {}

        self._ingest(nodes or [], edges or [])

    # ------------------------------------------------------------------
    # Ingestion (dedupe nodes/edges, build adjacency)
    # ------------------------------------------------------------------
    def _ingest(
        self, nodes: Sequence[Dict[str, Any]], edges: Sequence[Dict[str, Any]]
    ) -> None:
        for n in nodes:
            nid = n.get('id')
            if nid is None or str(nid) in self.node_meta:
                continue
            nid = str(nid)
            meta = {k: v for k, v in n.items() if k != 'id'}
            meta.setdefault('label', nid)
            self.node_ids.append(nid)
            self.node_meta[nid] = meta

        for e in edges:
            src, tgt = e.get('source'), e.get('target')
            if src is None or tgt is None:
                continue
            src, tgt = str(src), str(tgt)
            if src == tgt:
                continue  # ignore self-loops
            # auto-register endpoints missing from the nodes list
            for nid in (src, tgt):
                if nid not in self.node_meta:
                    self.node_ids.append(nid)
                    self.node_meta[nid] = {'label': nid}
            key = (src, tgt)
            if key in self._edge_set:
                continue
            self._edge_set.add(key)
            try:
                weight = float(e.get('weight', 1.0))
            except (TypeError, ValueError):
                weight = 1.0
            self.edges.append((src, tgt, weight))
            self.adjacency.setdefault(src, []).append(tgt)
            self.adjacency.setdefault(tgt, []).append(src)
            self.undirected.setdefault(src, set()).add(tgt)
            self.undirected.setdefault(tgt, set()).add(src)

    # ------------------------------------------------------------------
    # Force-directed layout
    # ------------------------------------------------------------------
    def compute_layout(self) -> Dict[str, Dict[str, float]]:
        """
        Simple force-directed layout.

        Per iteration: pair repulsion (Coulomb-like), spring attraction along
        edges toward ``link_distance``, mild pull toward canvas center and
        displacement clamping. Random init positions come from a seeded RNG so
        the layout is reproducible for the same seed.
        """
        n = len(self.node_ids)
        positions: Dict[str, Dict[str, float]] = {}
        if n == 0:
            return positions

        rng = random.Random(self.seed)
        cx, cy = self.width / 2.0, self.height / 2.0

        pos = {
            nid: [
                cx + rng.uniform(-1.0, 1.0) * self.width * 0.25,
                cy + rng.uniform(-1.0, 1.0) * self.height * 0.25,
            ]
            for nid in self.node_ids
        }

        max_disp = self.link_distance * 0.5
        for _ in range(self.iterations):
            disp = {nid: [0.0, 0.0] for nid in self.node_ids}

            # Repulsion between every node pair (O(n^2), fine for small graphs)
            for i in range(n):
                for j in range(i + 1, n):
                    a, b = self.node_ids[i], self.node_ids[j]
                    dx = pos[a][0] - pos[b][0]
                    dy = pos[a][1] - pos[b][1]
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < 1e-6:
                        # jitter to break exact overlap
                        jitter = rng.uniform(0.1, 1.0)
                        dx, dy = jitter, -jitter
                        dist_sq = 2.0 * jitter * jitter
                    dist = math.sqrt(dist_sq)
                    repulse = self.charge / dist_sq
                    ux, uy = dx / dist, dy / dist
                    disp[a][0] += ux * repulse
                    disp[a][1] += uy * repulse
                    disp[b][0] -= ux * repulse
                    disp[b][1] -= uy * repulse

            # Spring attraction along edges
            for src, tgt, _w in self.edges:
                dx = pos[tgt][0] - pos[src][0]
                dy = pos[tgt][1] - pos[src][1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 1e-6:
                    continue
                force = (dist - self.link_distance) * 0.05
                ux, uy = dx / dist, dy / dist
                disp[src][0] += ux * force
                disp[src][1] += uy * force
                disp[tgt][0] -= ux * force
                disp[tgt][1] -= uy * force

            # Center gravity + clamped displacement
            for nid in self.node_ids:
                disp[nid][0] += (cx - pos[nid][0]) * 0.01
                disp[nid][1] += (cy - pos[nid][1]) * 0.01

                fx, fy = disp[nid]
                mag = math.sqrt(fx * fx + fy * fy)
                if mag < 1e-6:
                    continue
                lim = min(mag, max_disp)
                pos[nid][0] += fx / mag * lim
                pos[nid][1] += fy / mag * lim

        for nid in self.node_ids:
            positions[nid] = {'x': round(pos[nid][0], 4), 'y': round(pos[nid][1], 4)}
        return positions

    # ------------------------------------------------------------------
    # Degree / centrality
    # ------------------------------------------------------------------
    def compute_degree(self) -> Dict[str, int]:
        """Undirected degree per node."""
        return {nid: len(self.undirected.get(nid, ())) for nid in self.node_ids}

    def compute_centrality(self) -> Dict[str, float]:
        """Normalized degree centrality: degree / (n - 1); 0.0 when n <= 1."""
        n = len(self.node_ids)
        if n <= 1:
            return {nid: 0.0 for nid in self.node_ids}
        denom = n - 1
        return {
            nid: round(len(self.undirected.get(nid, ())) / denom, 6)
            for nid in self.node_ids
        }

    def top_central_nodes(self, k: int = 5) -> List[Tuple[str, float]]:
        """Top-k nodes by centrality, sorted desc (stable by node id)."""
        centrality = self.compute_centrality()
        ordered = sorted(centrality.items(), key=lambda kv: (-kv[1], kv[0]))
        return ordered[:max(0, int(k))]

    # ------------------------------------------------------------------
    # Shortest path (BFS, unweighted)
    # ------------------------------------------------------------------
    def shortest_path(
        self, source: str, target: str
    ) -> List[str]:
        """BFS shortest path as node-id list; empty list when unreachable."""
        source, target = str(source), str(target)
        if source not in self.node_meta or target not in self.node_meta:
            return []
        if source == target:
            return [source]
        visited = {source}
        parent: Dict[str, str] = {}
        queue = [source]
        head = 0
        while head < len(queue):
            current = queue[head]
            head += 1
            for nxt in sorted(self.undirected.get(current, ())):
                if nxt in visited:
                    continue
                visited.add(nxt)
                parent[nxt] = current
                if nxt == target:
                    path = [target]
                    while path[-1] != source:
                        path.append(parent[path[-1]])
                    path.reverse()
                    return path
                queue.append(nxt)
        return []

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_graph(self, with_positions: bool = True) -> Dict[str, Any]:
        """
        Build the export structure:
        ``{"nodes": [...], "edges": [...], "positions": {...}, "stats": {...}}``.
        Node dicts keep original metadata plus degree/centrality.
        """
        positions = self.compute_layout() if with_positions else {}
        degree = self.compute_degree()
        centrality = self.compute_centrality()

        out_nodes = []
        for nid in self.node_ids:
            node: Dict[str, Any] = {'id': nid}
            node.update(self.node_meta[nid])
            node['degree'] = degree[nid]
            node['centrality'] = centrality[nid]
            if with_positions:
                node['x'] = positions[nid]['x']
                node['y'] = positions[nid]['y']
            out_nodes.append(node)

        out_edges = [
            {'source': s, 'target': t, 'weight': w} for s, t, w in self.edges
        ]

        stats = {
            'node_count': len(self.node_ids),
            'edge_count': len(self.edges),
            'connected_components': self.count_connected_components(),
        }
        result: Dict[str, Any] = {
            'nodes': out_nodes,
            'edges': out_edges,
            'stats': stats,
        }
        if with_positions:
            result['positions'] = positions
        return result

    def to_json(self, indent: int = 2) -> str:
        """JSON string of ``export_graph()``."""
        return json.dumps(self.export_graph(with_positions=True), indent=indent)

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------
    def count_connected_components(self) -> int:
        """Number of connected components (undirected)."""
        visited: set = set()
        count = 0
        for nid in self.node_ids:
            if nid in visited:
                continue
            count += 1
            stack = [nid]
            visited.add(nid)
            while stack:
                current = stack.pop()
                for nxt in self.undirected.get(current, ()):
                    if nxt not in visited:
                        visited.add(nxt)
                        stack.append(nxt)
        return count
