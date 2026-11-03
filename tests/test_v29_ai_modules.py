"""Tests for V29 Advanced AI Capabilities modules (M1-M5).

Covers:
- M1 neural_symbolic: HashEmbedder, AttentionPooler, SymbolicRuleEngine,
  NeuralSymbolicBridge (gating + hybrid inference).
- M2 common_sense: ConceptStore (~30 builtin concepts), BFS paths,
  contradiction check, context boost.
- M3 explainable_ai: perturbation attribution, counterfactuals,
  VI/EN explanation templates, confidence calibration.
- M4 transfer_learning: GD-trained linear model, freeze, few-shot
  fine-tune, forgetting metric, distillation.
- M5 multi_agent: BDI deliberation, FIPA-ACL message bus, negotiation,
  task decomposition, consensus vote.

All "neural" components here are toy simulations (hash vectors, hand-
written attention and gradient descent on list[float]) — no torch.
"""

import math

import pytest

from quan_ai_brain.ai.neural_symbolic import (
    Fact,
    HashEmbedder,
    HybridMatch,
    NeuralSymbolicBridge,
    Rule,
    SymbolicRuleEngine,
    AttentionPooler,
    cosine_similarity,
    softmax,
    tokenize,
)
from quan_ai_brain.ai.common_sense import (
    CommonSenseReasoner,
    Concept,
    ConceptStore,
    ContradictionReport,
    InferencePath,
    RelationType,
)
from quan_ai_brain.ai.explainable_ai import (
    AttributionExplainer,
    ConfidenceCalibrator,
    Counterfactual,
    CounterfactualExplainer,
    Explanation,
    ExplanationGenerator,
    ExplainableAI,
)
from quan_ai_brain.ai.transfer_learning import (
    DistillationResult,
    FewShotResult,
    GradientDescentTrainer,
    LinearModel,
    TransferLearningEngine,
    TrainingReport,
)
from quan_ai_brain.ai.multi_agent import (
    ACLMessage,
    BDIAgent,
    ConsensusVote,
    MessageBus,
    MultiAgentSystem,
    NegotiationOutcome,
    Performative,
    TaskDecomposer,
    TaskNode,
    negotiate_price,
)

# =========================================================================
# M1 — Neural Symbolic
# =========================================================================


