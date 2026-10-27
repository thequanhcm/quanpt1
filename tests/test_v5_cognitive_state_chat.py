"""Tests — V5 Increment 2: Pass cognitive_state into chat context when create_task=True."""
import pytest
import sys
from unittest.mock import Mock

sys.path.insert(0, 'src')

from quan_ai_brain.cognition.context_builder import PromptContextBuilder
from quan_ai_brain.cognition.models import RetrievalResult


class TestV5CognitiveStateInChat:
    """Test V5: cognitive_state passed to context in chat flow."""

    def test_cognitive_state_passed_to_context_builder(self):
        """When cognitive_state is provided, context should include evidence block."""
        builder = PromptContextBuilder()
        
        cognitive_state = {
            'beliefs': [
                {
                    'statement': 'User wants to create a task',
                    'kind': 'FACT_USER',
                    'source_ref': 'user_request',
                    'verification_status': 'USER_PROVIDED',
                    'confidence': 1.0
                }
            ],
            'contradictions': []
        }
        
        context = builder.build(
            user_query="Create a task",
            retrieval=RetrievalResult(memories=[], query="", total_found=0, total_chars=0),
            cognitive_state=cognitive_state
        )
        
        assert "[COGNITIVE EVIDENCE" in context.rendered_context
        assert "[USER_PROVIDED]" in context.rendered_context

    def test_cognitive_state_none_no_evidence_block(self):
        """When cognitive_state is None, no evidence block should appear."""
        builder = PromptContextBuilder()
        
        context = builder.build(
            user_query="Hello",
            retrieval=RetrievalResult(memories=[], query="", total_found=0, total_chars=0),
            cognitive_state=None
        )
        
        assert "[COGNITIVE EVIDENCE" not in context.rendered_context

    def test_cognitive_state_empty_no_evidence_block(self):
        """When cognitive_state is empty dict, no evidence block should appear."""
        builder = PromptContextBuilder()
        
        context = builder.build(
            user_query="Hello",
            retrieval=RetrievalResult(memories=[], query="", total_found=0, total_chars=0),
            cognitive_state={'beliefs': [], 'contradictions': []}
        )
        
        assert "[COGNITIVE EVIDENCE" not in context.rendered_context
