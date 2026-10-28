"""
Recommendation System Module (V25.5)

Provides:
- content-based filtering: term-frequency vectors over tags/text, cosine
  similarity
- collaborative filtering: simple user-item matrix, user-based kNN with
  cosine similarity on mean-centered ratings
- hybrid blending with configurable weights
- similar-items helper (item-to-item content similarity)

Standard library only (no numpy, no scikit-learn).

Version: V25.5
Author: QUAN AI BRAIN Team
"""

import logging
import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens."""
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Cosine similarity between two sparse weight dicts; 0.0 when empty."""
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    numerator = sum(vec_a[t] * vec_b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return numerator / (norm_a * norm_b)


class ItemProfile:
    """TF vector + tags for one item."""

    __slots__ = ('item_id', 'tags', 'tf')

    def __init__(self, item_id: str, tags: Sequence[str], tf: Dict[str, float]):
        self.item_id = item_id
        self.tags = list(tags)
        self.tf = tf


class ContentBasedFilter:
    """
    Content-based recommender over term-frequency vectors.

    Items are dicts: ``{"id": str, "tags": [str], "text": str}``. The
    document fed to the TF vector is tags (each tag contributes
    ``tag_weight`` repeats) plus the item text.
    """

    def __init__(self, tag_weight: int = 3):
        self.tag_weight = int(tag_weight)
        self.items: Dict[str, Dict[str, Any]] = {}
        self._profiles: Dict[str, ItemProfile] = {}

    def add_item(self, item: Dict[str, Any]) -> None:
        item_id = str(item.get('id'))
        if not item_id or item_id in self.items:
            return
        tags = [str(t).lower() for t in (item.get('tags') or [])]
        text = str(item.get('text') or '')
        doc: List[str] = list(tags) * self.tag_weight + _tokenize(text)
        tf = Counter(doc)
        self.items[item_id] = {'tags': tags, 'text': text}
        self._profiles[item_id] = ItemProfile(item_id, tags, dict(tf))

    def add_items(self, items: Iterable[Dict[str, Any]]) -> None:
        for item in items:
            self.add_item(item)

    def profile(self, item_id: str) -> Optional[ItemProfile]:
        return self._profiles.get(item_id)

    def similarity(self, id_a: str, id_b: str) -> float:
        pa, pb = self._profiles.get(str(id_a)), self._profiles.get(str(id_b))
        if pa is None or pb is None:
            return 0.0
        return cosine_similarity(pa.tf, pb.tf)

    def similar_items(
        self, item_id: str, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """Most similar items to ``item_id`` (desc, excludes the item itself)."""
        item_id = str(item_id)
        scored = [
            (other, self.similarity(item_id, other))
            for other in self._profiles
            if other != item_id
        ]
        scored = [(i, s) for i, s in scored if s > 0.0]
        scored.sort(key=lambda t: (-t[1], t[0]))
        return scored[:max(0, int(top_k))]

    def recommend(
        self, liked_item_ids: Sequence[str], top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Score every not-yet-liked item by its mean cosine similarity to the
        liked items. Returns (item_id, score) desc; empty when nothing liked.
        """
        liked = [str(i) for i in liked_item_ids if str(i) in self._profiles]
        if not liked:
            return []
        candidates = [i for i in self._profiles if i not in set(liked)]
        scored = []
        for cand in candidates:
            sims = [self.similarity(liked_id, cand) for liked_id in liked]
            score = sum(sims) / len(sims)
            if score > 0.0:
                scored.append((cand, score))
        scored.sort(key=lambda t: (-t[1], t[0]))
        return scored[:max(0, int(top_k))]


class CollaborativeFilter:
    """
    User-based collaborative filtering with a plain dict user-item matrix.

    ``ratings`` maps user_id -> {item_id: rating}. Similarity is cosine on
    mean-centered rating vectors (Pearson-like); predictions are rating
    predictions from the k nearest neighbors.
    """

    def __init__(
        self,
        ratings: Optional[Dict[str, Dict[str, float]]] = None,
        k: int = 3,
    ):
        self.k = max(1, int(k))
        self.ratings: Dict[str, Dict[str, float]] = {
            str(u): {str(i): float(r) for i, r in items.items()}
            for u, items in (ratings or {}).items()
        }
        self._centered: Dict[str, Dict[str, float]] = {}
        self._similarity: Dict[Tuple[str, str], float] = {}

    # ------------------------------------------------------------------
    def add_rating(self, user_id: str, item_id: str, rating: float) -> None:
        u, i = str(user_id), str(item_id)
        self.ratings.setdefault(u, {})[i] = float(rating)
        self._centered.pop(u, None)
        self._similarity.clear()

    def _centered_vector(self, user_id: str) -> Dict[str, float]:
        if user_id not in self._centered:
            vec = self.ratings.get(user_id, {})
            mean = sum(vec.values()) / len(vec) if vec else 0.0
            self._centered[user_id] = {
                i: r - mean for i, r in vec.items()
            }
        return self._centered[user_id]

    def user_similarity(self, user_a: str, user_b: str) -> float:
        """Cosine similarity between mean-centered rating vectors."""
        a, b = str(user_a), str(user_b)
        if a == b:
            return 0.0
        key = (a, b) if a <= b else (b, a)
        if key not in self._similarity:
            sim = cosine_similarity(
                self._centered_vector(a), self._centered_vector(b)
            )
            self._similarity[key] = sim
        return self._similarity[key]

    def similar_users(self, user_id: str, k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Top-k similar users (sim > 0, desc, tie-break by user id)."""
        user_id = str(user_id)
        k = self.k if k is None else int(k)
        sims = [
            (other, self.user_similarity(user_id, other))
            for other in self.ratings
            if other != user_id
        ]
        sims = [(u, s) for u, s in sims if s > 0.0]
        sims.sort(key=lambda t: (-t[1], t[0]))
        return sims[:max(0, k)]

    def predict(self, user_id: str, item_id: str) -> Optional[float]:
        """
        Predict the user's rating for an item from up to k neighbors who
        rated it. Returns None when no usable neighbor exists.
        """
        user_id, item_id = str(user_id), str(item_id)
        target = self.ratings.get(user_id, {}).get(item_id)
        if target is not None:
            return target  # already rated -> known value
        user_mean = (
            sum(self.ratings.get(user_id, {}).values())
            / len(self.ratings.get(user_id, {}))
            if self.ratings.get(user_id)
            else 0.0
        )
        num = 0.0
        den = 0.0
        for other, sim in self.similar_users(user_id):
            rating = self.ratings.get(other, {}).get(item_id)
            if rating is None:
                continue
            other_mean = (
                sum(self.ratings.get(other, {}).values())
                / len(self.ratings.get(other, {}))
            )
            num += sim * (rating - other_mean)
            den += abs(sim)
        if den == 0.0:
            return None
        return user_mean + num / den

    def recommend(
        self, user_id: str, top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Top-k unseen items for the user, ranked by predicted rating desc,
        ties broken alphabetically by item id. Unpredictable items are
        excluded.
        """
        user_id = str(user_id)
        seen = set(self.ratings.get(user_id, {}))
        candidates = set()
        for other, _sim in self.similar_users(user_id, k=None):
            candidates.update(self.ratings.get(other, {}).keys())
        candidates -= seen
        scored = []
        for item in candidates:
            pred = self.predict(user_id, item)
            if pred is not None:
                scored.append((item, pred))
        scored.sort(key=lambda t: (-t[1], t[0]))
        return scored[:max(0, int(top_k))]


class HybridRecommender:
    """
    Weighted blend of content-based and collaborative scores.

    ``content_weight + collab_weight`` need not sum to 1; the blended score
    is the weighted sum of each component's min-max-normalized scores.
    """

    def __init__(
        self,
        content: ContentBasedFilter,
        collab: CollaborativeFilter,
        content_weight: float = 0.5,
        collab_weight: float = 0.5,
    ):
        self.content = content
        self.collab = collab
        self.content_weight = float(content_weight)
        self.collab_weight = float(collab_weight)

    @staticmethod
    def _normalize(scores: List[Tuple[str, float]]) -> Dict[str, float]:
        if not scores:
            return {}
        values = [s for _i, s in scores]
        lo, hi = min(values), max(values)
        if hi == lo:
            return {i: 0.5 for i, _s in scores}
        return {i: (s - lo) / (hi - lo) for i, s in scores}

    def recommend(
        self, user_id: str, liked_item_ids: Optional[Sequence[str]] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Blend content + collaborative rankings.

        ``liked_item_ids`` defaults to the user's top-rated items
        (rating >= 4). The result includes the blended ``score``, the two
        component scores and the ``components`` that contributed.
        """
        user_id = str(user_id)
        if liked_item_ids is None:
            user_ratings = self.collab.ratings.get(user_id, {})
            liked = [
                i for i, r in sorted(user_ratings.items(),
                                     key=lambda kv: (-kv[1], kv[0]))
                if r >= 4.0
            ]
        else:
            liked = [str(i) for i in (liked_item_ids or [])]

        content_scores = self.content.recommend(liked, top_k=10**6)
        collab_scores = self.collab.recommend(user_id, top_k=10**6)
        content_norm = self._normalize(content_scores)
        collab_norm = self._normalize(collab_scores)

        union = set(content_norm) | set(collab_norm)
        results: List[Dict[str, Any]] = []
        for item in union:
            cs = content_norm.get(item, 0.0)
            xs = collab_norm.get(item, 0.0)
            score = self.content_weight * cs + self.collab_weight * xs
            components = []
            if item in content_norm:
                components.append('content')
            if item in collab_norm:
                components.append('collaborative')
            results.append({
                'item_id': item,
                'score': round(score, 6),
                'content_score': round(cs, 6),
                'collab_score': round(xs, 6),
                'components': components,
            })
        results.sort(key=lambda r: (-r['score'], r['item_id']))
        return results[:max(0, int(top_k))]


class RecommendationEngine:
    """Facade bundling content + collaborative + hybrid recommenders."""

    def __init__(
        self,
        items: Optional[Sequence[Dict[str, Any]]] = None,
        ratings: Optional[Dict[str, Dict[str, float]]] = None,
        content_weight: float = 0.5,
        collab_weight: float = 0.5,
        k: int = 3,
    ):
        self.content = ContentBasedFilter()
        self.content.add_items(items or [])
        self.collab = CollaborativeFilter(ratings=ratings, k=k)
        self.hybrid = HybridRecommender(
            self.content, self.collab,
            content_weight=content_weight, collab_weight=collab_weight,
        )

    def get_recommendations(
        self, user_id: str, top_k: int = 5,
        liked_item_ids: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self.hybrid.recommend(
            user_id, liked_item_ids=liked_item_ids, top_k=top_k
        )

    def similar_items(self, item_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        return self.content.similar_items(item_id, top_k=top_k)
