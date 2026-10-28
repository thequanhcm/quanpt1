"""V20 — Recommendation Engine & Personalization.

Recommendation system với content-based, collaborative filtering, context-aware, personalization.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Recommendation:
    """Recommendation item."""
    item_id: str
    score: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserProfile:
    """User profile for personalization."""
    user_id: str
    interests: dict[str, float]  # category -> interest_score
    preferences: dict[str, Any]
    interaction_history: list[dict]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str | None = None


class RecommendationEngine:
    """Recommendation engine with multiple strategies."""
    
    def __init__(self):
        self._items: dict[str, dict] = {}
        self._user_profiles: dict[str, UserProfile] = {}
        self._interactions: list[dict] = []
        self._item_categories: dict[str, list[str]] = defaultdict(list)
    
    def add_item(self, item_id: str, content: dict[str, Any],
                categories: list[str] | None = None):
        """Add item to recommendation pool."""
        self._items[item_id] = {
            'content': content,
            'categories': categories or [],
            'popularity': 0,
            'rating': 0.0,
            'rating_count': 0
        }
        
        if categories:
            for cat in categories:
                self._item_categories[cat].append(item_id)
    
    def recommend_by_content(self, query_content: dict[str, Any],
                            top_k: int = 10) -> list[Recommendation]:
        """Content-based recommendation using similarity."""
        recommendations = []
        
        # Simple cosine similarity approximation
        for item_id, item in self._items.items():
            similarity = self._calculate_similarity(query_content, item['content'])
            
            if similarity > 0:
                recommendations.append(Recommendation(
                    item_id=item_id,
                    score=similarity,
                    reason=f"Similar to your query ({similarity:.2f})",
                    metadata=item['content']
                ))
        
        # Sort by score and return top_k
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def recommend_by_collaborative(self, user_id: str, top_k: int = 10) -> list[Recommendation]:
        """Collaborative filtering recommendation."""
        if user_id not in self._user_profiles:
            return []
        
        user_profile = self._user_profiles[user_id]
        user_interests = user_profile.interests
        
        # Find items matching user interests
        recommendations = []
        for item_id, item in self._items.items():
            # Calculate match score based on categories
            item_categories = item.get('categories', [])
            match_score = sum(user_interests.get(cat, 0) for cat in item_categories)
            
            # Boost by popularity
            popularity_boost = item['popularity'] * 0.1
            
            total_score = match_score + popularity_boost
            
            if total_score > 0:
                recommendations.append(Recommendation(
                    item_id=item_id,
                    score=total_score,
                    reason=f"Matches your interests",
                    metadata=item['content']
                ))
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def recommend_by_context(self, context: dict[str, Any],
                            top_k: int = 10) -> list[Recommendation]:
        """Context-aware recommendation."""
        recommendations = []
        
        context_factors = []
        if 'time_of_day' in context:
            hour = context['time_of_day']
            if 9 <= hour <= 17:
                context_factors.append('work')
            elif 18 <= hour <= 22:
                context_factors.append('personal')
            else:
                context_factors.append('late_night')
        
        if 'location' in context:
            context_factors.append(context['location'])
        
        if 'device' in context:
            context_factors.append(context['device'])
        
        for item_id, item in self._items.items():
            # Match context factors
            context_match = sum(1 for factor in context_factors 
                              if factor in item.get('content', {}).get('tags', []))
            
            if context_match > 0:
                recommendations.append(Recommendation(
                    item_id=item_id,
                    score=context_match,
                    reason=f"Relevant for current context",
                    metadata=item['content']
                ))
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def recommend_by_trending(self, time_window: int = 24,
                             top_k: int = 10) -> list[Recommendation]:
        """Trending recommendations."""
        # Filter recent interactions
        cutoff = datetime.now(timezone.utc).timestamp() - (time_window * 3600)
        recent_interactions = [
            i for i in self._interactions 
            if i.get('timestamp', 0) > cutoff
        ]
        
        # Count item popularity
        item_counts = defaultdict(int)
        for interaction in recent_interactions:
            item_id = interaction.get('item_id')
            if item_id:
                item_counts[item_id] += 1
        
        recommendations = []
        for item_id, count in item_counts.items():
            if item_id in self._items:
                item = self._items[item_id]
                recommendations.append(Recommendation(
                    item_id=item_id,
                    score=count,
                    reason=f"Trending ({count} interactions)",
                    metadata=item['content']
                ))
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def _calculate_similarity(self, content1: dict, content2: dict) -> float:
        """Calculate similarity between two content items."""
        # Simple Jaccard similarity for tags
        tags1 = set(content1.get('tags', []))
        tags2 = set(content2.get('tags', []))
        
        if not tags1 or not tags2:
            return 0.0
        
        intersection = len(tags1 & tags2)
        union = len(tags1 | tags2)
        
        return intersection / union if union > 0 else 0.0
    
    def update_item_popularity(self, item_id: str, interaction_type: str = 'view'):
        """Update item popularity based on interaction."""
        if item_id not in self._items:
            return
        
        weights = {'view': 1, 'click': 2, 'like': 5, 'share': 10}
        weight = weights.get(interaction_type, 1)
        
        self._items[item_id]['popularity'] += weight
    
    def get_all_recommendations(self, user_id: str | None = None,
                               context: dict | None = None,
                               top_k: int = 10) -> list[Recommendation]:
        """Get combined recommendations from all strategies."""
        all_recommendations = []
        
        # Content-based
        if context and 'query' in context:
            content_recs = self.recommend_by_content(context['query'], top_k * 2)
            all_recommendations.extend(content_recs)
        
        # Collaborative
        if user_id:
            collab_recs = self.recommend_by_collaborative(user_id, top_k * 2)
            all_recommendations.extend(collab_recs)
        
        # Context-aware
        if context:
            context_recs = self.recommend_by_context(context, top_k * 2)
            all_recommendations.extend(context_recs)
        
        # Trending
        trending_recs = self.recommend_by_trending(top_k)
        all_recommendations.extend(trending_recs)
        
        # Deduplicate and re-rank
        seen = set()
        unique_recs = []
        for rec in all_recommendations:
            if rec.item_id not in seen:
                seen.add(rec.item_id)
                unique_recs.append(rec)
        
        unique_recs.sort(key=lambda r: r.score, reverse=True)
        return unique_recs[:top_k]


class PersonalizationEngine:
    """Personalization engine for recommendations."""
    
    def __init__(self):
        self._profiles: dict[str, UserProfile] = {}
        self._interactions: list[dict] = []
    
    def build_user_profile(self, user_id: str,
                          initial_interests: dict[str, float] | None = None) -> UserProfile:
        """Build user profile."""
        profile = UserProfile(
            user_id=user_id,
            interests=initial_interests or {},
            preferences={},
            interaction_history=[]
        )
        
        self._profiles[user_id] = profile
        return profile
    
    def update_user_profile(self, user_id: str,
                           interactions: list[dict]) -> UserProfile | None:
        """Update user profile based on interactions."""
        if user_id not in self._profiles:
            return None
        
        profile = self._profiles[user_id]
        
        # Update interests based on interactions
        for interaction in interactions:
            item_id = interaction.get('item_id')
            interaction_type = interaction.get('type', 'view')
            categories = interaction.get('categories', [])
            
            # Record interaction
            profile.interaction_history.append({
                'item_id': item_id,
                'type': interaction_type,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            # Update interests
            weight = {'view': 0.1, 'click': 0.3, 'like': 0.7, 'share': 1.0}.get(interaction_type, 0.1)
            for category in categories:
                profile.interests[category] = profile.interests.get(category, 0) + weight
        
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        self._profiles[user_id] = profile
        
        return profile
    
    def get_personalized_recommendations(self, user_id: str,
                                        top_k: int = 10) -> list[Recommendation]:
        """Get personalized recommendations for user."""
        if user_id not in self._profiles:
            return []
        
        profile = self._profiles[user_id]
        
        # Sort items by user interests
        recommendations = []
        for item_id, item in RecommendationEngine()._items.items():
            item_categories = item.get('categories', [])
            
            # Calculate relevance score
            relevance = sum(profile.interests.get(cat, 0) for cat in item_categories)
            
            # Boost by item popularity
            relevance += item.get('popularity', 0) * 0.05
            
            if relevance > 0:
                recommendations.append(Recommendation(
                    item_id=item_id,
                    score=relevance,
                    reason=f"Based on your interests",
                    metadata=item['content']
                ))
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:top_k]
    
    def evaluate_recommendations(self, user_id: str,
                                feedback: list[dict]) -> dict:
        """Evaluate recommendation quality based on feedback."""
        if user_id not in self._profiles:
            return {'error': 'User not found'}
        
        # Calculate precision, recall
        recommended_items = set()
        relevant_items = set()
        
        for feedback_item in feedback:
            if feedback_item.get('recommended'):
                recommended_items.add(feedback_item['item_id'])
            if feedback_item.get('relevant', False):
                relevant_items.add(feedback_item['item_id'])
        
        # Precision
        intersection = recommended_items & relevant_items
        precision = len(intersection) / len(recommended_items) if recommended_items else 0
        
        # Recall
        recall = len(intersection) / len(relevant_items) if relevant_items else 0
        
        # F1 score
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'total_feedback': len(feedback)
        }


class DiversityFilter:
    """Ensure recommendation diversity."""
    
    def __init__(self, diversity_threshold: float = 0.3):
        self.diversity_threshold = diversity_threshold
    
    def filter_duplicates(self, recommendations: list[Recommendation]) -> list[Recommendation]:
        """Filter duplicate recommendations."""
        seen = set()
        unique = []
        
        for rec in recommendations:
            if rec.item_id not in seen:
                seen.add(rec.item_id)
                unique.append(rec)
        
        return unique
    
    def ensure_diversity(self, recommendations: list[Recommendation],
                        max_per_category: int = 3) -> list[Recommendation]:
        """Ensure diversity across categories."""
        category_counts = defaultdict(int)
        diversified = []
        
        for rec in recommendations:
            categories = rec.metadata.get('categories', [])
            
            # Check if adding this would exceed category limit
            if any(category_counts[cat] >= max_per_category for cat in categories):
                continue
            
            diversified.append(rec)
            for cat in categories:
                category_counts[cat] += 1
        
        return diversified
    
    def boost_novelty(self, recommendations: list[Recommendation],
                     user_history: list[str], novelty_weight: float = 0.3) -> list[Recommendation]:
        """Boost novel recommendations."""
        user_history_set = set(user_history)
        
        for rec in recommendations:
            if rec.item_id not in user_history_set:
                # Boost novel items
                rec.score *= (1 + novelty_weight)
            else:
                # Slightly penalize familiar items
                rec.score *= (1 - novelty_weight * 0.5)
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations


class SerendipityEngine:
    """Add serendipitous recommendations."""
    
    def __init__(self, serendipity_rate: float = 0.1):
        self.serendipity_rate = serendipity_rate
    
    def add_serendipity(self, recommendations: list[Recommendation],
                       all_items: dict[str, dict],
                       user_profile: UserProfile) -> list[Recommendation]:
        """Add serendipitous recommendations."""
        num_serendipitous = max(1, int(len(recommendations) * self.serendipity_rate))
        
        # Find items that are relevant but not obvious
        candidate_items = []
        for item_id, item in all_items.items():
            if item_id not in [r.item_id for r in recommendations]:
                # Check if somewhat relevant but not too obvious
                categories = item.get('categories', [])
                relevance = sum(user_profile.interests.get(cat, 0) for cat in categories)
                
                if 0.2 < relevance < 0.8:  # Somewhat relevant but not obvious
                    candidate_items.append((item_id, item, relevance))
        
        # Select random serendipitous items
        random.seed(42)  # For reproducibility
        serendipitous = random.sample(candidate_items, min(num_serendipitous, len(candidate_items)))
        
        # Add to recommendations
        for item_id, item, relevance in serendipitous:
            recommendations.append(Recommendation(
                item_id=item_id,
                score=relevance * 0.7,  # Slightly lower score
                reason="You might like this surprise",
                metadata=item['content']
            ))
        
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations