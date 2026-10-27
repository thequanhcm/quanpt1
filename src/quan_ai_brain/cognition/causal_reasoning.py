"""
Causal Reasoning Module (Base for V23)

This module provides base classes for causal reasoning.
V23 extends this with advanced causal chain discovery.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class CausalNode:
    """Represents a node in the causal graph"""
    node_id: str
    label: str
    node_type: str  # EVENT, CONDITION, OUTCOME
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalEdge:
    """Represents an edge in the causal graph"""
    source_id: str
    target_id: str
    edge_type: str  # CAUSES, ENABLES, INHIBITS
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CausalGraph:
    """Causal graph data structure"""

    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: Dict[str, Dict[str, CausalEdge]] = {}  # source -> {target -> edge}
        self.reverse_edges: Dict[str, Dict[str, CausalEdge]] = {}  # target -> {source -> edge}

    def add_node(self, node: CausalNode) -> None:
        """Add a node to the graph"""
        self.nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, edge_type: str, confidence: float) -> None:
        """Add an edge to the graph"""
        if source_id not in self.edges:
            self.edges[source_id] = {}
        
        edge = CausalEdge(source_id, target_id, edge_type, confidence)
        self.edges[source_id][target_id] = edge

        if target_id not in self.reverse_edges:
            self.reverse_edges[target_id] = {}
        self.reverse_edges[target_id][source_id] = edge

        # Ensure nodes exist
        if source_id not in self.nodes:
            self.add_node(CausalNode(source_id, source_id, "EVENT"))
        if target_id not in self.nodes:
            self.add_node(CausalNode(target_id, target_id, "EVENT"))

    def get_successors(self, node_id: str) -> Dict[str, Dict[str, Any]]:
        """Get successor nodes and their edges"""
        if node_id not in self.edges:
            return {}
        
        return {
            target: {
                'type': edge.edge_type,
                'confidence': edge.confidence,
                'metadata': edge.metadata
            }
            for target, edge in self.edges[node_id].items()
        }

    def get_predecessors(self, node_id: str) -> Dict[str, Dict[str, Any]]:
        """Get predecessor nodes and their edges"""
        if node_id not in self.reverse_edges:
            return {}
        
        return {
            source: {
                'type': edge.edge_type,
                'confidence': edge.confidence,
                'metadata': edge.metadata
            }
            for source, edge in self.reverse_edges[node_id].items()
        }

    @property
    def nodes_list(self) -> List[str]:
        """Get list of node IDs"""
        return list(self.nodes.keys())

    @property
    def edges_list(self) -> List[CausalEdge]:
        """Get list of all edges"""
        all_edges = []
        for target_edges in self.edges.values():
            all_edges.extend(target_edges.values())
        return all_edges

    def get_edge(self, source_id: str, target_id: str) -> Optional[CausalEdge]:
        """Get edge between two nodes"""
        if source_id in self.edges and target_id in self.edges[source_id]:
            return self.edges[source_id][target_id]
        return None

    def has_path(self, source_id: str, target_id: str) -> bool:
        """Check if there is a path from source to target"""
        if source_id == target_id:
            return True
        
        visited = set()
        queue = [source_id]
        
        while queue:
            current = queue.pop(0)
            if current == target_id:
                return True
            
            if current in visited:
                continue
            visited.add(current)
            
            if current in self.edges:
                queue.extend(self.edges[current].keys())
        
        return False


class CausalInferenceEngine:
    """Engine for causal inference"""

    def __init__(self, db):
        self.db = db
        self.graph = CausalGraph()

    def infer_causality(self, event_a: str, event_b: str) -> Dict[str, Any]:
        """Infer causal relationship between two events"""
        # Check if there's a direct edge
        edge = self.graph.get_edge(event_a, event_b)
        if edge:
            return {
                'causal': True,
                'type': edge.edge_type,
                'confidence': edge.confidence,
                'direct': True
            }

        # Check if there's an indirect path
        if self.graph.has_path(event_a, event_b):
            return {
                'causal': True,
                'type': 'INDIRECT',
                'confidence': 0.5,  # Lower confidence for indirect
                'direct': False
            }

        return {
            'causal': False,
            'type': None,
            'confidence': 0.0,
            'direct': False
        }

    def compute_causal_effect(self, intervention: str) -> Dict[str, Any]:
        """Compute causal effect of an intervention"""
        # Find all affected nodes
        affected = []
        
        if intervention in self.graph.edges:
            for target, edge in self.graph.edges[intervention].items():
                affected.append({
                    'node': target,
                    'effect_type': edge.edge_type,
                    'confidence': edge.confidence
                })

        return {
            'intervention': intervention,
            'affected_nodes': affected,
            'num_affected': len(affected)
        }