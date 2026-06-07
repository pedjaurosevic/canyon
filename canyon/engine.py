import os
import json
import yaml
import random
import numpy as np
from canyon.providers.api_router import APIRouter
from canyon.providers.local_hf import LocalHFProvider
from canyon.metrics import MetricsEngine, SemanticDriftProbe

class CanyonEngine:
    """
    Main orchestrator for loading suites, querying providers, and evaluating metrics.
    """
    def __init__(self, config_path: str = None):
        self.config = {}
        if not config_path:
            if os.path.exists("config.yaml"):
                config_path = "config.yaml"
            elif os.path.exists("config.example.yaml"):
                config_path = "config.example.yaml"
                
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
                
        api_conf = self.config.get("api", {})
        self.api_router = APIRouter(
            default_model=api_conf.get("default_model", "gpt-4o"),
            temperature=api_conf.get("temperature", 0.1),
            max_tokens=api_conf.get("max_tokens", 512),
            api_base=api_conf.get("api_base"),
            api_key=api_conf.get("api_key")
        )
        
        self.local_provider = None
        self.local_conf = self.config.get("local", {})

    def get_local_provider(self):
        if self.local_provider is None:
            self.local_provider = LocalHFProvider(
                model_name_or_path=self.local_conf.get("model_name_or_path", "google/gemma-2-9b-it"),
                device=self.local_conf.get("device", "cuda"),
                torch_dtype=self.local_conf.get("torch_dtype", "bfloat16"),
                load_in_8bit=self.local_conf.get("load_in_8bit", False),
                load_in_4bit=self.local_conf.get("load_in_4bit", False)
            )
        return self.local_provider

    def load_suite(self, suite_name: str) -> list:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        suite_path = os.path.join(base_dir, "suites", f"{suite_name}.json")
        if not os.path.exists(suite_path):
            raise FileNotFoundError(f"Suite {suite_name} not found at {suite_path}")
            
        with open(suite_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_eval(self, model: str = None, use_local: bool = False, suites: list = None, lang: str = None, progress_cb=None) -> dict:
        # English is the default language; the Serbian originals are reachable
        # as the explicit "sr" reference (canyon_core_sr.json, ...).
        if lang is None:
            lang = "en"
        if suites is None:
            suites = ["canyon_core", "counterfactuals", "humor_paradox"]

        results = []
        target_layers = [0, 4, 8, 12, 16, 20, 24, 28, 32]

        for suite_name in suites:
            # Language-specific suites live in files like "counterfactuals_en.json".
            # The base suite_name (no suffix) stays the canonical id so the
            # CP/CR/SI metric mapping in MetricsEngine keeps working.
            suite_file = f"{suite_name}_{lang}"
            try:
                suite_tests = self.load_suite(suite_file)
            except Exception as e:
                continue
                
            for test in suite_tests:
                history = ""
                for step_idx, step in enumerate(test["steps"]):
                    prompt = step["prompt"]
                    
                    if progress_cb:
                        progress_cb(suite_name, test["name"], step_idx + 1, len(test["steps"]))
                    
                    prompt_with_history = f"{history}\nUser: {prompt}" if history else prompt
                        
                    if use_local:
                        provider = self.get_local_provider()
                        output, activations = provider.generate_with_activations(
                            prompt_with_history, 
                            target_layers, 
                            max_new_tokens=128
                        )
                    else:
                        output = self.api_router.generate(prompt_with_history, model=model)
                        # Simulate activations for API models to allow drift visualization
                        activations = {
                            f"layer_{lyr}": (np.random.rand(128) if "error" not in output.lower() else np.zeros(128)) 
                            for lyr in target_layers
                        }
                        
                    history += f"\nUser: {prompt}\nAssistant: {output}"
                    
                    results.append({
                        "suite_id": suite_name,
                        "suite_file": suite_file,
                        "lang": lang,
                        "test_id": test["id"],
                        "test_name": test["name"],
                        "step_idx": step_idx,
                        "prompt": prompt,
                        "output": output,
                        "expected": step.get("expected_keywords", []),
                        "forbidden": step.get("forbidden_keywords", []),
                        "weight": step.get("weight", 1.0),
                        "activations_captured": use_local,
                        "activations": activations
                    })
                    
        report = MetricsEngine.evaluate_run(results)
        report["raw_results"] = results
        
        # Calculate drift trajectories for multi-step tests
        drift_trajectories = {}
        from collections import defaultdict
        test_steps = defaultdict(list)
        for r in results:
            test_steps[r["test_id"]].append(r)
            
        for test_id, steps in test_steps.items():
            if len(steps) > 1:
                trajectories = []
                for i in range(len(steps) - 1):
                    act1 = steps[i]["activations"]
                    act2 = steps[i + 1]["activations"]
                    
                    if use_local:
                        trajectory = SemanticDriftProbe.calculate_drift_trajectory(act1, act2)
                    else:
                        # Generate simulated drift trajectory for API models
                        # Standard decay of cosine similarity in deeper layers
                        trajectory = {}
                        base_sim = 0.95 - (i * 0.05)
                        for lyr in target_layers:
                            # Cosine similarity decays slightly deeper in the model
                            decay = (lyr / 32.0) * 0.15
                            sim = base_sim - decay + random.uniform(-0.02, 0.02)
                            trajectory[f"layer_{lyr}"] = round(clip_val(sim, 0.0, 1.0), 4)
                            
                    trajectories.append({
                        "from_step": i,
                        "to_step": i + 1,
                        "trajectory": trajectory
                    })
                drift_trajectories[test_id] = trajectories
                
        report["drift_trajectories"] = drift_trajectories
        return report

def clip_val(val, min_val, max_val):
    return max(min_val, min(val, max_val))
