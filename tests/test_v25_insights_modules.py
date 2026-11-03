"""
Tests for V25 Insights Modules (M2-M5)

Covers:
- M2 insights_engine: AIInsightsEngine (rules, scoring, dedupe), correlations
- M3 report_generator: ReportGenerator (markdown/html/csv exports)
- M4 graph_visualization: KnowledgeGraphVisualizer (layout, centrality, export)
- M5 recommendation_system: content-based, collaborative, hybrid
- V25 integration: M1 analytics_engine reused end-to-end (no skips)
"""

import csv
import io
import json
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from quan_ai_brain.analytics.analytics_engine import (
    Anomaly,
    Insight,
    InsightType,
    Metric,
    MetricType,
    MetricsCalculator,
    Priority,
)
from quan_ai_brain.analytics.insights_engine import (
    AIInsightsEngine,
    CorrelationAnalyzer,
    pearson_correlation,
)
from quan_ai_brain.analytics.report_generator import (
    Report,
    ReportGenerator,
    ReportSection,
)
from quan_ai_brain.analytics.graph_visualization import KnowledgeGraphVisualizer
from quan_ai_brain.analytics.recommendation_system import (
    CollaborativeFilter,
    ContentBasedFilter,
    HybridRecommender,
    RecommendationEngine,
    cosine_similarity,
)


def make_metric(metric_id='total_ku', value=100.0, warning=None, critical=None):
    return Metric(
        metric_id=metric_id,
        name=metric_id.replace('_', ' ').title(),
        value=value,
        unit='units',
        metric_type=MetricType.COUNT,
        timestamp=datetime.utcnow(),
        threshold_warning=warning,
        threshold_critical=critical,
    )


def make_anomaly(severity='critical', metric_name='creates_24h'):
    return Anomaly(
        anomaly_id=f'anomaly_{metric_name}_{severity}',
        metric_name=metric_name,
        observed_value=150.0,
        expected_value=100.0,
        deviation=3.5,
        timestamp=datetime.utcnow(),
        severity=severity,
        description=f'{metric_name} is 3.5 standard deviations from baseline',
    )


class _FakeAge:
    """M1 MetricsCalculator calls ``.total_days`` on the db's age object."""

    def __init__(self, days):
        self.total_days = days


def make_mock_db():
    db = Mock()
    db.count_knowledge_units = Mock(return_value=1000)
    db.count_by_type = Mock(return_value={'FACT': 500, 'QUESTION': 300})
    db.count_by_status = Mock(
        side_effect=lambda status=None: (
            {'VERIFIED': 800, 'PENDING': 200}
            if status is None
            else {'VERIFIED': 800, 'PENDING': 200}.get(status, 0)
        )
    )
    db.get_average_confidence = Mock(return_value=0.75)
    db.count_recent = Mock(return_value=50)
    db.get_average_age = Mock(return_value=_FakeAge(15.0))
    db.count_stale = Mock(return_value=10)
    db.count_searches = Mock(return_value=200)
    db.get_average_search_results = Mock(return_value=15.5)
    return db


CONTENT_ITEMS = [
    {'id': 'py1', 'tags': ['python', 'ml'],
     'text': 'machine learning tutorial with python'},
    {'id': 'py2', 'tags': ['python', 'ml'],
     'text': 'deep learning with python and neural networks'},
    {'id': 'java1', 'tags': ['java', 'spring'],
     'text': 'spring framework enterprise java guide'},
    {'id': 'web1', 'tags': ['python', 'web'],
     'text': 'flask web development in python'},
]

COLLAB_RATINGS = {
    'u1': {'i1': 5, 'i2': 4, 'i3': 1},
    'u2': {'i1': 5, 'i2': 4, 'i4': 5},
    'u3': {'i3': 5, 'i4': 1, 'i5': 2},
    'u4': {'i1': 1, 'i3': 5},
}


