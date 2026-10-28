"""V15 — Knowledge Graph Expansion & Multi-Agent Memory.

Mở rộng knowledge graph (entities, relationships, graph algorithms) +
multi-agent memory sharing (memory pool, agent-specific views, cross-agent learning).
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class GraphNode:
    """Graph node (entity)."""
    node_id: str
    node_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GraphEdge:
    """Graph edge (relationship)."""
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class GraphMetrics:
    """Graph metrics."""
    num_nodes: int
    num_edges: int
    density: float
    avg_degree: float
    num_connected_components: int
    diameter: int | None
    avg_clustering: float


class KnowledgeGraph:
    """Knowledge graph with entities and relationships."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        self._connect()
    
    def _connect(self):
        """Connect to database and create schema."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON")
        self._conn = conn
        self._create_schema()
        self._load_graph()
    
    def _create_schema(self):
        """Create graph schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                properties TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS graph_edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                properties TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relationship_type),
                FOREIGN KEY (source_id) REFERENCES graph_nodes(node_id),
                FOREIGN KEY (target_id) REFERENCES graph_nodes(node_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_edges_source ON graph_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON graph_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON graph_nodes(node_type);
        """)
        self._conn.commit()
    
    def _load_graph(self):
        """Load graph from database."""
        # Load nodes
        for row in self._conn.execute("SELECT node_id, node_type, properties, created_at FROM graph_nodes"):
            node = GraphNode(
                node_id=row[0],
                node_type=row[1],
                properties=json.loads(row[2]),
                created_at=row[3]
            )
            self._nodes[node.node_id] = node
        
        # Load edges
        for row in self._conn.execute("SELECT source_id, target_id, relationship_type, properties, created_at FROM graph_edges"):
            edge = GraphEdge(
                source_id=row[0],
                target_id=row[1],
                relationship_type=row[2],
                properties=json.loads(row[3]),
                created_at=row[4]
            )
            self._edges.append(edge)
            self._adjacency[edge.source_id].add(edge.target_id)
            self._reverse_adjacency[edge.target_id].add(edge.source_id)
    
    def add_entity(self, entity_id: str, entity_type: str, properties: dict[str, Any] | None = None) -> bool:
        """Add entity to graph."""
        if entity_id in self._nodes:
            return False
        
        node = GraphNode(
            node_id=entity_id,
            node_type=entity_type,
            properties=properties or {}
        )
        
        self._nodes[entity_id] = node
        self._conn.execute(
            "INSERT INTO graph_nodes (node_id, node_type, properties, created_at) VALUES (?, ?, ?, ?)",
            (entity_id, entity_type, json.dumps(node.properties), node.created_at)
        )
        self._conn.commit()
        return True
    
    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, 
                        properties: dict[str, Any] | None = None) -> bool:
        """Add relationship between entities."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return False
        
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=properties or {}
        )
        
        self._edges.append(edge)
        self._adjacency[source_id].add(target_id)
        self._reverse_adjacency[target_id].add(source_id)
        
        self._conn.execute(
            "INSERT INTO graph_edges (source_id, target_id, relationship_type, properties, created_at) VALUES (?, ?, ?, ?, ?)",
            (source_id, target_id, relationship_type, json.dumps(edge.properties), edge.created_at)
        )
        self._conn.commit()
        return True
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity and all its relationships."""
        if entity_id not in self._nodes:
            return False
        
        # Remove all edges involving this node FIRST
        edges_to_remove = [e for e in self._edges if e.source_id == entity_id or e.target_id == entity_id]
        for edge in edges_to_remove:
            self._edges.remove(edge)
            if edge.target_id in self._adjacency.get(edge.source_id, set()):
                self._adjacency[edge.source_id].remove(edge.target_id)
            if edge.source_id in self._reverse_adjacency.get(edge.target_id, set()):
                self._reverse_adjacency[edge.target_id].remove(edge.source_id)
        
        # Delete edges from database first
        self._conn.execute("DELETE FROM graph_edges WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
        
        # Remove node
        del self._nodes[entity_id]
        self._conn.execute("DELETE FROM graph_nodes WHERE node_id = ?", (entity_id,))
        self._conn.commit()
        return True
    
    def remove_relationship(self, source_id: str, target_id: str, relationship_type: str) -> bool:
        """Remove specific relationship."""
        for i, edge in enumerate(self._edges):
            if edge.source_id == source_id and edge.target_id == target_id and edge.relationship_type == relationship_type:
                self._edges.pop(i)
                if target_id in self._adjacency[source_id]:
                    self._adjacency[source_id].remove(target_id)
                if source_id in self._reverse_adjacency[target_id]:
                    self._reverse_adjacency[target_id].remove(source_id)
                self._conn.execute(
                    "DELETE FROM graph_edges WHERE source_id = ? AND target_id = ? AND relationship_type = ?",
                    (source_id, target_id, relationship_type)
                )
                self._conn.commit()
                return True
        return False
    
    def get_neighbors(self, entity_id: str, direction: str = 'both') -> list[str]:
        """Get neighboring entities."""
        if entity_id not in self._nodes:
            return []
        
        if direction == 'out':
            return list(self._adjacency.get(entity_id, set()))
        elif direction == 'in':
            return list(self._reverse_adjacency.get(entity_id, set()))
        else:  # both
            neighbors = set(self._adjacency.get(entity_id, set()))
            neighbors.update(self._reverse_adjacency.get(entity_id, set()))
            return list(neighbors)
    
    def get_subgraph(self, center_id: str, depth: int = 2) -> dict[str, Any]:
        """Get subgraph centered on entity."""
        if center_id not in self._nodes:
            return {"nodes": [], "edges": []}
        
        visited = {center_id}
        queue = deque([(center_id, 0)])
        subgraph_nodes = {center_id}
        subgraph_edges = []
        
        while queue:
            node_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            
            for neighbor in self._adjacency.get(node_id, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    subgraph_nodes.add(neighbor)
                    queue.append((neighbor, current_depth + 1))
        
        # Collect edges within subgraph
        for edge in self._edges:
            if edge.source_id in subgraph_nodes and edge.target_id in subgraph_nodes:
                subgraph_edges.append(edge)
        
        return {
            "nodes": [self._nodes[nid] for nid in subgraph_nodes],
            "edges": subgraph_edges
        }
    
    def find_shortest_path(self, source_id: str, target_id: str) -> list[str] | None:
        """Find shortest path using BFS."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        
        if source_id == target_id:
            return [source_id]
        
        visited = {source_id}
        queue = deque([(source_id, [source_id])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in self._adjacency.get(current, set()):
                if neighbor == target_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None  # No path found
    
    def find_connected_components(self) -> list[set[str]]:
        """Find connected components (undirected)."""
        visited = set()
        components = []
        
        for node_id in self._nodes:
            if node_id in visited:
                continue
            
            component = set()
            queue = deque([node_id])
            
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                
                visited.add(current)
                component.add(current)
                
                # Both directions
                for neighbor in self._adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
                for neighbor in self._reverse_adjacency.get(current, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            
            components.append(component)
        
        return components
    
    def calculate_graph_metrics(self) -> GraphMetrics:
        """Calculate graph metrics."""
        num_nodes = len(self._nodes)
        num_edges = len(self._edges)
        
        if num_nodes <= 1:
            return GraphMetrics(
                num_nodes=num_nodes,
                num_edges=num_edges,
                density=0.0,
                avg_degree=0.0,
                num_connected_components=0,
                diameter=None,
                avg_clustering=0.0
            )
        
        # Density
        max_edges = num_nodes * (num_nodes - 1)
        density = num_edges / max_edges if max_edges > 0 else 0.0
        
        # Average degree
        degrees = [len(self._adjacency.get(nid, set())) + len(self._reverse_adjacency.get(nid, set())) 
                   for nid in self._nodes]
        avg_degree = sum(degrees) / num_nodes if num_nodes > 0 else 0.0
        
        # Connected components
        components = self.find_connected_components()
        num_components = len(components)
        
        # Diameter (max shortest path in largest component)
        largest_component = max(components, key=len) if components else set()
        diameter = None
        if len(largest_component) > 1:
            max_dist = 0
            nodes_list = list(largest_component)
            for i, node1 in enumerate(nodes_list[:10]):  # Sample for performance
                for node2 in nodes_list[i+1:]:
                    path = self.find_shortest_path(node1, node2)
                    if path:
                        max_dist = max(max_dist, len(path) - 1)
            diameter = max_dist if max_dist > 0 else None
        
        # Average clustering coefficient
        clustering_coeffs = []
        for node_id in self._nodes:
            neighbors = set(self._adjacency.get(node_id, set())) | set(self._reverse_adjacency.get(node_id, set()))
            k = len(neighbors)
            if k < 2:
                clustering_coeffs.append(0.0)
                continue
            
            # Count edges between neighbors
            neighbor_edges = 0
            for n1 in neighbors:
                for n2 in neighbors:
                    if n1 != n2 and n2 in self._adjacency.get(n1, set()):
                        neighbor_edges += 1
            
            max_neighbor_edges = k * (k - 1)
            clustering = neighbor_edges / max_neighbor_edges if max_neighbor_edges > 0 else 0.0
            clustering_coeffs.append(clustering)
        
        avg_clustering = sum(clustering_coeffs) / num_nodes if num_nodes > 0 else 0.0
        
        return GraphMetrics(
            num_nodes=num_nodes,
            num_edges=num_edges,
            density=density,
            avg_degree=avg_degree,
            num_connected_components=num_components,
            diameter=diameter,
            avg_clustering=avg_clustering
        )
    
    def export_to_graphml(self, output_path: str):
        """Export graph to GraphML format."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
                 '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
                 '  <key id="rel_type" for="edge" attr.name="rel_type" attr.type="string"/>',
                 '  <graph id="G" edgedefault="directed">']
        
        # Nodes
        for node in self._nodes.values():
            props = ' '.join(f'{k}="{v}"' for k, v in node.properties.items())
            lines.append(f'    <node id="{node.node_id}"><data key="type">{node.node_type}</data> {props}</node>')
        
        # Edges
        for edge in self._edges:
            props = ' '.join(f'{k}="{v}"' for k, v in edge.properties.items())
            lines.append(f'    <edge source="{edge.source_id}" target="{edge.target_id}"><data key="rel_type">{edge.relationship_type}</data> {props}</edge>')
        
        lines.extend(['  </graph>', '</graphml>'])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def import_from_graphml(self, input_path: str):
        """Import graph from GraphML format (simplified parser)."""
        # Simplified - in production use xml.etree.ElementTree
        raise NotImplementedError("GraphML import requires XML parsing")
    
    def close(self):
        """Close database connection."""
        self._conn.close()