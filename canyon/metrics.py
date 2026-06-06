import json
import re

class MetricsEngine:
    """
    Engine to calculate semantic grounding metrics (CP, CR, SI scores)
    and the final Stochastic Parrot Index (SPI).
    """
    @staticmethod
    def keyword_in_text(keyword: str, text_lower: str) -> bool:
        """
        Match a keyword inside already-lowercased text.

        Short ASCII keywords (<= 3 chars, e.g. the pronouns "i", "yo", "ich")
        are matched with word boundaries so they do not spuriously fire inside
        unrelated words ("i" inside "nicht", "this", ...). Everything else —
        longer ASCII phrases and all non-ASCII (CJK, Cyrillic) keywords — uses
        plain substring matching, which is the right behaviour for scripts that
        have no whitespace word boundaries.
        """
        kw = keyword.lower()
        if kw.isascii() and len(kw.replace(" ", "")) <= 3 and kw.replace(" ", "").isalpha():
            return re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", text_lower) is not None
        return kw in text_lower

    @staticmethod
    def calculate_step_score(output: str, expected: list, forbidden: list) -> float:
        output_lower = output.lower()

        # 1. Expected keywords match (70% weight).
        # expected_keywords are SYNONYMS of the single correct (grounded) answer,
        # so the concept is considered present if ANY of them is found. This avoids
        # punishing a correct but concise reply (e.g. answering just "I").
        if not expected:
            expected_score = 1.0
        else:
            found_any = any(MetricsEngine.keyword_in_text(kw, output_lower) for kw in expected)
            expected_score = 1.0 if found_any else 0.0

        # 2. Forbidden keywords avoidance (30% weight)
        if not forbidden:
            forbidden_score = 1.0
        else:
            found_forbidden = any(MetricsEngine.keyword_in_text(kw, output_lower) for kw in forbidden)
            forbidden_score = 0.0 if found_forbidden else 1.0

        return round((expected_score * 0.7) + (forbidden_score * 0.3), 2)

    @staticmethod
    def evaluate_run(run_results: list) -> dict:
        """
        Calculates scores based on test suite execution results.
        """
        scores_by_suite = {}
        
        for res in run_results:
            suite_id = res["suite_id"]
            step_score = MetricsEngine.calculate_step_score(
                res["output"], 
                res["expected"], 
                res["forbidden"]
            )
            
            if suite_id not in scores_by_suite:
                scores_by_suite[suite_id] = []
            
            scores_by_suite[suite_id].append(step_score * res.get("weight", 1.0))
            
        # CP-Score (Counterfactual Plasticity) -> 'counterfactuals' suite
        cp_scores = scores_by_suite.get("counterfactuals", [])
        cp_score = sum(cp_scores) / len(cp_scores) if cp_scores else 0.0
        
        # CR-Score (Contextual Realignment) -> 'canyon_core' suite
        cr_scores = scores_by_suite.get("canyon_core", [])
        cr_score = sum(cr_scores) / len(cr_scores) if cr_scores else 0.0
        
        # SI-Score (Semantic Invariance) -> 'humor_paradox' suite
        si_scores = scores_by_suite.get("humor_paradox", [])
        si_score = sum(si_scores) / len(si_scores) if si_scores else 0.0
        
        # Stochastic Parrot Index (SPI) is a weighted metric:
        # Higher index -> Better Semantic Grounding
        # Lower index -> High probability of Stochastic Parroting
        spi = round((cp_score * 0.4) + (cr_score * 0.4) + (si_score * 0.2), 2)
        
        classification = "Stochastic Parrot"
        if spi >= 0.75:
            classification = "Strong Grounding (World Model)"
        elif spi >= 0.5:
            classification = "Weak Grounding (Hybrid)"
            
        return {
            "metrics": {
                "cp_score": round(cp_score, 2),
                "cr_score": round(cr_score, 2),
                "si_score": round(si_score, 2),
                "stochastic_parrot_index": spi
            },
            "classification": classification
        }

import numpy as np

class SemanticDriftProbe:
    """
    Computes geometric distances (Cosine Similarity) in latent space 
    between activation vectors across decoder layers.
    """
    @staticmethod
    def cosine_similarity(u: np.ndarray, v: np.ndarray) -> float:
        dot_product = np.dot(u, v)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        
        if norm_u == 0.0 or norm_v == 0.0:
            return 0.0
            
        return float(dot_product / (norm_u * norm_v))

    @staticmethod
    def calculate_drift_trajectory(activations_step1: dict, activations_step2: dict) -> dict:
        """
        Calculates cosine similarity trajectory across all logged layers.
        """
        trajectory = {}
        for layer, vec1 in activations_step1.items():
            if layer in activations_step2:
                v1 = np.array(vec1).flatten()
                v2 = np.array(activations_step2[layer]).flatten()
                
                similarity = SemanticDriftProbe.cosine_similarity(v1, v2)
                trajectory[layer] = round(similarity, 4)
                
        return trajectory

    @staticmethod
    def generate_ascii_graph(trajectory: dict) -> str:
        """
        Generates an ASCII graph of cosine similarity trajectory across model layers.
        """
        if not trajectory:
            return "No drift data available."
            
        # Parse layers and similarities
        sorted_points = []
        for k, v in trajectory.items():
            try:
                layer_num = int(k.split("_")[1])
                sorted_points.append((layer_num, v))
            except Exception:
                pass
        
        sorted_points.sort(key=lambda x: x[0])
        if not sorted_points:
            return "No valid layer data for drift."
            
        layers, similarities = zip(*sorted_points)
        
        # Grid dimensions
        width = len(layers)
        height = 6 # number of rows in graph
        
        min_s = min(similarities)
        max_s = max(similarities)
        
        # Adjust min and max for prettier look
        if min_s == max_s:
            min_val = max(0.0, min_s - 0.1)
            max_val = min(1.0, max_s + 0.1)
        else:
            span = max_s - min_s
            min_val = max(0.0, min_s - span * 0.1)
            max_val = min(1.0, max_s + span * 0.1)
            
        # Generate grid of spaces
        grid = [[" " for _ in range(width)] for _ in range(height)]
        
        # Plot points
        for col_idx, sim in enumerate(similarities):
            # Map sim to row index [0, height-1]
            if max_val == min_val:
                row_idx = height // 2
            else:
                row_idx = int(round((sim - min_val) / (max_val - min_val) * (height - 1)))
            row_idx = max(0, min(height - 1, row_idx))
            # Invert row index because grid row 0 is top
            grid[height - 1 - row_idx][col_idx] = "●"
            
        # Build output string
        lines = []
        lines.append("   Cosine Similarity")
        for r in range(height):
            # Y-axis label
            val = max_val - r * ((max_val - min_val) / (height - 1)) if height > 1 else max_val
            label = f"   {val:5.2f} | "
            row_chars = "".join(grid[r][c] + "   " for c in range(width))
            lines.append(label + row_chars)
            
        # X-axis
        lines.append("          +" + "-" * (width * 4))
        # X-axis labels (Layer numbers)
        x_labels = "           " + "".join(f"L{l:<3}" for l in layers)
        lines.append(x_labels)
        
        return "\n".join(lines)