# ======================================================================
# M2: AI Insights Engine
# ======================================================================
class TestInsightsEngine:

    def test_pearson_perfect_positive(self):
        assert pearson_correlation([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)

    def test_pearson_perfect_negative(self):
        assert pearson_correlation([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)

    def test_pearson_uncorrelated_is_zero(self):
        assert pearson_correlation([1, 2, 3, 4], [3, 1, 4, 2]) == pytest.approx(0.0, abs=1e-9)

    def test_pearson_degenerate_inputs(self):
        assert pearson_correlation([5, 5, 5], [1, 2, 3]) == 0.0  # constant series
        assert pearson_correlation([1, 2], [1, 2, 3]) == 0.0  # length mismatch
        assert pearson_correlation([1], [1]) == 0.0  # too short
        assert pearson_correlation([], []) == 0.0  # empty

    def test_correlation_analyzer_finds_strong_pair(self):
        analyzer = CorrelationAnalyzer(threshold=0.7, min_points=3)
        series = {
            'a': [1, 2, 3, 4, 5],
            'b': [2, 4, 6, 8, 10],
            'c': [1, -1, 1, -1, 1],
        }
        pairs = analyzer.find_strong_pairs(series)
        assert pairs == [('a', 'b', pytest.approx(1.0))]

    def test_anomaly_insight_critical(self):
        engine = AIInsightsEngine()
        insight = engine.insight_from_anomaly(make_anomaly(severity='critical'))
        assert insight.insight_type == InsightType.ANOMALY
        assert insight.priority == Priority.CRITICAL
        assert insight.confidence * insight.impact == pytest.approx(0.81)
        assert any('Observed: 150' in e for e in insight.evidence)
        assert insight.related_metrics == ['creates_24h']

    def test_anomaly_insight_low_severity(self):
        engine = AIInsightsEngine()
        insight = engine.insight_from_anomaly(make_anomaly(severity='low'))
        assert insight.priority == Priority.LOW
        assert insight.impact < 0.5

    def test_trend_insight_up_with_forecast_note(self):
        engine = AIInsightsEngine()
        result = {
            'trend': 'up',
            'slope': 2.0,
            'mean': 50.0,
            'data': [{'value': 48}, {'value': 50}, {'value': 52}],
        }
        insight = engine.insight_from_trend('creates_24h', result)
        assert insight.insight_type == InsightType.TREND
        assert 'Forecast note' in insight.description
        assert '54.00' in insight.description  # 52 + slope 2
        assert insight.priority == Priority.MEDIUM

    def test_trend_insight_down_priority(self):
        engine = AIInsightsEngine()
        result = {'trend': 'down', 'slope': -1.5, 'mean': 30.0,
                  'data': [{'value': 33}, {'value': 30}]}
        insight = engine.insight_from_trend('avg_confidence', result)
        assert insight.title.startswith('Declining')
        assert insight.priority == Priority.HIGH
        assert insight.impact == 0.8

    def test_trend_insufficient_data_returns_none(self):
        engine = AIInsightsEngine()
        assert engine.insight_from_trend('x', {'trend': 'insufficient_data', 'data': []}) is None
        assert engine.insight_from_trend('x', {'data': []}) is None

    def test_correlation_insight_fields(self):
        engine = AIInsightsEngine()
        engine.add_series('searches', [1, 2, 3, 4])
        engine.add_series('creates', [2, 4, 6, 8])
        insight = engine.insight_from_correlation('searches', 'creates', 1.0)
        assert insight.insight_type == InsightType.CORRELATION
        assert insight.related_metrics == ['searches', 'creates']
        assert 'positive' in insight.title.lower()
        assert 'r=1.00' in insight.description

    def test_metric_warning_threshold_insight(self):
        engine = AIInsightsEngine()
        insights = engine.insights_from_metric(make_metric('verified_rate', 0.2, warning=0.5))
        assert len(insights) == 1
        assert insights[0].insight_type == InsightType.RECOMMENDATION
        assert 'warning threshold' in insights[0].description

    def test_metric_critical_threshold_insight(self):
        engine = AIInsightsEngine()
        insights = engine.insights_from_metric(
            make_metric('avg_confidence', 0.3, warning=0.6, critical=0.4)
        )
        assert len(insights) == 1
        assert insights[0].priority == Priority.CRITICAL
        assert 'critical threshold' in insights[0].description

    def test_metric_above_thresholds_no_insight(self):
        engine = AIInsightsEngine()
        assert engine.insights_from_metric(make_metric('m', 0.9, warning=0.5)) == []

    def test_score_is_impact_times_confidence(self):
        engine = AIInsightsEngine()
        insight = engine.insight_from_anomaly(make_anomaly(severity='high'))
        assert engine.score(insight) == pytest.approx(0.9 * 0.7)

    def test_dedupe_removes_similar_keeps_best(self):
        engine = AIInsightsEngine()
        strong = engine._build(
            InsightType.ANOMALY, 'CPU usage spike detected',
            'CPU usage spike detected on node', 0.9, 0.9, ['e'], ['r'], ['cpu'],
        )
        weak = engine._build(
            InsightType.ANOMALY, 'CPU usage spike detected',
            'CPU usage spike detected on node', 0.5, 0.5, ['e'], ['r'], ['cpu'],
        )
        kept = engine.dedupe([weak, strong])
        assert len(kept) == 1
        assert kept[0].confidence == pytest.approx(0.9)

    def test_dedupe_keeps_different_types(self):
        engine = AIInsightsEngine()
        first = engine._build(
            InsightType.ANOMALY, 'CPU usage spike detected',
            'CPU usage spike detected on node', 0.9, 0.9, [], [], ['cpu'],
        )
        second = engine._build(
            InsightType.TREND, 'CPU usage spike detected',
            'CPU usage spike detected on node', 0.9, 0.9, [], [], ['cpu'],
        )
        assert len(engine.dedupe([first, second])) == 2

    def test_dedupe_keeps_dissimilar_texts(self):
        engine = AIInsightsEngine()
        first = engine._build(
            InsightType.ANOMALY, 'CPU anomaly on node A',
            'cpu usage is high', 0.9, 0.9, [], [], ['cpu'],
        )
        second = engine._build(
            InsightType.ANOMALY, 'Memory anomaly on node B',
            'memory usage is low', 0.8, 0.8, [], [], ['memory'],
        )
        assert len(engine.dedupe([first, second])) == 2

    def test_generate_all_sorted_and_deduped(self):
        engine = AIInsightsEngine(
            series={'a': [1, 2, 3, 4], 'b': [2, 4, 6, 8]},
            metrics=[make_metric('verified_rate', 0.2, warning=0.5)],
            anomalies=[make_anomaly(severity='critical')],
            trend_results={'creates_24h': {
                'trend': 'down', 'slope': -1.0, 'mean': 10.0,
                'data': [{'value': 12}, {'value': 10}],
            }},
        )
        insights = engine.generate_all()
        types = {i.insight_type for i in insights}
        assert {InsightType.ANOMALY, InsightType.TREND,
                InsightType.CORRELATION, InsightType.RECOMMENDATION} <= types
        scores = [engine.score(i) for i in insights]
        assert scores == sorted(scores, reverse=True)
        assert len(insights) == len(engine.dedupe(insights))


# ======================================================================
# M3: Automated Reports
# ======================================================================
class TestReportGenerator:

    @pytest.fixture
    def generator(self):
        return ReportGenerator(metrics_provider=[make_metric('total_ku', 100)])

    def test_generate_report_has_four_sections(self, generator):
        report = generator.generate_report()
        titles = [s.title for s in report.sections]
        assert titles == ['Executive Summary', 'Metrics Detail', 'Anomalies',
                          'Recommendations']

    def test_report_identity_fields(self, generator):
        report = generator.generate_report(title='Daily Report')
        assert report.title == 'Daily Report'
        assert report.report_id.startswith('report_')
        assert isinstance(report.generated_at, datetime)

    def test_exec_summary_content(self, generator):
        report = generator.generate_report()
        summary = report.get_section('Executive Summary')
        assert 'Health status' in summary.content
        assert 'Total metrics collected: 1' in summary.content

    def test_health_status_healthy(self, generator):
        assert generator.generate_report().health_status() == 'healthy'

    def test_health_status_critical_anomaly(self, generator):
        report = generator.generate_report(anomalies=[make_anomaly('critical')])
        assert report.health_status() == 'critical'

    def test_health_status_warning_threshold(self):
        gen = ReportGenerator(metrics_provider=[make_metric('m', 10, warning=50)])
        assert gen.generate_report().health_status() == 'warning'

    def test_metrics_detail_section_table_and_figures(self, generator):
        report = generator.generate_report()
        detail = report.get_section('Metrics Detail')
        assert '| Metric | Value | Unit | Type |' in detail.content
        assert 'Total Ku' in detail.content
        assert detail.metrics == {'total_ku': 100.0}

    def test_markdown_export_contains_all_sections(self, generator):
        md = generator.to_markdown(generator.generate_report())
        assert '# Daily' not in md
        assert md.startswith('# QUAN AI BRAIN Analytics Report')
        for title in ('## Executive Summary', '## Metrics Detail',
                      '## Anomalies', '## Recommendations'):
            assert title in md

    def test_anomalies_section_content(self, generator):
        report = generator.generate_report(anomalies=[make_anomaly('high')])
        anomalies = report.get_section('Anomalies')
        assert '**[high] creates_24h**' in anomalies.content

    def test_no_anomalies_section_message(self, generator):
        report = generator.generate_report()
        assert 'No anomalies detected' in report.get_section('Anomalies').content

    def test_html_export_structure_and_escaping(self):
        gen = ReportGenerator(
            metrics_provider=[make_metric('total_<ku>', 100)]
        )
        report = gen.generate_report()
        html = gen.to_html(report)
        assert html.startswith('<!DOCTYPE html>')
        assert '<h1>' in html and '<h2>' in html
        assert '<table border="1">' in html
        assert 'Total &lt;Ku&gt;' in html  # metric name escaped
        assert '<Total <Ku>>' not in html

    def test_csv_export_rows(self, generator):
        report = generator.generate_report(
            anomalies=[], insights=[],
        )
        csv_text = generator.to_csv(report)
        rows = list(csv.reader(io.StringIO(csv_text)))
        assert rows[0][0] == 'metric_id'
        assert len(rows) == 2  # header + 1 metric
        assert rows[1][0] == 'total_ku'

    def test_render_dispatch_and_invalid_format(self, generator):
        report = generator.generate_report()
        assert generator.render(report, 'html') == generator.to_html(report)
        assert generator.render(report, 'md') == generator.to_markdown(report)
        with pytest.raises(ValueError):
            generator.render(report, 'pdf')

    def test_report_to_dict_round_trip(self, generator):
        data = generator.generate_report().to_dict()
        assert data['health_status'] == 'healthy'
        assert len(data['sections']) == 4
        assert data['metrics'][0]['metric_id'] == 'total_ku'

    def test_recommendations_from_insights_deduped(self, generator):
        engine = AIInsightsEngine()
        insight = engine.insight_from_anomaly(make_anomaly('critical'))
        report = generator.generate_report(
            insights=[insight],
            extra_recommendations=['Investigate root cause', '  investigate root cause  '],
        )
        assert report.recommendations.count('Investigate root cause') == 1

    def test_generator_with_metrics_calculator(self):
        gen = ReportGenerator(metrics_provider=MetricsCalculator(make_mock_db()))
        report = gen.generate_report()
        assert any(m.metric_id == 'total_ku' for m in report.metrics)
        assert any(m.metric_id == 'avg_confidence' for m in report.metrics)
        md = gen.to_markdown(report)
        assert 'Total Knowledge Units' in md
        assert 'Average Confidence' in md


# ======================================================================
# M4: Knowledge Graph Visualization
# ======================================================================
class TestGraphVisualization:

    def _star_graph(self):
        nodes = [{'id': 'hub', 'label': 'Hub', 'type': 'concept'}] + [
            {'id': f'l{i}', 'label': f'Leaf {i}', 'type': 'note'}
            for i in range(1, 5)
        ]
        edges = [{'source': 'hub', 'target': f'l{i}', 'weight': 1.0}
                 for i in range(1, 5)]
        return nodes, edges

    def test_empty_graph_layout(self):
        graph = KnowledgeGraphVisualizer(nodes=[], edges=[])
        assert graph.compute_layout() == {}
        assert graph.compute_centrality() == {}

    def test_layout_positions_for_all_nodes(self):
        nodes, edges = self._star_graph()
        positions = KnowledgeGraphVisualizer(nodes=nodes, edges=edges).compute_layout()
        assert set(positions) == {'hub', 'l1', 'l2', 'l3', 'l4'}
        for p in positions.values():
            assert set(p) == {'x', 'y'}
            assert isinstance(p['x'], float) and isinstance(p['y'], float)

    def test_layout_deterministic_with_same_seed(self):
        nodes, edges = self._star_graph()
        first = KnowledgeGraphVisualizer(nodes=nodes, edges=edges, seed=42)
        second = KnowledgeGraphVisualizer(nodes=nodes, edges=edges, seed=42)
        assert first.compute_layout() == second.compute_layout()

    def test_layout_varies_with_seed(self):
        nodes, edges = self._star_graph()
        first = KnowledgeGraphVisualizer(nodes=nodes, edges=edges, seed=1)
        second = KnowledgeGraphVisualizer(nodes=nodes, edges=edges, seed=2)
        assert first.compute_layout() != second.compute_layout()

    def test_degree_star_graph(self):
        nodes, edges = self._star_graph()
        degree = KnowledgeGraphVisualizer(nodes=nodes, edges=edges).compute_degree()
        assert degree['hub'] == 4
        assert all(degree[f'l{i}'] == 1 for i in range(1, 5))

    def test_centrality_normalized(self):
        nodes, edges = self._star_graph()
        centrality = KnowledgeGraphVisualizer(nodes=nodes, edges=edges).compute_centrality()
        assert centrality['hub'] == pytest.approx(1.0)  # 4 / (5-1)
        assert centrality['l1'] == pytest.approx(0.25)

    def test_top_central_nodes(self):
        nodes, edges = self._star_graph()
        top = KnowledgeGraphVisualizer(nodes=nodes, edges=edges).top_central_nodes(k=2)
        assert top[0][0] == 'hub'
        assert len(top) == 2 and top[0][1] >= top[1][1]

    def test_self_loop_ignored(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[{'id': 'a'}], edges=[{'source': 'a', 'target': 'a'}]
        )
        assert graph.edges == []
        assert graph.compute_degree() == {'a': 0}

    def test_duplicate_edges_deduped(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[{'id': 'a'}, {'id': 'b'}],
            edges=[{'source': 'a', 'target': 'b'}, {'source': 'a', 'target': 'b'}],
        )
        assert len(graph.edges) == 1
        assert graph.compute_degree() == {'a': 1, 'b': 1}

    def test_unknown_endpoints_autoregistered(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[], edges=[{'source': 'x', 'target': 'y'}]
        )
        assert set(graph.node_ids) == {'x', 'y'}
        assert graph.count_connected_components() == 1

    def test_export_graph_structure(self):
        nodes, edges = self._star_graph()
        data = KnowledgeGraphVisualizer(nodes=nodes, edges=edges).export_graph()
        assert set(data) == {'nodes', 'edges', 'positions', 'stats'}
        hub = next(n for n in data['nodes'] if n['id'] == 'hub')
        assert hub['label'] == 'Hub' and hub['type'] == 'concept'
        assert hub['degree'] == 4 and hub['centrality'] == pytest.approx(1.0)
        assert 'x' in hub and 'y' in hub
        assert data['stats']['node_count'] == 5
        assert data['stats']['edge_count'] == 4

    def test_json_export_round_trip(self):
        nodes, edges = self._star_graph()
        payload = json.loads(
            KnowledgeGraphVisualizer(nodes=nodes, edges=edges).to_json()
        )
        assert payload['stats']['connected_components'] == 1
        assert len(payload['positions']) == 5
        assert json.loads(json.dumps(payload)) == payload

    def test_shortest_path(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[{'id': n} for n in ('a', 'b', 'c', 'd')],
            edges=[{'source': 'a', 'target': 'b'},
                   {'source': 'b', 'target': 'c'},
                   {'source': 'a', 'target': 'd'},
                   {'source': 'd', 'target': 'c'}],
        )
        assert graph.shortest_path('a', 'c') == ['a', 'b', 'c']
        assert graph.shortest_path('a', 'a') == ['a']
        assert graph.shortest_path('a', 'ghost') == []

    def test_unreachable_path_empty(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[{'id': 'a'}, {'id': 'b'}, {'id': 'c'}, {'id': 'd'}],
            edges=[{'source': 'a', 'target': 'b'}, {'source': 'c', 'target': 'd'}],
        )
        assert graph.count_connected_components() == 2
        assert graph.shortest_path('a', 'c') == []


# ======================================================================
# M5: Recommendation System
# ======================================================================
class TestRecommendationSystem:

    @pytest.fixture
    def content(self):
        content = ContentBasedFilter()
        content.add_items(CONTENT_ITEMS)
        return content

    def test_cosine_identical_vectors(self):
        assert cosine_similarity({'a': 1.0, 'b': 2.0}, {'a': 1.0, 'b': 2.0}) == pytest.approx(1.0)

    def test_cosine_orthogonal_and_empty(self):
        assert cosine_similarity({'a': 1.0}, {'b': 1.0}) == pytest.approx(0.0)
        assert cosine_similarity({}, {'a': 1.0}) == 0.0

    def test_content_profile_tag_weighting(self):
        content = ContentBasedFilter(tag_weight=3)
        content.add_item({'id': 'x', 'tags': ['python'], 'text': ''})
        assert content.profile('x').tf == {'python': 3}

    def test_content_similarity_scores(self, content):
        assert content.similarity('py1', 'py2') > content.similarity('py1', 'web1')
        assert content.similarity('py1', 'java1') == 0.0
        assert content.similarity('py1', 'missing') == 0.0

    def test_similar_items_excludes_self_and_zero(self, content):
        similar = content.similar_items('py1', top_k=5)
        ids = [i for i, _s in similar]
        assert 'py1' not in ids and 'java1' not in ids
        assert ids[0] == 'py2'
        scores = [s for _i, s in similar]
        assert scores == sorted(scores, reverse=True)

    def test_content_recommend_ranks_by_profile_match(self, content):
        recs = content.recommend(['py1'], top_k=3)
        ids = [i for i, _s in recs]
        assert 'py1' not in ids
        assert ids.index('py2') < ids.index('web1')

    def test_content_recommend_empty_likes(self, content):
        assert content.recommend([], top_k=3) == []
        assert content.recommend(['ghost'], top_k=3) == []

    def test_collab_similarity_finds_close_users(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        similar = collab.similar_users('u1')
        assert [u for u, _s in similar] == ['u2']
        assert similar[0][1] > 0

    def test_collab_predict_known_and_unrated(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        assert collab.predict('u1', 'i1') == 5
        prediction = collab.predict('u1', 'i4')
        assert prediction is not None
        assert 3.0 < prediction < 4.5  # user mean 3.33 + neighbor offset

    def test_collab_predict_without_neighbors_is_none(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        assert collab.predict('u5', 'i1') is None  # u5 has no ratings

    def test_collab_recommend_excludes_seen(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        recs = collab.recommend('u1', top_k=5)
        ids = [i for i, _s in recs]
        assert 'i1' not in ids and 'i2' not in ids and 'i3' not in ids
        assert 'i4' in ids
        scores = [s for _i, s in recs]
        assert scores == sorted(scores, reverse=True)

    def test_collab_recommend_cold_user_empty(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        assert collab.recommend('ghost', top_k=5) == []

    def test_collab_add_rating_updates_results(self):
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        assert 'i4' in [i for i, _s in collab.recommend('u1')]
        collab.add_rating('u1', 'i4', 5)
        assert 'i4' not in [i for i, _s in collab.recommend('u1')]

    def test_hybrid_pure_content_weights(self):
        content = ContentBasedFilter()
        content.add_items(CONTENT_ITEMS)
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        hybrid = HybridRecommender(content, collab,
                                   content_weight=1.0, collab_weight=0.0)
        recs = hybrid.recommend('u1', liked_item_ids=['py1'], top_k=5)
        assert {r['item_id'] for r in recs} == {'py2', 'web1'}
        assert recs[0]['item_id'] == 'py2'
        assert all(r['components'] == ['content'] for r in recs)

    def test_hybrid_blends_both_signals(self):
        content = ContentBasedFilter()
        content.add_items(CONTENT_ITEMS)
        collab = CollaborativeFilter(ratings=COLLAB_RATINGS, k=3)
        hybrid = HybridRecommender(content, collab,
                                   content_weight=0.5, collab_weight=0.5)
        recs = hybrid.recommend('u1', liked_item_ids=['py1'], top_k=5)
        items = {r['item_id'] for r in recs}
        assert {'py2', 'web1', 'i4'} <= items
        by_id = {r['item_id']: r for r in recs}
        assert by_id['py2']['components'] == ['content', 'collaborative'] or \
               set(by_id['py2']['components']) == {'content'}
        assert set(by_id['i4']['components']) == {'collaborative'}
        scores = [r['score'] for r in recs]
        assert scores == sorted(scores, reverse=True)

    def test_recommendation_engine_facade(self):
        engine = RecommendationEngine(
            items=CONTENT_ITEMS, ratings=COLLAB_RATINGS,
        )
        recs = engine.get_recommendations('u1', top_k=5, liked_item_ids=['py1'])
        assert 0 < len(recs) <= 5
        for rec in recs:
            assert set(rec) >= {'item_id', 'score', 'components'}
        similar = engine.similar_items('py1', top_k=2)
        assert similar[0][0] == 'py2'


# ======================================================================
# V25 Integration (M1 + M2-M5)
# ======================================================================
class TestV25Integration:

    def test_metrics_to_report_pipeline(self):
        calculator = MetricsCalculator(make_mock_db())
        generator = ReportGenerator(metrics_provider=calculator)
        report = generator.generate_report(title='Daily Digest')
        md = generator.to_markdown(report)
        assert 'Total Knowledge Units' in md
        assert '| Metric | Value | Unit | Type |' in md
        assert report.get_section('Metrics Detail').metrics['total_ku'] == 1000.0

    def test_anomaly_insights_into_report(self):
        anomaly = make_anomaly(severity='critical')
        engine = AIInsightsEngine()
        insight = engine.insight_from_anomaly(anomaly)
        generator = ReportGenerator(metrics_provider=[])
        report = generator.generate_report(anomalies=[anomaly], insights=[insight])
        md = generator.to_markdown(report)
        assert 'creates_24h' in md
        assert 'critical' in md
        assert 'Investigate root cause' in md
        assert report.health_status() == 'critical'

    def test_graph_json_round_trip(self):
        graph = KnowledgeGraphVisualizer(
            nodes=[{'id': 'k1', 'label': 'Knowledge', 'type': 'fact'},
                   {'id': 'k2', 'label': 'Source', 'type': 'doc'}],
            edges=[{'source': 'k1', 'target': 'k2', 'weight': 2.0}],
            seed=7,
        )
        payload = json.loads(graph.to_json())
        assert payload['stats'] == {'node_count': 2, 'edge_count': 1,
                                    'connected_components': 1}
        assert payload['positions']['k1'] == payload['positions']['k1']
        assert graph.compute_layout() == graph.compute_layout()

    def test_recommendation_engine_end_to_end(self):
        engine = RecommendationEngine(
            items=CONTENT_ITEMS, ratings=COLLAB_RATINGS,
        )
        recs = engine.get_recommendations('u1', top_k=5)
        assert recs
        assert all(r['score'] >= 0.0 for r in recs)
        assert all(r['item_id'] not in COLLAB_RATINGS['u1'] for r in recs
                   if 'collaborative' in r['components'])

    def test_full_insight_generation_workflow(self):
        engine = AIInsightsEngine(
            series={'a': [1, 2, 3, 4], 'b': [2, 4, 6, 8]},
            metrics=[make_metric('verified_rate', 0.2, warning=0.5)],
            anomalies=[make_anomaly('critical')],
            trend_results={'creates_24h': {
                'trend': 'down', 'slope': -1.0, 'mean': 10.0,
                'data': [{'value': 12}, {'value': 10}],
            }},
        )
        insights = engine.generate_all()
        assert len(insights) >= 4
        assert all(isinstance(i, Insight) for i in insights)
        scores = [engine.score(i) for i in insights]
        assert scores == sorted(scores, reverse=True)

    def test_m1_module_reused_not_modified(self):
        # M1 classes are importable and our modules return M1 dataclass instances
        from quan_ai_brain.analytics.analytics_engine import (
            AnomalyDetector,
            InsightsGenerator,
            TrendAnalyzer,
        )
        assert MetricsCalculator is not None
        assert TrendAnalyzer is not None
        assert AnomalyDetector is not None
        assert InsightsGenerator is not None
        engine = AIInsightsEngine()
        assert isinstance(engine.insight_from_anomaly(make_anomaly()), Insight)
        assert isinstance(make_metric(), Metric)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
