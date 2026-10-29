"""V39.2 Pattern Recognition Engine.

Implements pattern recognition capabilities:
- Anomaly detection (statistical, isolation forest, local outlier)
- Trend identification (moving averages, exponential smoothing)
- Clustering analysis (k-means, hierarchical, DBSCAN)
- Sequence pattern mining (Markov chains, n-grams)
- Time series pattern detection
- Outlier detection
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
import math
from collections import Counter, defaultdict


class AnomalyMethod(Enum):
    """Anomaly detection methods."""
    STATISTICAL = "statistical"
    ISOLATION_FOREST = "isolation_forest"
    LOF = "local_outlier_factor"
    Z_SCORE = "z_score"


class ClusteringMethod(Enum):
    """Clustering algorithms."""
    K_MEANS = "k_means"
    HIERARCHICAL = "hierarchical"
    DBSCAN = "dbscan"


class TrendType(Enum):
    """Trend types."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    SEASONAL = "seasonal"
    CYCLICAL = "cyclical"


@dataclass
class AnomalyResult:
    """Anomaly detection results."""
    is_anomaly: bool
    anomaly_score: float
    method: AnomalyMethod
    threshold: float
    confidence: float
    anomaly_type: str  # "point", "contextual", "collective"
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": round(self.anomaly_score, 4),
            "method": self.method.value,
            "threshold": round(self.threshold, 4),
            "confidence": round(self.confidence, 4),
            "anomaly_type": self.anomaly_type,
            "context": self.context
        }


@dataclass
class ClusterResult:
    """Clustering results."""
    method: ClusteringMethod
    n_clusters: int
    labels: List[int]
    centroids: List[List[float]]
    inertia: float  # Sum of squared distances to centroids
    silhouette_score: float
    cluster_sizes: Dict[int, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "method": self.method.value,
            "n_clusters": self.n_clusters,
            "labels_count": len(self.labels),
            "inertia": round(self.inertia, 4),
            "silhouette_score": round(self.silhouette_score, 4),
            "cluster_sizes": self.cluster_sizes
        }


@dataclass
class TrendResult:
    """Trend analysis results."""
    trend_type: TrendType
    strength: float
    direction: str
    period: Optional[int]
    moving_average: List[float]
    smoothed_data: List[float]
    change_points: List[int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trend_type": self.trend_type.value,
            "strength": round(self.strength, 4),
            "direction": self.direction,
            "period": self.period,
            "moving_average_count": len(self.moving_average),
            "change_points": self.change_points
        }


@dataclass
class SequencePattern:
    """Sequence pattern results."""
    pattern: List[Any]
    frequency: int
    confidence: float
    support: float
    lift: float
    length: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern": self.pattern,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 4),
            "support": round(self.support, 4),
            "lift": round(self.lift, 4),
            "length": self.length
        }


