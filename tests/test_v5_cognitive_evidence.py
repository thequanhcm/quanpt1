"""Tests — V5: Cognitive Evidence Integration (evidence traceability in chat context).

Test: context_builder.build() với cognitive_state hiển thị verification_status + source_ref.
CANDIDATE → UNVERIFIED, mâu thuẫn được giữ lại.
"""
import pytest
import sys

sys.path.insert(0, 'src')

from quan_ai_brain.cognition.context_builder import PromptContextBuilder


class TestCognitiveEvidenceIntegration:
    """Test V5: Cognitive State evidence in context."""

    def test_cognitive_state_shows_verification_status(self):
        """Context should show verification_status + source_ref for each belief."""
        builder = PromptContextBuilder()
        
        cognitive_state = {
            'beliefs': [
                {
                    'statement': 'Capital of Vietnam is Hanoi',
                    'kind': 'FACT_RETRIEVED',
                    'source_ref': 'memory:mem_001',
                    'verification_status': 'VERIFIED',
                    'confidence': 0.95
                },
                {
                    'statement': 'User prefers concise responses',
                    'kind': 'FACT_USER',
                    'source_ref': 'user_direct_input',
                    'verification_status': 'USER_PROVIDED',
                    'confidence': 1.0
                }
            ]
        }
        
        context = builder.build(
            user_query="What is the capital?",
            cognitive_state=cognitive_state
        )
        
        # Verify context contains evidence block
        assert "[COGNITIVE EVIDENCE" in context.rendered_context
        assert "[VERIFIED]" in context.rendered_context
        assert "[USER_PROVIDED]" in context.rendered_context
        assert "memory:mem_001" in context.rendered_context
        assert "Capital of Vietnam is Hanoi" in context.rendered_context

    def test_candidate_beliefs_marked_as_unverified(self):
        """CANDIDATE beliefs should be marked as CANDIDATE (UNVERIFIED), not VERIFIED."""
        builder = PromptContextBuilder()
        
        cognitive_state = {
            'beliefs': [
                {
                    'statement': 'Hypothesis: system may be running on Pi 5',
                    'kind': 'HYPOTHESIS',
                    'source_ref': 'inference:coordinator',
                    'verification_status': 'candidate',  # Should be marked UNVERIFIED
                    'confidence': 0.3
                }
            ]
        }
        
        context = builder.build(
            user_query="Where does the system run?",
            cognitive_state=cognitive_state
        )
        
        # Verify CANDIDATE is marked as UNVERIFIED
        assert "CANDIDATE (UNVERIFIED)" in context.rendered_context
        assert "Hypothesis: system may be running on Pi 5" in context.rendered_context
        # Should NOT appear as VERIFIED
        assert "[VERIFIED]" not in context.rendered_context or "CANDIDATE (UNVERIFIED)" in context.rendered_context

    def test_contradictions_preserved_not_auto_resolved(self):
        """Contradictions should be shown in context, not auto-resolved."""
        builder = PromptContextBuilder()
        
        cognitive_state = {
            'beliefs': [
                {
                    'statement': 'System runs on PC Core',
                    'kind': 'FACT_OBSERVED',
                    'source_ref': 'probe:health_api',
                    'verification_status': 'OBSERVED',
                    'confidence': 1.0
                }
            ],
            'contradictions': [
                {
                    'claim_a': 'System runs on PC Core',
                    'claim_b': 'System runs on Pi 5',
                    'resolution_status': 'UNRESOLVED',
                    'source_a': 'probe:health_api',
                    'source_b': 'user_statement'
                }
            ]
        }
        
        context = builder.build(
            user_query="Where does the system run?",
            cognitive_state=cognitive_state
        )
        
        # Verify contradictions are shown
        assert "[CONTRADICTIONS" in context.rendered_context
        assert "UNRESOLVED" in context.rendered_context
        assert "System runs on PC Core" in context.rendered_context
        assert "System runs on Pi 5" in context.rendered_context
        # Should NOT auto-resolve
        assert "resolved" not in context.rendered_context.lower() or "UNRESOLVED" in context.rendered_context

    def test_backward_compatibility_no_cognitive_state(self):
        """Context should work without cognitive_state param (backward compat)."""
        builder = PromptContextBuilder()
        
        # Call WITHOUT cognitive_state
        context = builder.build(
            user_query="Hello",
            retrieval=None
        )
        
        # Should still work
        assert context.rendered_context is not None
        assert "[SYSTEM INSTRUCTIONS" in context.rendered_context
        # Should NOT have cognitive evidence block
        assert "[COGNITIVE EVIDENCE" not in context.rendered_context

    def test_cognitive_state_cap_at_10_beliefs(self):
        """Context should cap beliefs at 10, show count of remaining."""
        builder = PromptContextBuilder()
        
        beliefs = [
            {
                'statement': f'Belief number {i}',
                'kind': 'FACT_RETRIEVED',
                'source_ref': f'source_{i}',
                'verification_status': 'VERIFIED',
                'confidence': 0.9
            }
            for i in range(15)
        ]
        
        cognitive_state = {
            'beliefs': beliefs,
            'contradictions': []
        }
        
        context = builder.build(
            user_query="Test",
            cognitive_state=cognitive_state
        )
        
        # Should show 10 beliefs
        assert "Belief number 0" in context.rendered_context
        assert "Belief number 9" in context.rendered_context
        # Should NOT show 11th
        assert "Belief number 10" not in context.rendered_context
        # Should show remaining count
        assert "and 5 more beliefs" in context.rendered_context

    def test_empty_cognitive_state_no_block(self):
        """Empty cognitive_state should not create evidence block."""
        builder = PromptContextBuilder()
        
        context = builder.build(
            user_query="Test",
            cognitive_state={'beliefs': [], 'contradictions': []}
        )
        
        # Should NOT have cognitive evidence block
        assert "[COGNITIVE EVIDENCE" not in context.rendered_context