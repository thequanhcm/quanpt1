"""V15 — Multi-Agent Memory Pool & Cross-Agent Learning."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class AgentInfo:
    """Agent information."""
    agent_id: str
    name: str
    permissions: list[str]  # ['read', 'write', 'share']
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reputation_score: float = 0.0


@dataclass
class SharedKnowledgeUnit:
    """Shared knowledge unit with visibility."""
    ku_id: str
    agent_id: str  # Owner agent
    visibility: str  # 'public', 'private', 'agents_only'
    allowed_agents: list[str] = field(default_factory=list)
    shared_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MultiAgentMemoryPool:
    """Shared memory pool for multiple agents."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._agents: dict[str, AgentInfo] = {}
        self._shared_kus: dict[str, SharedKnowledgeUnit] = {}
        self._contributions: dict[str, list[dict]] = {}  # agent_id -> [contributions]
        self._conn = sqlite3.connect(str(self.db_path))
        self._create_schema()
        self._load_agents()
    
    def _create_schema(self):
        """Create multi-agent schema."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                permissions TEXT NOT NULL,
                reputation_score REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS shared_knowledge (
                ku_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                visibility TEXT NOT NULL,
                allowed_agents TEXT,
                shared_at TEXT NOT NULL,
                PRIMARY KEY (ku_id, agent_id),
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            );
            
            CREATE TABLE IF NOT EXISTS agent_contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                contribution_type TEXT NOT NULL,
                description TEXT,
                ku_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_shared_ku ON shared_knowledge(ku_id);
            CREATE INDEX IF NOT EXISTS idx_shared_agent ON shared_knowledge(agent_id);
            CREATE INDEX IF NOT EXISTS idx_contributions_agent ON agent_contributions(agent_id);
        """)
        self._conn.commit()
    
    def _load_agents(self):
        """Load agents from database."""
        for row in self._conn.execute("SELECT agent_id, name, permissions, reputation_score, created_at FROM agents"):
            agent = AgentInfo(
                agent_id=row[0],
                name=row[1],
                permissions=json.loads(row[2]),
                reputation_score=row[3],
                created_at=row[4]
            )
            self._agents[agent.agent_id] = agent
    
    def register_agent(self, agent_id: str, name: str, permissions: list[str] | None = None) -> bool:
        """Register a new agent."""
        if agent_id in self._agents:
            return False
        
        permissions = permissions or ['read']
        agent = AgentInfo(
            agent_id=agent_id,
            name=name,
            permissions=permissions
        )
        
        self._agents[agent_id] = agent
        self._contributions[agent_id] = []
        
        self._conn.execute(
            "INSERT INTO agents (agent_id, name, permissions, reputation_score, created_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, name, json.dumps(permissions), 0.0, agent.created_at)
        )
        self._conn.commit()
        return True
    
    def get_agent_memory(self, agent_id: str) -> list[str]:
        """Get KU IDs accessible by agent."""
        if agent_id not in self._agents:
            return []
        
        accessible_kus = []
        agent = self._agents[agent_id]
        
        for ku_id, shared_ku in self._shared_kus.items():
            if shared_ku.visibility == 'public':
                accessible_kus.append(ku_id)
            elif shared_ku.visibility == 'private' and shared_ku.agent_id == agent_id:
                accessible_kus.append(ku_id)
            elif shared_ku.visibility == 'agents_only':
                if shared_ku.agent_id == agent_id or agent_id in shared_ku.allowed_agents:
                    accessible_kus.append(ku_id)
            # Also include own private KUs
            elif shared_ku.agent_id == agent_id:
                accessible_kus.append(ku_id)
        
        return accessible_kus
    
    def add_to_shared_memory(self, ku_id: str, agent_id: str, visibility: str = 'public',
                            allowed_agents: list[str] | None = None) -> bool:
        """Add KU to shared memory pool."""
        if agent_id not in self._agents:
            return False
        
        if visibility not in ['public', 'private', 'agents_only']:
            return False
        
        shared_ku = SharedKnowledgeUnit(
            ku_id=ku_id,
            agent_id=agent_id,
            visibility=visibility,
            allowed_agents=allowed_agents or []
        )
        
        self._shared_kus[ku_id] = shared_ku
        
        # Record contribution
        self._record_contribution(agent_id, 'share', f"Shared KU: {ku_id}", ku_id)
        
        self._conn.execute(
            "INSERT INTO shared_knowledge (ku_id, agent_id, visibility, allowed_agents, shared_at) VALUES (?, ?, ?, ?, ?)",
            (ku_id, agent_id, visibility, json.dumps(allowed_agents or []), shared_ku.shared_at)
        )
        self._conn.commit()
        return True
    
    def query_shared_memory(self, query: str, agent_id: str, filters: dict[str, Any] | None = None) -> list[str]:
        """Query shared memory with filters."""
        if agent_id not in self._agents:
            return []
        
        accessible_kus = set(self.get_agent_memory(agent_id))
        
        # Apply filters
        if filters:
            filtered_kus = set()
            for ku_id in accessible_kus:
                shared_ku = self._shared_kus.get(ku_id)
                if not shared_ku:
                    continue
                
                if 'visibility' in filters and shared_ku.visibility != filters['visibility']:
                    continue
                if 'owner_agent' in filters and shared_ku.agent_id != filters['owner_agent']:
                    continue
                
                filtered_kus.add(ku_id)
            
            accessible_kus = filtered_kus
        
        return list(accessible_kus)
    
    def share_knowledge(self, source_agent_id: str, target_agent_id: str, ku_ids: list[str]) -> bool:
        """Share knowledge from one agent to another."""
        if source_agent_id not in self._agents or target_agent_id not in self._agents:
            return False
        
        # Check source agent has permission to share
        if 'share' not in self._agents[source_agent_id].permissions:
            return False
        
        for ku_id in ku_ids:
            shared_ku = self._shared_kus.get(ku_id)
            if not shared_ku or shared_ku.agent_id != source_agent_id:
                continue
            
            # Update allowed agents
            if ku_id in self._shared_kus:
                if target_agent_id not in self._shared_kus[ku_id].allowed_agents:
                    self._shared_kus[ku_id].allowed_agents.append(target_agent_id)
                    self._conn.execute(
                        "UPDATE shared_knowledge SET allowed_agents = ? WHERE ku_id = ?",
                        (json.dumps(self._shared_kus[ku_id].allowed_agents), ku_id)
                    )
        
        self._conn.commit()
        
        # Record contribution
        self._record_contribution(source_agent_id, 'share_to_agent', 
                                 f"Shared {len(ku_ids)} KUs with {target_agent_id}", None)
        
        return True
    
    def get_agent_contributions(self, agent_id: str) -> list[dict]:
        """Get contributions by agent."""
        if agent_id not in self._agents:
            return []
        
        contributions = []
        for row in self._conn.execute(
            "SELECT contribution_type, description, ku_id, created_at FROM agent_contributions WHERE agent_id = ?",
            (agent_id,)
        ):
            contributions.append({
                'type': row[0],
                'description': row[1],
                'ku_id': row[2],
                'created_at': row[3]
            })
        
        return contributions
    
    def calculate_agent_reputation(self, agent_id: str) -> float:
        """Calculate agent reputation based on contributions."""
        if agent_id not in self._agents:
            return 0.0
        
        contributions = self.get_agent_contributions(agent_id)
        
        # Simple reputation calculation
        reputation = 0.0
        for contrib in contributions:
            if contrib['type'] == 'share':
                reputation += 1.0
            elif contrib['type'] == 'share_to_agent':
                reputation += 2.0
            elif contrib['type'] == 'query':
                reputation += 0.1
        
        # Update agent reputation
        self._agents[agent_id].reputation_score = reputation
        self._conn.execute(
            "UPDATE agents SET reputation_score = ? WHERE agent_id = ?",
            (reputation, agent_id)
        )
        self._conn.commit()
        
        return reputation
    
    def merge_agent_memories(self, agent_ids: list[str]) -> list[str]:
        """Merge memories from multiple agents (returns merged KU IDs)."""
        if not all(agent_id in self._agents for agent_id in agent_ids):
            return []
        
        merged_kus = set()
        for agent_id in agent_ids:
            accessible_kus = self.get_agent_memory(agent_id)
            merged_kus.update(accessible_kus)
        
        return list(merged_kus)
    
    def set_permissions(self, agent_id: str, permissions: list[str]) -> bool:
        """Set agent permissions."""
        if agent_id not in self._agents:
            return False
        
        valid_permissions = ['read', 'write', 'share']
        if not all(p in valid_permissions for p in permissions):
            return False
        
        self._agents[agent_id].permissions = permissions
        self._conn.execute(
            "UPDATE agents SET permissions = ? WHERE agent_id = ?",
            (json.dumps(permissions), agent_id)
        )
        self._conn.commit()
        return True
    
    def check_permission(self, agent_id: str, resource: str, action: str) -> bool:
        """Check if agent has permission for action on resource."""
        if agent_id not in self._agents:
            return False
        
        agent = self._agents[agent_id]
        
        if action == 'read':
            return 'read' in agent.permissions
        elif action == 'write':
            return 'write' in agent.permissions
        elif action == 'share':
            return 'share' in agent.permissions
        
        return False
    
    def _record_contribution(self, agent_id: str, contribution_type: str, 
                            description: str | None, ku_id: str | None):
        """Record agent contribution."""
        self._conn.execute(
            "INSERT INTO agent_contributions (agent_id, contribution_type, description, ku_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (agent_id, contribution_type, description, ku_id, datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()
    
    def close(self):
        """Close database connection."""
        self._conn.close()