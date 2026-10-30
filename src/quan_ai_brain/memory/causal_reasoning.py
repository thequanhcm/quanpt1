"""V17 — Causal Reasoning & Counterfactual Memory.

Suy luận nhân quả (causal reasoning) và ghi nhớ các kịch bản "what-if" (counterfactual memory).
"""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CausalNode:
    """Causal event/node."""
    causal_id: str
    event_type: str  # 'cause', 'effect', 'event', 'outcome'
    description: str
    timestamp: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CausalEdge:
    """Causal relationship."""
    source_id: str
    target_id: str
    link_type: str  # 'direct', 'indirect', 'contributory', 'necessary', 'sufficient'
    strength: float  # 0-1
    evidence: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CausalChain:
    """Causal chain between events."""
    start_id: str
    end_id: str
    chain: list[str]  # sequence of event IDs
    total_strength: float
    mechanism: str | None


class CausalGraph:
    """Causal graph for reasoning about cause-effect relationships."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
        self._load_graph()
    
    def _create_schema(self):
        """Create causal graph schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS causal_nodes (
                causal_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                properties TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS causal_edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                link_type TEXT NOT NULL,
                strength REAL NOT NULL,
                evidence TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id),
                FOREIGN KEY (source_id) REFERENCES causal_nodes(causal_id),
                FOREIGN KEY (target_id) REFERENCES causal_nodes(causal_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_edges_source ON causal_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON causal_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON causal_nodes(event_type);
        """)
        self._conn.commit()
    
    def _load_graph(self):
        """Load graph from database."""
        self._nodes = {}
        self._edges = []
        self._adjacency = defaultdict(list)
        self._reverse_adjacency = defaultdict(list)
        
        for row in self._conn.execute("SELECT causal_id, event_type, description, timestamp, properties, created_at FROM causal_nodes"):
            node = CausalNode(
                causal_id=row[0],
                event_type=row[1],
                description=row[2],
                timestamp=row[3],
                properties=json.loads(row[4]),
                created_at=row[5]
            )
            self._nodes[node.causal_id] = node
        
        for row in self._conn.execute("SELECT source_id, target_id, link_type, strength, evidence, created_at FROM causal_edges"):
            edge = CausalEdge(
                source_id=row[0],
                target_id=row[1],
                link_type=row[2],
                strength=row[3],
                evidence=json.loads(row[4]) if row[4] else [],
                created_at=row[5]
            )
            self._edges.append(edge)
            self._adjacency[edge.source_id].append(edge)
            self._reverse_adjacency[edge.target_id].append(edge)
    
    def add_causal_event(self, event_id: str, event_type: str, description: str, 
                        timestamp: str, properties: dict[str, Any] | None = None) -> bool:
        """Add causal event."""
        if event_id in self._nodes:
            return False
        
        node = CausalNode(
            causal_id=event_id,
            event_type=event_type,
            description=description,
            timestamp=timestamp,
            properties=properties or {}
        )
        
        self._nodes[event_id] = node
        self._conn.execute(
            "INSERT INTO causal_nodes (causal_id, event_type, description, timestamp, properties, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, event_type, description, timestamp, json.dumps(node.properties), node.created_at)
        )
        self._conn.commit()
        return True
    
    def add_causal_link(self, cause_id: str, effect_id: str, link_type: str = 'direct',
                       strength: float = 0.8, evidence: list[str] | None = None) -> bool:
        """Add causal link between events."""
        if cause_id not in self._nodes or effect_id not in self._nodes:
            return False
        
        if link_type not in ['direct', 'indirect', 'contributory', 'necessary', 'sufficient']:
            return False
        
        if not (0 <= strength <= 1):
            return False
        
        edge = CausalEdge(
            source_id=cause_id,
            target_id=effect_id,
            link_type=link_type,
            strength=strength,
            evidence=evidence or []
        )
        
        self._edges.append(edge)
        self._adjacency[cause_id].append(edge)
        self._reverse_adjacency[effect_id].append(edge)
        
        self._conn.execute(
            "INSERT OR REPLACE INTO causal_edges (source_id, target_id, link_type, strength, evidence, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (cause_id, effect_id, link_type, strength, json.dumps(evidence or []), edge.created_at)
        )
        self._conn.commit()
        return True
    
    def find_causes(self, event_id: str, depth: int = 3) -> list[dict]:
        """Find causes (upstream) of an event."""
        if event_id not in self._nodes:
            return []
        
        causes = []
        visited = {event_id}
        queue = [(event_id, 0)]
        
        while queue:
            current, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            
            for edge in self._reverse_adjacency.get(current, []):
                cause_id = edge.source_id
                if cause_id in visited:
                    continue
                
                visited.add(cause_id)
                causes.append({
                    'event_id': cause_id,
                    'event': self._nodes[cause_id],
                    'link_type': edge.link_type,
                    'strength': edge.strength,
                    'distance': current_depth + 1
                })
                
                queue.append((cause_id, current_depth + 1))
        
        return sorted(causes, key=lambda x: x['strength'], reverse=True)
    
    def find_effects(self, event_id: str, depth: int = 3) -> list[dict]:
        """Find effects (downstream) of an event."""
        if event_id not in self._nodes:
            return []
        
        effects = []
        visited = {event_id}
        queue = [(event_id, 0)]
        
        while queue:
            current, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue
            
            for edge in self._adjacency.get(current, []):
                effect_id = edge.target_id
                if effect_id in visited:
                    continue
                
                visited.add(effect_id)
                effects.append({
                    'event_id': effect_id,
                    'event': self._nodes[effect_id],
                    'link_type': edge.link_type,
                    'strength': edge.strength,
                    'distance': current_depth + 1
                })
                
                queue.append((effect_id, current_depth + 1))
        
        return sorted(effects, key=lambda x: x['strength'], reverse=True)
    
    def find_causal_chain(self, start_id: str, end_id: str) -> CausalChain | None:
        """Find causal chain between two events."""
        if start_id not in self._nodes or end_id not in self._nodes:
            return None
        
        if start_id == end_id:
            return CausalChain(
                start_id=start_id,
                end_id=end_id,
                chain=[start_id],
                total_strength=1.0,
                mechanism=None
            )
        
        # BFS to find path
        visited = {start_id}
        queue = [(start_id, [start_id], 1.0)]
        
        while queue:
            current, path, strength = queue.pop(0)
            
            for edge in self._adjacency.get(current, []):
                next_id = edge.target_id
                if next_id == end_id:
                    total_strength = strength * edge.strength
                    return CausalChain(
                        start_id=start_id,
                        end_id=end_id,
                        chain=path + [next_id],
                        total_strength=total_strength,
                        mechanism=self._infer_mechanism(path + [next_id])
                    )
                
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id], strength * edge.strength))
        
        return None  # No chain found
    
    def _infer_mechanism(self, chain: list[str]) -> str | None:
        """Infer causal mechanism from chain."""
        if len(chain) < 2:
            return None
        
        # Simple heuristic based on event types
        event_types = [self._nodes[nid].event_type for nid in chain if nid in self._nodes]
        
        if 'cause' in event_types and 'effect' in event_types:
            return "Direct cause-effect relationship"
        elif len(set(event_types)) == 1:
            return f"Chain of {event_types[0]} events"
        else:
            return "Mixed causal chain"
    
    def infer_causality(self, event1_id: str, event2_id: str, context: dict[str, Any] | None = None) -> dict:
        """Infer causal relationship between two events."""
        if event1_id not in self._nodes or event2_id not in self._nodes:
            return {'causality': 'unknown', 'strength': 0.0, 'evidence': []}
        
        event1 = self._nodes[event1_id]
        event2 = self._nodes[event2_id]
        
        # Check temporal ordering
        try:
            t1 = datetime.fromisoformat(event1.timestamp)
            t2 = datetime.fromisoformat(event2.timestamp)
            temporal_order = t1 < t2
        except:
            temporal_order = True  # Assume valid if can't parse
        
        # Check existing causal link
        chain = self.find_causal_chain(event1_id, event2_id)
        
        if chain:
            return {
                'causality': 'causal',
                'strength': chain.total_strength,
                'evidence': ['existing_chain'],
                'mechanism': chain.mechanism
            }
        
        # Check reverse link
        reverse_chain = self.find_causal_chain(event2_id, event1_id)
        if reverse_chain:
            return {
                'causality': 'reverse_causal',
                'strength': reverse_chain.total_strength,
                'evidence': ['reverse_chain']
            }
        
        # Heuristic inference
        evidence = []
        strength = 0.0
        
        if temporal_order:
            evidence.append('temporal_order')
            strength += 0.3
        
        # Check for correlation (simplified)
        if event1.event_type == event2.event_type:
            evidence.append('similar_type')
            strength += 0.2
        
        if context and context.get('co_occurrence', 0) > 0.7:
            evidence.append('high_co_occurrence')
            strength += 0.3
        
        strength = min(1.0, strength)
        
        return {
            'causality': 'possible' if strength > 0.4 else 'uncertain',
            'strength': strength,
            'evidence': evidence
        }
    
    def calculate_causal_strength(self, cause_id: str, effect_id: str) -> float:
        """Calculate causal strength between cause and effect."""
        chain = self.find_causal_chain(cause_id, effect_id)
        if chain:
            return chain.total_strength
        
        # Check direct edge
        for edge in self._adjacency.get(cause_id, []):
            if edge.target_id == effect_id:
                return edge.strength
        
        return 0.0
    
    def identify_root_cause(self, effect_id: str, max_depth: int = 5) -> dict | None:
        """Identify root cause of an effect."""
        causes = self.find_causes(effect_id, depth=max_depth)
        if not causes:
            return None
        
        # Find the furthest upstream cause
        root_cause = max(causes, key=lambda x: x['distance'])
        
        # Get full chain
        chain = self.find_causal_chain(root_cause['event_id'], effect_id)
        
        return {
            'root_cause_id': root_cause['event_id'],
            'root_cause': root_cause['event'],
            'chain': chain.chain if chain else [],
            'total_strength': chain.total_strength if chain else 0.0
        }
    
    def predict_effects(self, cause_id: str, context: dict[str, Any] | None = None) -> list[dict]:
        """Predict effects of a cause."""
        effects = self.find_effects(cause_id, depth=3)
        
        # Filter by context if provided
        if context:
            filtered = []
            for effect in effects:
                # Simple filtering based on context
                if context.get('filter_type') and effect['event'].event_type != context['filter_type']:
                    continue
                filtered.append(effect)
            effects = filtered
        
        return effects
    
    def find_common_causal_patterns(self, min_frequency: int = 2) -> list[dict]:
        """Find common causal patterns."""
        link_types = defaultdict(int)
        
        for edge in self._edges:
            link_types[edge.link_type] += 1
        
        patterns = []
        for link_type, count in link_types.items():
            if count >= min_frequency:
                patterns.append({
                    'pattern_type': link_type,
                    'frequency': count,
                    'percentage': count / len(self._edges) * 100 if self._edges else 0
                })
        
        return sorted(patterns, key=lambda x: x['frequency'], reverse=True)
    
    def find_confounding_factors(self, cause_id: str, effect_id: str) -> list[str]:
        """Find potential confounding factors."""
        confounders = []
        
        # Find events that have edges to both cause and effect
        cause_causes = set(e.source_id for e in self._reverse_adjacency.get(cause_id, []))
        effect_causes = set(e.source_id for e in self._reverse_adjacency.get(effect_id, []))
        
        potential_confounders = cause_causes.intersection(effect_causes)
        confounders.extend(potential_confounders)
        
        return confounders
    
    def find_mediating_variables(self, cause_id: str, effect_id: str) -> list[str]:
        """Find mediating variables in causal chain."""
        chain = self.find_causal_chain(cause_id, effect_id)
        if not chain or len(chain.chain) < 3:
            return []
        
        # Mediators are intermediate nodes (excluding start and end)
        return chain.chain[1:-1]
    
    def close(self):
        """Close database connection."""
        self._conn.close()