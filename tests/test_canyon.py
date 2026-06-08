import pytest
import os
import sys

# Add path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.metrics import MetricsEngine
from canyon.engine import CanyonEngine

def test_metrics_calculation():
    # Test step score logic
    # Expected words found, forbidden avoided
    score1 = MetricsEngine.calculate_step_score(
        output="I flew by plane over the Grand Canyon to Chicago.",
        expected=["i", "plane"],
        forbidden=["canyon flies"]
    )
    assert score1 == 1.0  # (1.0 * 0.7) + (1.0 * 0.3)

    # Forbidden word present
    score2 = MetricsEngine.calculate_step_score(
        output="The Grand Canyon flies toward space.",
        expected=["i"],
        forbidden=["canyon flies"]
    )
    assert score2 == 0.0  # (0.0 * 0.7) + (0.0 * 0.3)

def test_negated_forbidden_is_ignored():
    # A forbidden phrase that is negated in the same clause must NOT be
    # penalised: "will not fall to the ground" is the correct (grounded) answer.
    score = MetricsEngine.calculate_step_score(
        output="The apple will not fall to the ground; it rises up.",
        expected=["rises", "up"],
        forbidden=["fall to the ground"],
        lang="en",
    )
    assert score == 1.0  # expected hit + forbidden negated → full credit


def test_cross_clause_negation_does_not_leak():
    # The negation ("not") belongs to a *different* clause than the forbidden
    # phrase, so the parrot answer must still be penalised. Expected keyword is
    # absent here to isolate the forbidden-avoidance component (30% weight).
    by_period = MetricsEngine.calculate_step_score(
        output="It will not rise. Instead, it drops to the ground.",
        expected=["levitates"],
        forbidden=["drops to the ground"],
        lang="en",
    )
    by_comma = MetricsEngine.calculate_step_score(
        output="It will not levitate, it drops to the ground.",
        expected=["levitates"],
        forbidden=["drops to the ground"],
        lang="en",
    )
    assert by_period == 0.0  # forbidden present and NOT negated → penalised
    assert by_comma == 0.0


def test_negation_multilingual():
    # Same-clause negation across the language-specific patterns.
    # Spanish pre-verbal negation.
    assert MetricsEngine._is_negated("caerá al suelo", "no caerá al suelo", "es")
    # Japanese suffix negation (落ちず) detected via the after-window.
    assert MetricsEngine._is_negated("落ち", "地面に落ちず、上に上がる", "ja")
    # Plain occurrence with no negation must report False.
    assert not MetricsEngine._is_negated("falls", "the apple falls down", "en")


def test_evaluate_run():
    run_results = [
        {
            "suite_id": "counterfactuals",
            "test_id": "phys-01",
            "step_idx": 0,
            "prompt": "...",
            "output": "The apple will fly up toward the sky.",
            "expected": ["up", "sky"],
            "forbidden": ["fall to the ground"],
            "weight": 1.0
        },
        {
            "suite_id": "canyon_core",
            "test_id": "canyon-01",
            "step_idx": 0,
            "prompt": "...",
            "output": "In the sentence 'I watched the Grand Canyon flying to Chicago', I am flying to Chicago.",
            "expected": ["i"],
            "forbidden": ["the grand canyon is flying"],
            "weight": 1.0
        }
    ]
    
    report = MetricsEngine.evaluate_run(run_results)
    assert "metrics" in report
    assert "classification" in report
    assert report["metrics"]["cp_score"] == 1.0
    assert report["metrics"]["cr_score"] == 1.0

def test_engine_load_suite():
    engine = CanyonEngine()
    suite = engine.load_suite("canyon_core")
    assert len(suite) > 0
    assert suite[0]["id"] == "canyon-01"

def test_engine_lang_suites():
    engine = CanyonEngine()
    # Language-specific suite files load and keep the same canonical test ids
    suite = engine.load_suite("counterfactuals_en")
    assert suite[0]["id"] == "phys-01"
    assert "gravity" in suite[0]["steps"][0]["prompt"].lower()

    # All 6 target languages exist for every base suite
    for base in ["canyon_core", "counterfactuals", "humor_paradox"]:
        for lang in ["en", "zh", "ja", "ru", "de", "es"]:
            s = engine.load_suite(f"{base}_{lang}")
            assert len(s) > 0

def test_semantic_drift_and_graph():
    from canyon.metrics import SemanticDriftProbe
    import numpy as np
    
    # Test cosine similarity
    u = np.array([1.0, 0.0, 0.0])
    v = np.array([1.0, 0.0, 0.0])
    w = np.array([0.0, 1.0, 0.0])
    assert SemanticDriftProbe.cosine_similarity(u, v) == 1.0
    assert SemanticDriftProbe.cosine_similarity(u, w) == 0.0
    
    # Test drift calculation
    act1 = {"layer_0": [1.0, 0.0], "layer_4": [0.0, 1.0]}
    act2 = {"layer_0": [1.0, 0.0], "layer_4": [1.0, 0.0]}
    trajectory = SemanticDriftProbe.calculate_drift_trajectory(act1, act2)
    assert trajectory["layer_0"] == 1.0
    assert trajectory["layer_4"] == 0.0
    
    # Test graph generation
    graph = SemanticDriftProbe.generate_ascii_graph(trajectory)
    assert "Cosine Similarity" in graph
    assert "L0" in graph
    assert "L4" in graph