class TestNeuralSymbolic:
    """M1: toy neural embedder + symbolic rule engine + bridge."""

    # -- tokenizer / helpers ------------------------------------------------
    def test_tokenize_basic(self):
        assert tokenize("Người uống NƯỚC") == ["người", "uống", "nước"]

    def test_tokenize_empty(self):
        assert tokenize("") == []
        assert tokenize("!!!") == []

    def test_softmax_sums_to_one(self):
        weights = softmax([1.0, 2.0, 3.0])
        assert math.isclose(sum(weights), 1.0, rel_tol=1e-9)
        assert weights[-1] == max(weights)

    def test_softmax_empty(self):
        assert softmax([]) == []

    def test_cosine_similarity_identical(self):
        v = [1.0, 2.0, 3.0]
        assert math.isclose(cosine_similarity(v, v), 1.0, rel_tol=1e-9)

    def test_cosine_similarity_orthogonal(self):
        assert math.isclose(cosine_similarity([1.0, 0.0], [0.0, 1.0]), 0.0,
                            abs_tol=1e-12)

    def test_cosine_similarity_zero_vector(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    # -- embedder -----------------------------------------------------------
    def test_embedder_deterministic(self):
        e1 = HashEmbedder(dim=16, seed=1).embed_text("người uống nước")
        e2 = HashEmbedder(dim=16, seed=1).embed_text("người uống nước")
        assert e1 == e2

    def test_embedder_dim(self):
        assert len(HashEmbedder(dim=24).embed_text("abc def")) == 24

    def test_embedder_empty_text_zero_vector(self):
        assert HashEmbedder(dim=8).embed_text("") == [0.0] * 8

    def test_embedder_similar_text_higher_than_unrelated(self):
        emb = HashEmbedder(dim=64)
        sim_same = emb.similarity("người uống nước", "người uống nước lọc")
        sim_diff = emb.similarity("người uống nước", "máy tính bộ nhớ")
        assert sim_same > sim_diff

    def test_embed_token_unit_norm(self):
        vec = HashEmbedder(dim=32).embed_token("nước")
        norm = math.sqrt(sum(v * v for v in vec))
        assert math.isclose(norm, 1.0, rel_tol=1e-9)

    # -- attention pooler ----------------------------------------------------
    def test_attention_weights_sum_to_one(self):
        vectors = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]]
        weights = AttentionPooler().attention_weights(vectors)
        assert math.isclose(sum(weights), 1.0, rel_tol=1e-9)
        assert all(w > 0 for w in weights)

    def test_attention_pool_preserves_dim(self):
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        pooled = AttentionPooler().pool(vectors)
        assert len(pooled) == 2

    def test_attention_pool_identical_vectors(self):
        vectors = [[1.0, 1.0]] * 3
        pooled = AttentionPooler().pool(vectors)
        assert all(math.isclose(p, 1.0) for p in pooled)

    # -- symbolic engine -------------------------------------------------------
    def test_add_and_query_fact(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        facts = engine.query("uống")
        assert len(facts) == 1
        assert facts[0].args == ("người", "nước")

    def test_query_with_args_filter(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        engine.add_fact("uống", ["chó", "nước"])
        assert len(engine.query("uống", ["người", "nước"])) == 1
        assert engine.query("uống", ["mèo", "nước"]) == []

    def test_duplicate_fact_not_added(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        engine.add_fact("uống", ["người", "nước"])
        assert len(engine.facts) == 1

    def test_forward_chain_derives_transitive_closure(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("is_a", ["chim", "động_vật"])
        engine.add_fact("is_a", ["động_vật", "sinh_vật"])
        engine.add_rule(
            "is_a_transitivity",
            premises=[["is_a", "?x", "?y"], ["is_a", "?y", "?z"]],
            conclusion=["is_a", "?x", "?z"],
        )
        derived = engine.forward_chain()
        keys = {f.key for f in derived}
        assert "is_a(chim,sinh_vật)" in keys

    def test_forward_chain_fixpoint_no_duplicates(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("is_a", ["a", "b"])
        engine.add_fact("is_a", ["b", "c"])
        engine.add_rule(
            "trans",
            premises=[["is_a", "?x", "?y"], ["is_a", "?y", "?z"]],
            conclusion=["is_a", "?x", "?z"],
        )
        engine.forward_chain()
        total = len(engine.facts)
        engine.forward_chain()  # second run derives nothing new
        assert len(engine.facts) == total

    def test_rule_with_constant_binding(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("is_a", ["người", "sinh_vật"])
        engine.add_fact("capable_of", ["sinh_vật", "sống"])
        engine.add_rule(
            "person_alive",
            premises=[["is_a", "?x", "sinh_vật"],
                      ["capable_of", "sinh_vật", "?act"]],
            conclusion=["capable_of", "?x", "?act"],
        )
        derived = engine.forward_chain()
        keys = {f.key for f in derived}
        assert "capable_of(người,sống)" in keys

    def test_derived_confidence_from_min_premise(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("is_a", ["chim", "động_vật"], confidence=0.9)
        engine.add_fact("is_a", ["động_vật", "sinh_vật"], confidence=0.8)
        engine.add_rule("trans",
                        premises=[["is_a", "?x", "?y"], ["is_a", "?y", "?z"]],
                        conclusion=["is_a", "?x", "?z"])
        derived = engine.forward_chain()
        conf = {f.key: f.confidence for f in derived}
        assert math.isclose(conf["is_a(chim,sinh_vật)"], 0.8)

    def test_ask_pattern_binds_variables(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        matches = engine.ask_pattern(["uống", "?x", "nước"])
        assert len(matches) == 1
        assert matches[0][1]["?x"] == "người"

    # -- bridge ---------------------------------------------------------------
    def test_bridge_neural_score_range(self):
        bridge = NeuralSymbolicBridge()
        fact = Fact("uống", ("người", "nước"))
        score = bridge.neural_score(fact, "người uống nước")
        assert 0.0 <= score <= 1.0

    def test_bridge_gating_discounts_low_neural_score(self):
        bridge = NeuralSymbolicBridge(alpha=0.5)
        high = bridge.gate(1.0, 0.9)
        low = bridge.gate(1.0, 0.1)
        assert high > low
        assert math.isclose(high, 0.5 + 0.5 * 0.9, rel_tol=1e-9)

    def test_bridge_hybrid_query_ranks_relevant_first(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        engine.add_fact("sở_hữu", ["người", "máy_tính"])
        bridge = NeuralSymbolicBridge()
        result = bridge.hybrid_query(engine, "người uống nước")
        assert result.best is not None
        assert result.best.fact.predicate == "uống"
        assert result.confidence > 0

    def test_bridge_extract_symbols(self):
        bridge = NeuralSymbolicBridge()
        symbols = bridge.extract_symbols("người muốn uống nước ngay",
                                         ["uống", "nước", "ăn"])
        assert symbols == ["uống", "nước"]

    def test_hybrid_match_to_dict_roundtrip(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        bridge = NeuralSymbolicBridge()
        result = bridge.hybrid_query(engine, "uống nước")
        d = result.to_dict()
        assert d["matches"][0]["fact"]["predicate"] == "uống"
        assert 0.0 <= d["confidence"] <= 1.0

    def test_rule_to_dict(self):
        rule = Rule("r1", [["is_a", "?x", "?y"]], ["is_a", "?x", "?y"], 0.7)
        d = rule.to_dict()
        assert d["name"] == "r1"
        assert d["base_confidence"] == 0.7

    def test_fact_to_text(self):
        assert Fact("uống", ("người", "nước")).to_text() == "uống người nước"


# =========================================================================
# M2 — Common Sense
# =========================================================================


class TestCommonSense:
    """M2: concept store, BFS inference, contradiction, context boost."""

    def test_builtin_store_has_30_concepts(self):
        store = ConceptStore()
        assert len(store) >= 30

    def test_store_contains_core_concepts(self):
        store = ConceptStore()
        for name in ("người", "uống", "nước", "lửa", "nóng"):
            assert name in store

    def test_empty_store(self):
        store = ConceptStore(load_builtin=False)
        assert len(store) == 0

    def test_add_concept_and_relation(self):
        store = ConceptStore(load_builtin=False)
        store.add_concept(Concept(name="xe"))
        store.add_relation("xe", RelationType.CAPABLE_OF, "chạy")
        assert store.get("xe") is not None
        assert ("capable_of", "chạy") in [(r.value if False else r.value, t) for r, t in []] or \
            any(rel == RelationType.CAPABLE_OF and t == "chạy"
                for rel, t in store.neighbors("xe"))

    def test_add_relation_auto_creates_concepts(self):
        store = ConceptStore(load_builtin=False)
        store.add_relation("a", RelationType.IS_A, "b")
        assert "a" in store and "b" in store

    def test_relation_type_values(self):
        assert RelationType.IS_A.value == "is_a"
        assert RelationType.HAS.value == "has"
        assert RelationType.CAPABLE_OF.value == "capable_of"
        assert RelationType.CAUSES.value == "causes"

    def test_direct_path_found(self):
        store = ConceptStore()
        path = store.find_path("lửa", "nóng")
        assert path is not None
        assert path.length == 1
        assert path.steps[0][0] == RelationType.CAUSES

    def test_multi_hop_path_nguoi_to_sinh_vat(self):
        store = ConceptStore()
        path = store.find_path("cá", "vật_thể")
        assert path is not None
        assert path.end == "vật_thể"
        assert path.length >= 2  # cá -> động_vật -> sinh_vật -> vật_thể

    def test_no_path_returns_none(self):
        store = ConceptStore()
        assert store.find_path("nước", "cpu") is None

    def test_path_confidence_decays_with_length(self):
        store = ConceptStore()
        short = store.find_path("lửa", "nóng")
        long = store.find_path("cá", "vật_thể")
        assert short.confidence > long.confidence

    def test_find_paths_from_limited_depth(self):
        store = ConceptStore()
        paths = store.find_paths_from("người", max_depth=1)
        assert all(p.length == 1 for p in paths)
        assert any(p.end == "uống" for p in paths)

    def test_infer_returns_paths(self):
        reasoner = CommonSenseReasoner()
        paths = reasoner.infer("lửa")
        assert len(paths) > 0
        assert all(isinstance(p, InferencePath) for p in paths)

    def test_explain_chain_vietnamese(self):
        reasoner = CommonSenseReasoner()
        text = reasoner.explain_chain("lửa", "nóng", lang="vi")
        assert text is not None
        assert "lửa" in text and "nóng" in text
        assert "gây ra" in text

    def test_explain_chain_english(self):
        reasoner = CommonSenseReasoner()
        text = reasoner.explain_chain("lửa", "nóng", lang="en")
        assert text is not None
        assert "causes" in text

    def test_explain_chain_no_path(self):
        reasoner = CommonSenseReasoner()
        assert reasoner.explain_chain("nước", "cpu") is None

    def test_contradiction_clean_concept(self):
        reasoner = CommonSenseReasoner()
        report = reasoner.check_contradiction("lửa")
        assert isinstance(report, ContradictionReport)
        assert not report.has_contradiction

    def test_contradiction_detected(self):
        reasoner = CommonSenseReasoner()
        reasoner.store.add_relation("thử_nghiệm", RelationType.CAUSES, "khát")
        reasoner.store.add_relation("thử_nghiệm", RelationType.CAUSES, "bớt_khát")
        report = reasoner.check_contradiction("thử_nghiệm")
        assert report.has_contradiction

    def test_context_boost_reorders(self):
        reasoner = CommonSenseReasoner()
        paths = reasoner.store.find_paths_from("người", max_depth=1)
        boosted = reasoner.context_boost(paths, context=["uống"])
        top = boosted[0]
        assert top.end == "uống"
        # boosted conf must exceed the same path's original confidence
        original = next(p for p in paths if p.end == "uống")
        assert top.confidence > original.confidence

    def test_context_boost_capped_at_one(self):
        reasoner = CommonSenseReasoner()
        path = InferencePath("a", "b", [(RelationType.IS_A, "b")], 0.95)
        boosted = reasoner.context_boost([path], context=["b"])
        assert boosted[0].confidence == 1.0

    def test_answer_capable_question(self):
        reasoner = CommonSenseReasoner()
        result = reasoner.answer("người có thể uống nước không?")
        assert result["answer"] is True
        assert result["explanation"] is not None
        assert result["confidence"] > 0

    def test_answer_unknown_pair(self):
        reasoner = CommonSenseReasoner()
        result = reasoner.answer("nước và cpu")
        assert result["answer"] is None

    def test_concept_to_dict(self):
        concept = Concept("nước", "Nước", "water",
                          {"is_a": ["chất_lỏng"]})
        d = concept.to_dict()
        assert d["name"] == "nước"
        assert d["relations"]["is_a"] == ["chất_lỏng"]

    def test_inference_path_to_dict(self):
        path = InferencePath("a", "b", [(RelationType.CAUSES, "b")], 0.9)
        d = path.to_dict()
        assert d["steps"] == [["causes", "b"]]


# =========================================================================
# M3 — Explainable AI
# =========================================================================


class TestExplainableAI:
    """M3: attribution, counterfactuals, templates, calibration."""

    @staticmethod
    def _score_fn(features):
        # decision: confident when f1 and f2 are high, f3 is (mild) noise;
        # supports any feature count >= 1 for generic tests
        weights = [0.4, 0.4, 0.1]
        total = sum(w * v for w, v in zip(weights, features)) + 0.05
        return total

    def test_attribution_identifies_top_feature(self):
        names = ["f1", "f2", "f3"]
        explainer = AttributionExplainer(self._score_fn, names)
        attribution = explainer.explain([1.0, 0.9, 0.1])
        top = attribution.top_feature
        assert top is not None
        assert top[0] in ("f1", "f2")
        assert top[1] > 0.3

    def test_attribution_noise_feature_small_delta(self):
        names = ["f1", "f2", "f3"]
        explainer = AttributionExplainer(self._score_fn, names)
        attribution = explainer.explain([1.0, 0.9, 0.1])
        assert attribution.scores["f3"] < 0.2

    def test_attribution_base_score(self):
        names = ["f1", "f2", "f3"]
        explainer = AttributionExplainer(self._score_fn, names)
        attribution = explainer.explain([1.0, 0.9, 0.1])
        assert math.isclose(attribution.base_score,
                            self._score_fn([1.0, 0.9, 0.1]))

    def test_attribution_wrong_length_raises(self):
        explainer = AttributionExplainer(self._score_fn, ["a", "b", "c"])
        with pytest.raises(ValueError):
            explainer.explain([1.0, 2.0])

    def test_attribution_custom_baseline(self):
        names = ["f1", "f2", "f3"]
        explainer = AttributionExplainer(self._score_fn, names,
                                         baseline=[0.0, 0.0, 0.0])
        attribution = explainer.explain([1.0, 1.0, 1.0])
        assert attribution.ranked[0][1] > 0

    def test_counterfactual_finds_flip(self):
        names = ["f1", "f2", "f3"]
        explainer = CounterfactualExplainer(self._score_fn, names,
                                            threshold=0.5)
        cf_list = explainer.explain([1.0, 1.0, 0.0])
        assert cf_list
        assert all(c.flipped for c in cf_list)
        assert all(isinstance(c, Counterfactual) for c in cf_list)

    def test_counterfactual_single_feature_change(self):
        names = ["f1", "f2", "f3"]
        explainer = CounterfactualExplainer(self._score_fn, names)
        cf_list = explainer.explain([1.0, 1.0, 0.0])
        assert all(len(c.changes) == 1 for c in cf_list)

    def test_counterfactual_none_when_unflippable(self):
        # constant score can never flip
        explainer = CounterfactualExplainer(lambda f: 0.9, ["a"], threshold=0.5)
        assert explainer.explain([0.5]) == []

    def test_counterfactual_alias(self):
        explainer = CounterfactualExplainer(self._score_fn, ["f1", "f2", "f3"])
        assert explainer.find_counterfactuals([1.0, 0.0, 0.0]) == \
            explainer.explain([1.0, 0.0, 0.0])

    def test_explanation_generator_vietnamese(self):
        gen = ExplanationGenerator("vi")
        explainer = AttributionExplainer(self._score_fn, ["giá", "khối_lượng"])
        attribution = explainer.explain([1.0, 0.2])
        explanation = gen.explain(attribution, decision="mua hàng")
        assert isinstance(explanation, Explanation)
        assert "mua hàng" in explanation.text
        assert explanation.language == "vi"

    def test_explanation_generator_english(self):
        gen = ExplanationGenerator("en")
        explainer = AttributionExplainer(self._score_fn, ["price", "weight"])
        attribution = explainer.explain([1.0, 0.2])
        explanation = gen.explain(attribution, decision="buy")
        assert explanation.language == "en"
        assert "decision" in explanation.text.lower()

    def test_explanation_includes_counterfactual(self):
        gen = ExplanationGenerator("vi")
        names = ["f1", "f2"]
        attribution = AttributionExplainer(self._score_fn, names).explain([1.0, 0.0])
        cf = CounterfactualExplainer(self._score_fn, names).explain([1.0, 0.0])
        explanation = gen.explain(attribution, counterfactuals=cf)
        assert "đảo ngược" in explanation.text or "nếu" in explanation.text.lower()

    def test_explainable_ai_facade(self):
        xai = ExplainableAI(self._score_fn, ["f1", "f2", "f3"], language="vi")
        explanation = xai.explain([1.0, 0.9, 0.1], decision="duyệt")
        assert explanation.text
        assert explanation.top_feature in ("f1", "f2")
        assert explanation.counterfactuals  # found some flip

    def test_explainable_ai_facade_no_cf(self):
        xai = ExplainableAI(self._score_fn, ["f1", "f2", "f3"])
        explanation = xai.explain([1.0, 0.9, 0.1], with_counterfactuals=False)
        assert explanation.counterfactuals == []

    def test_calibrator_identity_without_history(self):
        calibrator = ConfidenceCalibrator(n_bins=10)
        assert calibrator.calibrate(0.7) == 0.7
        assert calibrator.bin_accuracy(0.7) is None

    def test_calibrator_bin_accuracy(self):
        calibrator = ConfidenceCalibrator(n_bins=10)
        for _ in range(10):
            calibrator.record(0.75, True)
        for _ in range(10):
            calibrator.record(0.75, False)
        assert math.isclose(calibrator.bin_accuracy(0.75), 0.5)

    def test_calibrator_pulls_toward_observed_accuracy(self):
        calibrator = ConfidenceCalibrator(n_bins=10)
        for _ in range(20):
            calibrator.record(0.8, False)  # model wrong at high scores
        calibrated = calibrator.calibrate(0.8)
        assert calibrated < 0.8

    def test_calibrator_records_clamped(self):
        calibrator = ConfidenceCalibrator()
        calibrator.record(1.5, True)
        assert calibrator.history[0][0] == 1.0

    def test_reliability_diagram_structure(self):
        calibrator = ConfidenceCalibrator(n_bins=5)
        for i in range(20):
            calibrator.record(0.55, True)
        diagram = calibrator.reliability_diagram()
        assert len(diagram) == 5
        hot = diagram[2]  # bin covering 0.4-0.6
        assert hot["count"] == 20
        assert math.isclose(hot["accuracy"], 1.0)

    def test_expected_calibration_error(self):
        calibrator = ConfidenceCalibrator(n_bins=10)
        for _ in range(10):
            calibrator.record(0.8, True)
        ece = calibrator.expected_calibration_error()
        assert ece is not None
        assert 0.0 <= ece <= 1.0

    def test_expected_calibration_error_empty(self):
        assert ConfidenceCalibrator().expected_calibration_error() is None

    def test_calibrator_invalid_bins(self):
        with pytest.raises(ValueError):
            ConfidenceCalibrator(n_bins=0)


# =========================================================================
# M4 — Transfer Learning
# =========================================================================


class TestTransferLearning:
    """M4: GD linear model, freeze, few-shot, forgetting, distillation."""

    @staticmethod
    def _source_data(n=40, dim=4):
        X = [[0.1 * (i % 10), 0.2 * ((i * 3) % 7), 0.3 * (i % 5),
              0.4 * (i % 3)] for i in range(n)]
        y = [2.0 * x[0] + 1.0 * x[1] - 0.5 * x[2] + 0.5 for x in X]
        return X, y

    def test_gd_reduces_loss(self):
        X, y = self._source_data()
        model = LinearModel(4)
        trainer = GradientDescentTrainer(lr=0.05, epochs=200)
        report = trainer.train(model, X, y, task="source")
        assert isinstance(report, TrainingReport)
        assert report.final_loss < report.initial_loss

    def test_gd_learns_true_relationship(self):
        X, y = self._source_data()
        model = LinearModel(4)
        GradientDescentTrainer(lr=0.05, epochs=400).train(model, X, y)
        probe = [0.5, 0.3, 0.2, 0.1]
        expected = 2.0 * probe[0] + 1.0 * probe[1] - 0.5 * probe[2] + 0.5
        assert math.isclose(model.predict(probe), expected, abs_tol=0.15)

    def test_linear_model_predict_bias(self):
        model = LinearModel(2, weights=[0.0, 0.0], bias=1.5)
        assert model.predict([3.0, 4.0]) == 1.5

    def test_linear_model_dim_mismatch(self):
        model = LinearModel(3)
        with pytest.raises(ValueError):
            model.predict([1.0, 2.0])

    def test_freeze_all_prevents_weight_update(self):
        X, y = self._source_data(20)
        model = LinearModel(4)
        before = list(model.weights)
        model.freeze_layer()  # all
        GradientDescentTrainer(lr=0.1, epochs=50).train(model, X, y)
        assert model.weights == before

    def test_freeze_partial(self):
        X, y = self._source_data(20)
        model = LinearModel(4)
        before = list(model.weights)
        model.freeze_layer([0, 1])
        GradientDescentTrainer(lr=0.1, epochs=50).train(model, X, y)
        assert model.weights[0] == before[0]
        assert model.weights[1] == before[1]
        assert (model.weights[2] != before[2]) or (model.weights[3] != before[3])

    def test_freeze_index_out_of_range(self):
        model = LinearModel(2)
        with pytest.raises(IndexError):
            model.freeze_layer([5])

    def test_unfreeze_all(self):
        model = LinearModel(3)
        model.freeze_layer()
        model.unfreeze_all()
        assert not any(model.frozen)

    def test_model_copy_independent(self):
        model = LinearModel(2, weights=[1.0, 2.0], bias=0.5)
        clone = model.copy()
        clone.weights[0] = 99.0
        assert model.weights[0] == 1.0

    def test_transfer_improves_target_vs_scratch(self):
        X_src, y_src = self._source_data(40)
        # target domain: scaled features, same weight structure
        X_tgt = [[x[0] * 2, x[1] * 2, x[2] * 2, x[3] * 2] for x in X_src[:8]]
        y_tgt = [2.0 * x[0] + 1.0 * x[1] - 0.5 * x[2] + 1.0 for x in X_tgt]

        engine = TransferLearningEngine(lr=0.05, epochs=300,
                                        fine_tune_epochs=150)
        # path A: transfer
        model = engine.train_source(X_src, y_src)
        engine.freeze_layer(model, [0, 1])  # keep source semantics
        transfer_result = engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=5)
        # path B: fresh model
        fresh = LinearModel(4)
        GradientDescentTrainer(lr=0.05, epochs=150).train(fresh, X_tgt, y_tgt)
        fresh_mse = fresh.mse(X_tgt, y_tgt)
        assert transfer_result.target_mse_after <= fresh_mse * 1.5 + 1e-9
        assert transfer_result.target_mse_after < transfer_result.target_mse_before

    def test_few_shot_uses_only_k_samples(self):
        X_src, y_src = self._source_data(30)
        engine = TransferLearningEngine(epochs=100, fine_tune_epochs=50)
        model = engine.train_source(X_src, y_src)
        X_tgt = [[0.2, 0.1, 0.4, 0.3]] * 12
        y_tgt = [1.0] * 12
        result = engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=5)
        assert result.k_samples == 5

    def test_few_shot_invalid_k(self):
        engine = TransferLearningEngine()
        with pytest.raises(ValueError):
            engine.few_shot_fine_tune(LinearModel(4), [[0.1, 0, 0, 0]],
                                      [1.0], k=0)

    def test_forgetting_metric_zero_when_frozen(self):
        X_src, y_src = self._source_data(40)
        engine = TransferLearningEngine()
        model = engine.train_source(X_src, y_src)
        reference = model.copy()
        model.freeze_layer()  # freeze everything -> source unchanged
        X_tgt = [[0.1, 0.2, 0.3, 0.4]] * 4
        y_tgt = [1.0] * 4
        engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=4,
                                  X_source_eval=X_src, y_source_eval=y_src)
        forgetting = engine.forgetting_metric(model, X_src, y_src,
                                              reference_model=reference)
        assert forgetting == 0.0

    def test_forgetting_detected_when_unfrozen(self):
        X_src, y_src = self._source_data(40)
        engine = TransferLearningEngine()
        model = engine.train_source(X_src, y_src)
        reference = model.copy()
        # aggressive fine-tune on wildly different target, nothing frozen
        X_tgt = [[5.0, -3.0, 2.0, -1.0]] * 5
        y_tgt = [50.0] * 5
        engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=5,
                                  X_source_eval=X_src, y_source_eval=y_src)
        forgetting = engine.forgetting_metric(model, X_src, y_src,
                                              reference_model=reference)
        assert forgetting > 0.0

    def test_few_shot_result_forgetting_field(self):
        X_src, y_src = self._source_data(30)
        engine = TransferLearningEngine()
        model = engine.train_source(X_src, y_src)
        X_tgt = [[1.0, 1.0, 1.0, 1.0]] * 3
        y_tgt = [0.0] * 3
        result = engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=3,
                                           X_source_eval=X_src,
                                           y_source_eval=y_src)
        assert isinstance(result, FewShotResult)
        assert 0.0 <= result.forgetting <= 1.0

    def test_distillation_student_approaches_teacher(self):
        X_src, y_src = self._source_data(40)
        engine = TransferLearningEngine()
        teacher = engine.train_source(X_src, y_src)
        result = engine.distill(teacher, X_src, epochs=400, lr=0.05)
        assert isinstance(result, DistillationResult)
        assert result.student_final_mse_vs_teacher < \
            result.student_initial_mse_vs_teacher
        assert result.teacher_agreement > 0.5

    def test_distillation_result_to_dict(self):
        engine = TransferLearningEngine()
        teacher = LinearModel(2, weights=[1.0, -1.0])
        result = engine.distill(teacher, [[0.5, 0.5]], epochs=10)
        d = result.to_dict()
        assert "teacher_agreement" in d

    def test_training_report_to_dict(self):
        report = TrainingReport("source", 10, 1.0, 0.5)
        assert report.to_dict()["final_loss"] == 0.5


# =========================================================================
# M5 — Multi-Agent
# =========================================================================


class TestMultiAgent:
    """M5: BDI, message bus, negotiation, decomposition, consensus."""

    # -- BDI -----------------------------------------------------------------
    def test_bdi_add_belief(self):
        agent = BDIAgent("a1")
        belief = agent.add_belief("pin", 85)
        assert agent.beliefs["pin"].value == 85
        assert belief.revision == 0

    def test_bdi_belief_revision_increments(self):
        agent = BDIAgent("a1")
        agent.add_belief("pin", 85)
        agent.add_belief("pin", 70)
        assert agent.beliefs["pin"].value == 70
        assert agent.beliefs["pin"].revision == 1

    def test_bdi_drop_belief(self):
        agent = BDIAgent("a1")
        agent.add_belief("pin", 85)
        assert agent.drop_belief("pin")
        assert "pin" not in agent.beliefs
        assert not agent.drop_belief("pin")

    def test_bdi_deliberation_commits_and_executes(self):
        agent = BDIAgent("worker")
        agent.add_desire("baocao", priority=0.9)
        summary = agent.deliberate()
        assert summary["desires_selected"] == ["baocao"]
        assert summary["executed"] == "act_baocao"
        assert agent.intentions[0].status.value == "done"

    def test_bdi_priority_order(self):
        agent = BDIAgent("worker")
        agent.add_desire("task_a", priority=0.3)
        agent.add_desire("task_b", priority=0.9)
        agent.deliberate()
        # highest priority desire committed first, executed first
        assert agent.intentions[0].desire_name == "task_b"

    def test_bdi_no_duplicate_intentions(self):
        agent = BDIAgent("worker")
        agent.add_desire("baocao", priority=0.9)
        agent.deliberate()
        agent.deliberate()
        assert len(agent.intentions) == 1

    def test_bdi_plan_factory(self):
        agent = BDIAgent("planner")
        agent.plan_factory = lambda desire, ag: ["b1", "b2"]
        agent.add_desire("x", 1.0)
        agent.deliberate()
        assert agent.intentions[0].progress == 1
        assert agent.intentions[0].status.value == "active"
        agent.deliberate()
        assert agent.intentions[0].status.value == "done"
        assert agent.desires["x"].achieved

    def test_bdi_action_log(self):
        agent = BDIAgent("worker")
        agent.add_desire("baocao", 1.0)
        agent.deliberate()
        assert agent.action_log[0]["agent"] == "worker"
        assert agent.action_log[0]["action"] == "act_baocao"

    # -- message bus ------------------------------------------------------------
    def test_bus_send_receive(self):
        bus = MessageBus()
        bus.send(ACLMessage(Performative.REQUEST, "a", "b", {"x": 1}))
        msg = bus.receive("b")
        assert msg is not None
        assert msg.performative == Performative.REQUEST
        assert bus.receive("b") is None

    def test_bus_filter_by_performative(self):
        bus = MessageBus()
        bus.send(ACLMessage(Performative.INFORM, "a", "b", "i"))
        bus.send(ACLMessage(Performative.REQUEST, "a", "b", "r"))
        msg = bus.receive("b", Performative.INFORM)
        assert msg.content == "i"
        msg2 = bus.receive("b", Performative.REQUEST)
        assert msg2.content == "r"

    def test_bus_history(self):
        bus = MessageBus()
        bus.send(ACLMessage(Performative.PROPOSE, "a", "b", 1))
        bus.send(ACLMessage(Performative.ACCEPT_PROPOSAL, "b", "a", 1))
        assert len(bus.history) == 2
        assert bus.history[0].performative == Performative.PROPOSE

    def test_bus_drain(self):
        bus = MessageBus()
        bus.send(ACLMessage(Performative.INFORM, "a", "b", "1"))
        bus.send(ACLMessage(Performative.INFORM, "a", "b", "2"))
        drained = bus.drain("b")
        assert len(drained) == 2
        assert bus.receive("b") is None

    def test_performative_values(self):
        assert Performative.REQUEST.value == "request"
        assert Performative.ACCEPT_PROPOSAL.value == "accept"
        assert Performative.REJECT_PROPOSAL.value == "reject"

    # -- negotiation -------------------------------------------------------------
    def test_negotiation_agrees_when_zopas_overlap(self):
        outcome = negotiate_price(buyer_reserve=100.0, seller_reserve=80.0)
        assert isinstance(outcome, NegotiationOutcome)
        assert outcome.agreed
        assert outcome.final_price is not None
        assert 80.0 <= outcome.final_price <= 100.0

    def test_negotiation_fails_when_no_overlap(self):
        outcome = negotiate_price(buyer_reserve=50.0, seller_reserve=120.0,
                                  max_rounds=8)
        assert not outcome.agreed
        assert outcome.final_price is None

    def test_negotiation_logs_fipa_messages(self):
        bus = MessageBus()
        negotiate_price(buyer_reserve=100.0, seller_reserve=80.0, bus=bus)
        performatives = {m.performative for m in bus.history}
        assert Performative.PROPOSE in performatives
        assert Performative.ACCEPT_PROPOSAL in performatives

    def test_negotiation_reject_logged_when_no_deal(self):
        bus = MessageBus()
        negotiate_price(buyer_reserve=40.0, seller_reserve=90.0,
                        max_rounds=3, bus=bus)
        assert any(m.performative == Performative.REJECT_PROPOSAL
                   for m in bus.history)

    # -- task decomposition ----------------------------------------------------
    def test_decompose_report_goal(self):
        decomposer = TaskDecomposer()
        tree = decomposer.decompose("baocao doanh thu", agents=["a1", "a2", "a3"])
        assert tree.name == "baocao doanh thu"
        assert len(tree.children) == 3
        assert all(child.agent for child in tree.children)

    def test_decompose_unknown_goal_generates_subtasks(self):
        decomposer = TaskDecomposer()
        tree = decomposer.decompose("nganhangviproc", agents=["a1"])
        assert len(tree.children) >= 2

    def test_decompose_assign_round_robin(self):
        decomposer = TaskDecomposer()
        tree = decomposer.decompose("report q4", agents=["a", "b"])
        agents = [child.agent for child in tree.children]
        assert agents == ["a", "b", "a"]

    def test_task_node_walk_and_leaves(self):
        root = TaskNode("root", children=[TaskNode("c1"),
                                          TaskNode("c2", children=[TaskNode("g1")])])
        assert len(root.walk()) == 4
        assert [leaf.name for leaf in root.leaves()] == ["c1", "g1"]

    def test_task_node_to_dict(self):
        tree = TaskNode("goal", agent="a1", children=[TaskNode("sub", agent="a2")])
        d = tree.to_dict()
        assert d["agent"] == "a1"
        assert d["children"][0]["name"] == "sub"

    # -- consensus ---------------------------------------------------------------
    def test_consensus_majority(self):
        vote = ConsensusVote()
        result = vote.vote({"a1": "phương_án_A", "a2": "phương_án_A",
                            "a3": "phương_án_B"})
        assert result.winner == "phương_án_A"
        assert result.majority
        assert result.tally["phương_án_A"] == 2

    def test_consensus_no_majority(self):
        vote = ConsensusVote()
        result = vote.vote({"a1": "x", "a2": "y", "a3": "z"})
        assert result.winner in ("x", "y", "z")  # tie broken deterministically
        assert not result.majority

    def test_consensus_empty(self):
        result = ConsensusVote().vote({})
        assert result.winner is None
        assert not result.majority

    def test_consensus_logs_inform_messages(self):
        bus = MessageBus()
        ConsensusVote(bus).vote({"a1": "opt1", "a2": "opt2"})
        assert all(m.performative == Performative.INFORM
                   for m in bus.history)
        assert len(bus.history) == 2

    # -- system facade ------------------------------------------------------------
    def test_system_add_agent(self):
        system = MultiAgentSystem()
        system.add_agent("researcher", ["tìm_kiểm"])
        assert "researcher" in system.agents
        assert system.agents["researcher"].capabilities == ["tìm_kiểm"]

    def test_request_capability_success_informs(self):
        system = MultiAgentSystem()
        system.add_agent("db", ["truy_vấn"])
        reply = system.request_capability("planner", "db", "truy_vấn")
        assert reply is not None
        assert reply.performative == Performative.INFORM

    def test_request_capability_missing_rejects(self):
        system = MultiAgentSystem()
        system.add_agent("db", ["truy_vấn"])
        reply = system.request_capability("planner", "db", "sửa_phần_cứng")
        assert reply.performative == Performative.REJECT_PROPOSAL

    def test_request_unknown_agent_returns_none(self):
        system = MultiAgentSystem()
        assert system.request_capability("planner", "ghost", "x") is None


# =========================================================================
# Integration (M1-M5 combined)
# =========================================================================


class TestV29Integration:
    """Cross-module integration: pipeline over all five modules."""

    def test_full_pipeline_symbolic_common_sense_xai(self):
        # M1: derive facts, M2: common sense check, M3: explain the decision
        engine = SymbolicRuleEngine()
        engine.add_fact("is_a", ["người", "sinh_vật"], confidence=0.95)
        engine.add_fact("capable_of", ["sinh_vật", "uống"], confidence=0.9)
        engine.add_rule(
            "capable_propagation",
            premises=[["is_a", "?x", "?y"], ["capable_of", "?y", "?a"]],
            conclusion=["capable_of", "?x", "?a"],
        )
        derived = engine.forward_chain()
        assert any(f.key == "capable_of(người,uống)" for f in derived)

        reasoner = CommonSenseReasoner()
        cs = reasoner.answer("người có thể uống nước không?")
        assert cs["answer"] is True

        score_fn = lambda feats: min(1.0, feats[0] * 0.6 + feats[1] * 0.4)
        xai = ExplainableAI(score_fn, ["symbolic_conf", "cs_conf"], "vi")
        explanation = xai.explain([0.9, float(cs["confidence"])],
                                  decision="cho_phép_uống")
        assert explanation.text
        assert explanation.top_feature in ("symbolic_conf", "cs_conf")

    def test_neural_bridge_over_rule_engine_facts(self):
        engine = SymbolicRuleEngine()
        engine.add_fact("uống", ["người", "nước"])
        engine.add_fact("causes", ["lửa", "nóng"])
        bridge = NeuralSymbolicBridge()
        result = bridge.hybrid_query(engine, "lửa gây ra nóng")
        assert result.best.fact.predicate == "causes"
        assert result.best.gated_confidence > 0

    def test_transfer_pipeline_end_to_end(self):
        X_src, y_src = TestTransferLearning._source_data(40)
        engine = TransferLearningEngine()
        model = engine.train_source(X_src, y_src)
        X_tgt = [[x[0] * 2, x[1] * 2, x[2] * 2, x[3] * 2] for x in X_src[:6]]
        y_tgt = [2.0 * x[0] + 1.0 * x[1] - 0.5 * x[2] + 1.0 for x in X_tgt]
        result = engine.few_shot_fine_tune(model, X_tgt, y_tgt, k=6,
                                           X_source_eval=X_src,
                                           y_source_eval=y_src)
        assert result.target_mse_after < result.target_mse_before
        distill = engine.distill(model, X_tgt)
        assert distill.student_final_mse_vs_teacher >= 0.0

    def test_multi_agent_with_consensus_and_negotiation(self):
        system = MultiAgentSystem()
        for name in ("a1", "a2", "a3"):
            system.add_agent(name, ["xử_lý"])
        vote = ConsensusVote(system.bus)
        result = vote.vote({"a1": "plan_A", "a2": "plan_A", "a3": "plan_B"})
        assert result.winner == "plan_A" and result.majority
        outcome = negotiate_price(buyer_reserve=90.0, seller_reserve=70.0,
                                  bus=system.bus)
        assert outcome.agreed
        assert len(system.bus.history) > 3

    def test_embedder_feeds_common_sense_context(self):
        # toy "neural" context extraction feeding the common-sense booster
        emb = HashEmbedder(dim=16)
        text = "người uống nước"
        vec = emb.embed_text(text)
        assert len(vec) == 16
        reasoner = CommonSenseReasoner()
        paths = reasoner.infer("người", max_depth=1)
        relevant = [p.end for p in paths if p.end in tokenize(text)]
        boosted = reasoner.context_boost(paths, context=relevant)
        assert boosted[0].confidence >= paths[0].confidence

    def test_xai_calibrator_closes_the_loop(self):
        calibrator = ConfidenceCalibrator(n_bins=5)
        for score, ok in [(0.9, True), (0.85, True), (0.4, False),
                          (0.35, False)]:
            calibrator.record(score, ok)
        assert calibrator.calibrate(0.9) > calibrator.calibrate(0.4)

    def test_v29_modules_importable_and_versioned(self):
        from quan_ai_brain.ai import neural_symbolic, common_sense, \
            explainable_ai, transfer_learning, multi_agent
        assert neural_symbolic.__version__.startswith("V29.1")
        assert common_sense.__version__.startswith("V29.2")
        assert explainable_ai.__version__.startswith("V29.3")
        assert transfer_learning.__version__.startswith("V29.4")
        assert multi_agent.__version__.startswith("V29.5")
