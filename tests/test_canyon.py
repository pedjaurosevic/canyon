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
        output="Ja sam leteo avionom iznad Velikog kanjona za Čikago.",
        expected=["ja", "avionom"],
        forbidden=["kanjon leti"]
    )
    assert score1 == 1.0  # (1.0 * 0.7) + (1.0 * 0.3)

    # Forbidden word present
    score2 = MetricsEngine.calculate_step_score(
        output="Veliki kanjon leti ka svemiru.",
        expected=["ja"],
        forbidden=["kanjon leti"]
    )
    assert score2 == 0.0  # (0.0 * 0.7) + (0.0 * 0.3)

def test_evaluate_run():
    run_results = [
        {
            "suite_id": "counterfactuals",
            "test_id": "phys-01",
            "step_idx": 0,
            "prompt": "...",
            "output": "Jabuka će poleteti gore prema nebu.",
            "expected": ["gore", "neb"],
            "forbidden": ["pasti na zemlju"],
            "weight": 1.0
        },
        {
            "suite_id": "canyon_core",
            "test_id": "canyon-01",
            "step_idx": 0,
            "prompt": "...",
            "output": "U rečenici 'Gledao sam Veliki kanjon leteći za Čikago', ja letim za Čikago.",
            "expected": ["ja"],
            "forbidden": ["veliki kanjon leti"],
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
