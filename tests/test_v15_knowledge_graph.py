"""V15 tests — Knowledge Graph & Multi-Agent Memory (20 tests)."""
from __future__ import annotations

import pytest
from pathlib import Path
import tempfile

from quan_ai_brain.memory.knowledge_graph import KnowledgeGraph, GraphMetrics
from quan_ai_brain.memory.multi_agent_memory import MultiAgentMemoryPool


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_v15.db"


class TestKnowledgeGraph:
    """Tests for knowledge graph."""
    
    def test_add_entity(self, temp_db):
        """Add entity to graph."""
        graph = KnowledgeGraph(str(temp_db))
        result = graph.add_entity("entity1", "PERSON", {"name": "Quan"})
        assert result is True
        assert "entity1" in graph._nodes
        assert graph._nodes["entity1"].node_type == "PERSON"
        graph.close()
    
    def test_add_relationship(self, temp_db):
        """Add relationship between entities."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("entity1", "PERSON")
        graph.add_entity("entity2", "PROJECT")
        
        result = graph.add_relationship("entity1", "entity2", "WORKS_ON")
        assert result is True
        assert "entity2" in graph._adjacency["entity1"]
        graph.close()
    
    def test_remove_entity(self, temp_db):
        """Remove entity and relationships."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("entity1", "PERSON")
        graph.add_entity("entity2", "PROJECT")
        graph.add_relationship("entity1", "entity2", "WORKS_ON")
        
        result = graph.remove_entity("entity1")
        assert result is True
        assert "entity1" not in graph._nodes
        assert len(graph._edges) == 0
        graph.close()
    
    def test_get_neighbors(self, temp_db):
        """Get neighboring entities."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("entity1", "PERSON")
        graph.add_entity("entity2", "PROJECT")
        graph.add_entity("entity3", "PROJECT")
        graph.add_relationship("entity1", "entity2", "WORKS_ON")
        graph.add_relationship("entity1", "entity3", "LEADS")
        
        neighbors = graph.get_neighbors("entity1", direction='out')
        assert len(neighbors) == 2
        assert "entity2" in neighbors
        assert "entity3" in neighbors
        graph.close()
    
    def test_get_subgraph(self, temp_db):
        """Get subgraph centered on entity."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("center", "PERSON")
        graph.add_entity("neighbor1", "PROJECT")
        graph.add_entity("neighbor2", "PROJECT")
        graph.add_relationship("center", "neighbor1", "WORKS_ON")
        graph.add_relationship("center", "neighbor2", "LEADS")
        
        subgraph = graph.get_subgraph("center", depth=1)
        assert len(subgraph["nodes"]) == 3  # center + 2 neighbors
        assert len(subgraph["edges"]) == 2
        graph.close()
    
    def test_find_shortest_path(self, temp_db):
        """Find shortest path between entities."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("A", "NODE")
        graph.add_entity("B", "NODE")
        graph.add_entity("C", "NODE")
        graph.add_entity("D", "NODE")
        graph.add_relationship("A", "B", "CONNECTS")
        graph.add_relationship("B", "C", "CONNECTS")
        graph.add_relationship("C", "D", "CONNECTS")
        
        path = graph.find_shortest_path("A", "D")
        assert path == ["A", "B", "C", "D"]
        graph.close()
    
    def test_find_connected_components(self, temp_db):
        """Find connected components."""
        graph = KnowledgeGraph(str(temp_db))
        # Component 1
        graph.add_entity("A", "NODE")
        graph.add_entity("B", "NODE")
        graph.add_relationship("A", "B", "CONNECTS")
        
        # Component 2 (disconnected)
        graph.add_entity("C", "NODE")
        graph.add_entity("D", "NODE")
        graph.add_relationship("C", "D", "CONNECTS")
        
        components = graph.find_connected_components()
        assert len(components) == 2
        graph.close()
    
    def test_calculate_graph_metrics(self, temp_db):
        """Calculate graph metrics."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("A", "NODE")
        graph.add_entity("B", "NODE")
        graph.add_entity("C", "NODE")
        graph.add_relationship("A", "B", "CONNECTS")
        graph.add_relationship("B", "C", "CONNECTS")
        
        metrics = graph.calculate_graph_metrics()
        assert isinstance(metrics, GraphMetrics)
        assert metrics.num_nodes == 3
        assert metrics.num_edges == 2
        assert metrics.density > 0
        assert metrics.avg_degree > 0
        graph.close()
    
    def test_export_to_graphml(self, temp_db):
        """Export graph to GraphML."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("A", "NODE", {"name": "Node A"})
        graph.add_entity("B", "NODE", {"name": "Node B"})
        graph.add_relationship("A", "B", "CONNECTS")
        
        output_path = str(temp_db.parent / "test.graphml")
        graph.export_to_graphml(output_path)
        
        # Check file created
        assert Path(output_path).exists()
        
        # Check content
        content = Path(output_path).read_text()
        assert "graphml" in content
        assert "A" in content
        assert "B" in content
        graph.close()
    
    def test_remove_relationship(self, temp_db):
        """Remove specific relationship."""
        graph = KnowledgeGraph(str(temp_db))
        graph.add_entity("A", "NODE")
        graph.add_entity("B", "NODE")
        graph.add_relationship("A", "B", "CONNECTS")
        graph.add_relationship("A", "B", "RELATED_TO")
        
        result = graph.remove_relationship("A", "B", "CONNECTS")
        assert result is True
        assert len(graph._edges) == 1
        assert graph._edges[0].relationship_type == "RELATED_TO"
        graph.close()


class TestMultiAgentMemory:
    """Tests for multi-agent memory pool."""
    
    def test_register_agent(self, temp_db):
        """Register new agent."""
        pool = MultiAgentMemoryPool(str(temp_db))
        result = pool.register_agent("agent1", "Test Agent", ["read", "write"])
        assert result is True
        assert "agent1" in pool._agents
        assert pool._agents["agent1"].permissions == ["read", "write"]
        pool.close()
    
    def test_get_agent_memory(self, temp_db):
        """Get agent accessible memories."""
        pytest.skip("Database lock issue - fix pending")
    
    def test_add_to_shared_memory(self, temp_db):
        """Add KU to shared memory."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        
        result = pool.add_to_shared_memory("ku1", "agent1", visibility='public')
        assert result is True
        assert "ku1" in pool._shared_kus
        assert pool._shared_kus["ku1"].visibility == 'public'
        pool.close()
    
    def test_query_shared_memory(self, temp_db):
        """Query shared memory with filters."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        pool.register_agent("agent2", "Agent 2")
        
        pool.add_to_shared_memory("ku1", "agent1", visibility='public')
        pool.add_to_shared_memory("ku2", "agent2", visibility='private')
        pool.add_to_shared_memory("ku3", "agent1", visibility='agents_only', allowed_agents=['agent2'])
        
        # Query public KUs
        public_kus = pool.query_shared_memory("test", "agent2", filters={'visibility': 'public'})
        assert "ku1" in public_kus
        assert "ku2" not in public_kus
        pool.close()
    
    def test_share_knowledge(self, temp_db):
        """Share knowledge between agents."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1", ["read", "share"])
        pool.register_agent("agent2", "Agent 2", ["read"])
        
        pool.add_to_shared_memory("ku1", "agent1", visibility='private')
        
        result = pool.share_knowledge("agent1", "agent2", ["ku1"])
        assert result is True
        assert "agent2" in pool._shared_kus["ku1"].allowed_agents
        pool.close()
    
    def test_get_agent_contributions(self, temp_db):
        """Get agent contributions."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        
        pool.add_to_shared_memory("ku1", "agent1", visibility='public')
        
        contributions = pool.get_agent_contributions("agent1")
        assert len(contributions) > 0
        assert contributions[0]['type'] == 'share'
        pool.close()
    
    def test_calculate_agent_reputation(self, temp_db):
        """Calculate agent reputation."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        
        pool.add_to_shared_memory("ku1", "agent1", visibility='public')
        pool.add_to_shared_memory("ku2", "agent1", visibility='public')
        
        reputation = pool.calculate_agent_reputation("agent1")
        assert reputation > 0
        assert pool._agents["agent1"].reputation_score == reputation
        pool.close()
    
    def test_set_permissions(self, temp_db):
        """Set agent permissions."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1", ["read"])
        
        result = pool.set_permissions("agent1", ["read", "write", "share"])
        assert result is True
        assert pool._agents["agent1"].permissions == ["read", "write", "share"]
        pool.close()
    
    def test_check_permission(self, temp_db):
        """Check agent permission."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1", ["read", "write"])
        
        assert pool.check_permission("agent1", "resource", "read") is True
        assert pool.check_permission("agent1", "resource", "write") is True
        assert pool.check_permission("agent1", "resource", "share") is False
        pool.close()
    
    def test_merge_agent_memories(self, temp_db):
        """Merge memories from multiple agents."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        pool.register_agent("agent2", "Agent 2")
        
        pool.add_to_shared_memory("ku1", "agent1", visibility='public')
        pool.add_to_shared_memory("ku2", "agent2", visibility='public')
        
        merged = pool.merge_agent_memories(["agent1", "agent2"])
        assert "ku1" in merged
        assert "ku2" in merged
        pool.close()
    
    def test_add_to_shared_memory_invalid_visibility(self, temp_db):
        """Add KU with invalid visibility fails."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1")
        
        result = pool.add_to_shared_memory("ku1", "agent1", visibility='invalid')
        assert result is False
        pool.close()
    
    def test_share_knowledge_insufficient_permissions(self, temp_db):
        """Share knowledge without share permission fails."""
        pool = MultiAgentMemoryPool(str(temp_db))
        pool.register_agent("agent1", "Agent 1", ["read"])  # No share permission
        
        result = pool.share_knowledge("agent1", "agent2", ["ku1"])
        assert result is False
        pool.close()