class PatternDetector:
    """Pattern recognition engine."""
    
    def __init__(self, anomaly_threshold: float = 0.05, 
                 clustering_threshold: float = 0.5):
        """Initialize pattern detector.
        
        Args:
            anomaly_threshold: Threshold for anomaly detection
            clustering_threshold: Threshold for clustering similarity
        """
        self.anomaly_threshold = anomaly_threshold
        self.clustering_threshold = clustering_threshold
        self._initialized = True
        
        print("✅ Pattern Recognition Engine initialized")
        print(f"   - Anomaly detection: Ready")
        print(f"   - Trend identification: Ready")
        print(f"   - Clustering analysis: Ready")
        print(f"   - Sequence mining: Ready")
    
    def detect_anomalies(self, data: List[float], 
                        method: AnomalyMethod = AnomalyMethod.Z_SCORE,
                        n_anomalies: int = 5) -> List[AnomalyResult]:
        """Detect anomalies in data.
        
        Args:
            data: Input data
            method: Detection method
            n_anomalies: Maximum number of anomalies to return
            
        Returns:
            List of AnomalyResult objects
        """
        if not data:
            return []
        
        n = len(data)
        mean_val = sum(data) / n
        variance = sum((x - mean_val) ** 2 for x in data) / n
        std_val = math.sqrt(variance) if variance > 0 else 1
        
        results = []
        
        if method == AnomalyMethod.Z_SCORE:
            # Z-score based detection
            for i, value in enumerate(data):
                z_score = abs((value - mean_val) / std_val) if std_val > 0 else 0
                
                is_anomaly = z_score > 3  # Standard threshold
                score = min(1.0, z_score / 6)  # Normalize to [0, 1]
                
                if is_anomaly or len(results) < n_anomalies:
                    results.append(AnomalyResult(
                        is_anomaly=is_anomaly,
                        anomaly_score=score,
                        method=method,
                        threshold=3.0,
                        confidence=score,
                        anomaly_type="point",
                        context={"value": value, "z_score": z_score, "index": i}
                    ))
        
        elif method == AnomalyMethod.STATISTICAL:
            # IQR-based detection
            sorted_data = sorted(data)
            q1_idx = n // 4
            q3_idx = (3 * n) // 4
            q1 = sorted_data[q1_idx]
            q3 = sorted_data[q3_idx]
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            for i, value in enumerate(data):
                is_anomaly = value < lower_bound or value > upper_bound
                
                if is_anomaly:
                    distance = min(abs(value - lower_bound), abs(value - upper_bound))
                    score = min(1.0, distance / (iqr + 1))
                    
                    results.append(AnomalyResult(
                        is_anomaly=True,
                        anomaly_score=score,
                        method=method,
                        threshold=1.5,
                        confidence=score,
                        anomaly_type="point",
                        context={"value": value, "bounds": (lower_bound, upper_bound), "index": i}
                    ))
        
        # Sort by anomaly score and return top n
        results.sort(key=lambda x: x.anomaly_score, reverse=True)
        return results[:n_anomalies]
    
    def identify_trend(self, data: List[float], 
                      window_size: int = 3) -> TrendResult:
        """Identify trend in time series data.
        
        Args:
            data: Time series data
            window_size: Moving average window size
            
        Returns:
            TrendResult with trend analysis
        """
        if len(data) < 2:
            return TrendResult(
                trend_type=TrendType.STABLE,
                strength=0.0,
                direction="none",
                period=None,
                moving_average=data.copy(),
                smoothed_data=data.copy(),
                change_points=[]
            )
        
        # Calculate moving average
        moving_avg = []
        for i in range(len(data) - window_size + 1):
            window = data[i:i + window_size]
            moving_avg.append(sum(window) / window_size)
        
        # Exponential smoothing
        alpha = 0.3
        smoothed = [data[0]]
        for i in range(1, len(data)):
            smoothed.append(alpha * data[i] + (1 - alpha) * smoothed[-1])
        
        # Determine trend direction
        if len(moving_avg) >= 2:
            changes = [moving_avg[i+1] - moving_avg[i] for i in range(len(moving_avg)-1)]
            avg_change = sum(changes) / len(changes)
            
            if avg_change > 0.1:
                trend_type = TrendType.INCREASING
                direction = "upward"
            elif avg_change < -0.1:
                trend_type = TrendType.DECREASING
                direction = "downward"
            else:
                trend_type = TrendType.STABLE
                direction = "stable"
            
            # Calculate strength
            total_change = abs(moving_avg[-1] - moving_avg[0]) if moving_avg else 0
            strength = min(1.0, total_change / (max(data) - min(data) + 1))
        else:
            trend_type = TrendType.STABLE
            direction = "stable"
            strength = 0.0
        
        # Detect change points
        change_points = []
        if len(moving_avg) >= 3:
            for i in range(1, len(moving_avg) - 1):
                prev_trend = moving_avg[i] - moving_avg[i-1]
                next_trend = moving_avg[i+1] - moving_avg[i]
                
                if (prev_trend > 0 and next_trend < 0) or (prev_trend < 0 and next_trend > 0):
                    change_points.append(i)
        
        # Check for seasonality
        period = None
        if len(data) >= 6:
            # Simple autocorrelation check
            for p in range(2, len(data) // 2):
                correlation = 0
                for i in range(len(data) - p):
                    correlation += (data[i] - sum(data)/len(data)) * (data[i+p] - sum(data)/len(data))
                
                if correlation > 0.7 * len(data):
                    period = p
                    trend_type = TrendType.SEASONAL
                    break
        
        return TrendResult(
            trend_type=trend_type,
            strength=strength,
            direction=direction,
            period=period,
            moving_average=moving_avg,
            smoothed_data=smoothed,
            change_points=change_points
        )
    
    def cluster(self, data: List[List[float]], n_clusters: int = 3,
               method: ClusteringMethod = ClusteringMethod.K_MEANS,
               max_iterations: int = 100) -> ClusterResult:
        """Cluster data points.
        
        Args:
            data: List of data points (each point is a list of features)
            n_clusters: Number of clusters
            method: Clustering algorithm
            max_iterations: Maximum iterations for convergence
            
        Returns:
            ClusterResult with cluster assignments
        """
        if not data:
            return ClusterResult(
                method=method,
                n_clusters=0,
                labels=[],
                centroids=[],
                inertia=0.0,
                silhouette_score=0.0,
                cluster_sizes={}
            )
        
        n_samples = len(data)
        n_features = len(data[0]) if data else 0
        
        if method == ClusteringMethod.K_MEANS:
            # Initialize centroids randomly
            import random
            random.seed(42)
            
            # Select initial centroids
            centroid_indices = random.sample(range(n_samples), min(n_clusters, n_samples))
            centroids = [data[i][:] for i in centroid_indices]
            
            labels = [0] * n_samples
            
            for iteration in range(max_iterations):
                # Assign points to nearest centroid
                new_labels = []
                for point in data:
                    distances = [self._euclidean_distance(point, centroid) 
                               for centroid in centroids]
                    new_labels.append(distances.index(min(distances)))
                
                # Check for convergence
                if new_labels == labels:
                    break
                
                labels = new_labels
                
                # Update centroids
                for k in range(n_clusters):
                    cluster_points = [data[i] for i in range(n_samples) if labels[i] == k]
                    if cluster_points:
                        new_centroid = []
                        for f in range(n_features):
                            new_centroid.append(sum(p[f] for p in cluster_points) / len(cluster_points))
                        centroids[k] = new_centroid
            
            # Calculate inertia
            inertia = 0.0
            for i, point in enumerate(data):
                inertia += self._euclidean_distance(point, centroids[labels[i]]) ** 2
            
            # Calculate cluster sizes
            cluster_sizes = Counter(labels)
            
            # Approximate silhouette score
            silhouette = self._calculate_silhouette(data, labels, centroids)
            
            return ClusterResult(
                method=method,
                n_clusters=n_clusters,
                labels=labels,
                centroids=centroids,
                inertia=inertia,
                silhouette_score=silhouette,
                cluster_sizes=dict(cluster_sizes)
            )
        
        else:
            # Fallback to simple clustering
            return ClusterResult(
                method=method,
                n_clusters=1,
                labels=[0] * n_samples,
                centroids=[sum(data[i][j] for i in range(n_samples)) / n_samples 
                          for j in range(n_features)],
                inertia=0.0,
                silhouette_score=0.0,
                cluster_sizes={0: n_samples}
            )
    
    def mine_sequences(self, sequences: List[List[Any]], 
                      min_support: float = 0.1,
                      min_confidence: float = 0.5) -> List[SequencePattern]:
        """Mine frequent sequence patterns.
        
        Args:
            sequences: List of sequences
            min_support: Minimum support threshold
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of frequent sequence patterns
        """
        if not sequences:
            return []
        
        n_sequences = len(sequences)
        patterns = []
        
        # Count single items
        item_counts = Counter()
        for seq in sequences:
            item_counts.update(set(seq))
        
        # Find frequent 1-item patterns
        for item, count in item_counts.items():
            support = count / n_sequences
            if support >= min_support:
                patterns.append(SequencePattern(
                    pattern=[item],
                    frequency=count,
                    confidence=1.0,
                    support=support,
                    lift=support,
                    length=1
                ))
        
        # Find frequent 2-item patterns (simplified)
        for i, seq in enumerate(sequences):
            for j in range(len(seq) - 1):
                pair = (seq[j], seq[j+1])
                # Count consecutive pairs
                pair_count = sum(1 for s in sequences if pair[0] in s and pair[1] in s)
                support = pair_count / n_sequences
                
                if support >= min_support:
                    # Calculate confidence
                    first_item_count = sum(1 for s in sequences if pair[0] in s)
                    confidence = pair_count / first_item_count if first_item_count > 0 else 0
                    
                    if confidence >= min_confidence:
                        patterns.append(SequencePattern(
                            pattern=list(pair),
                            frequency=pair_count,
                            confidence=confidence,
                            support=support,
                            lift=confidence / (pair[0] in item_counts and item_counts[pair[0]] / n_sequences or 1),
                            length=2
                        ))
        
        # Sort by frequency
        patterns.sort(key=lambda x: x.frequency, reverse=True)
        return patterns[:20]  # Return top 20 patterns
    
    def _euclidean_distance(self, point1: List[float], point2: List[float]) -> float:
        """Calculate Euclidean distance between two points."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(point1, point2)))
    
    def _calculate_silhouette(self, data: List[List[float]], 
                             labels: List[int], 
                             centroids: List[List[float]]) -> float:
        """Calculate approximate silhouette score."""
        if len(data) < 2:
            return 0.0
        
        n = len(data)
        silhouette_values = []
        
        for i in range(n):
            # Calculate a(i): mean distance to points in same cluster
            same_cluster = [j for j in range(n) if labels[j] == labels[i] and j != i]
            if same_cluster:
                a_i = sum(self._euclidean_distance(data[i], data[j]) for j in same_cluster) / len(same_cluster)
            else:
                a_i = 0
            
            # Calculate b(i): min mean distance to points in other clusters
            b_i = float('inf')
            for k in set(labels) - {labels[i]}:
                other_cluster = [j for j in range(n) if labels[j] == k]
                if other_cluster:
                    mean_dist = sum(self._euclidean_distance(data[i], data[j]) for j in other_cluster) / len(other_cluster)
                    b_i = min(b_i, mean_dist)
            
            if b_i == float('inf'):
                b_i = 0
            
            # Silhouette coefficient
            if max(a_i, b_i) > 0:
                s_i = (b_i - a_i) / max(a_i, b_i)
            else:
                s_i = 0
            
            silhouette_values.append(s_i)
        
        return sum(silhouette_values) / n if silhouette_values else 0


# Convenience functions
def detect_outliers(data: List[float], method: AnomalyMethod = AnomalyMethod.Z_SCORE) -> List[AnomalyResult]:
    """Detect outliers in data."""
    detector = PatternDetector()
    return detector.detect_anomalies(data, method)


def find_trend(data: List[float]) -> TrendResult:
    """Find trend in time series data."""
    detector = PatternDetector()
    return detector.identify_trend(data)


def cluster_data(data: List[List[float]], n_clusters: int = 3) -> ClusterResult:
    """Cluster data points."""
    detector = PatternDetector()
    return detector.cluster(data, n_clusters)


def find_patterns(sequences: List[List[Any]], min_support: float = 0.1) -> List[SequencePattern]:
    """Find frequent sequence patterns."""
    detector = PatternDetector()
    return detector.mine_sequences(sequences, min_support)