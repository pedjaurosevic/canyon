#!/usr/bin/env python3
"""
CANYON multilingual benchmark runner.

Black-box mode: queries the live llama.cpp endpoint (default the local
gemma-4-12B served on :18083) over all target languages and records the
CP / CR / SI / SPI metrics plus per-test outputs.

White-box mode: loads the local Hugging Face model from config.yaml
(CPU Qwen-0.5B by default) and captures *real* hidden-state activations,
producing genuine cosine-similarity drift trajectories across layers.

Results are written as JSON into results/ and a combined summary.json
that the whitepaper and the GitHub Pages site consume.

Usage:
  python3 scripts/run_benchmark.py --backend black --model openai/gemma-4-12B-it-Q4_K_M.gguf
  python3 scripts/run_benchmark.py --backend white --wl-lang en
  python3 scripts/run_benchmark.py --backend both
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.engine import CanyonEngine
from canyon.metrics import SemanticDriftProbe

LANGS = ["en", "zh", "ja", "ru", "de", "es"]
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))


def _trim_results(raw):
    """Strip the heavy activation arrays before serialising raw outputs."""
    slim = []
    for r in raw:
        slim.append({
            "suite_id": r["suite_id"],
            "lang": r.get("lang"),
            "test_id": r["test_id"],
            "test_name": r["test_name"],
            "step_idx": r["step_idx"],
            "prompt": r["prompt"],
            "output": r["output"],
            "expected": r["expected"],
            "forbidden": r["forbidden"],
        })
    return slim


def _drift_with_ascii(drift_trajectories):
    """Attach an ASCII graph string to each drift trajectory."""
    out = {}
    for test_id, trajs in drift_trajectories.items():
        enriched = []
        for t in trajs:
            enriched.append({
                "from_step": t["from_step"],
                "to_step": t["to_step"],
                "trajectory": t["trajectory"],
                "ascii": SemanticDriftProbe.generate_ascii_graph(t["trajectory"]),
            })
        out[test_id] = enriched
    return out


def run_blackbox(engine, model, langs):
    summary = {}
    for lang in langs:
        print(f"[black-box] {lang} -> {model}")
        t0 = time.time()
        report = engine.run_eval(model=model, use_local=False, lang=lang)
        dt = round(time.time() - t0, 1)
        entry = {
            "lang": lang,
            "backend": "blackbox",
            "model": model,
            "elapsed_s": dt,
            "metrics": report["metrics"],
            "classification": report["classification"],
            "drift_trajectories": _drift_with_ascii(report.get("drift_trajectories", {})),
            "raw_results": _trim_results(report["raw_results"]),
        }
        summary[lang] = entry
        with open(os.path.join(RESULTS_DIR, f"blackbox_{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        m = report["metrics"]
        print(f"    SPI={m['stochastic_parrot_index']:.2f} "
              f"(CP={m['cp_score']:.2f} CR={m['cr_score']:.2f} SI={m['si_score']:.2f}) "
              f"[{report['classification']}] {dt}s")
    return summary


def run_whitebox(engine, langs):
    summary = {}
    for lang in langs:
        print(f"[white-box] {lang} (real activations, this is slow on CPU)...")
        t0 = time.time()
        report = engine.run_eval(use_local=True, lang=lang)
        dt = round(time.time() - t0, 1)
        entry = {
            "lang": lang,
            "backend": "whitebox",
            "model": engine.local_conf.get("model_name_or_path"),
            "elapsed_s": dt,
            "metrics": report["metrics"],
            "classification": report["classification"],
            "drift_trajectories": _drift_with_ascii(report.get("drift_trajectories", {})),
            "raw_results": _trim_results(report["raw_results"]),
        }
        summary[lang] = entry
        with open(os.path.join(RESULTS_DIR, f"whitebox_{lang}.json"), "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        m = report["metrics"]
        print(f"    SPI={m['stochastic_parrot_index']:.2f} "
              f"(CP={m['cp_score']:.2f} CR={m['cr_score']:.2f} SI={m['si_score']:.2f}) {dt}s")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--backend", choices=["black", "white", "both"], default="black")
    ap.add_argument("--model", default="openai/gemma-4-12B-it-Q4_K_M.gguf",
                    help="LiteLLM model id for black-box runs (openai/ prefix routes to local endpoint).")
    ap.add_argument("--langs", default=",".join(LANGS),
                    help="Comma-separated language codes for the black-box sweep.")
    ap.add_argument("--wl-lang", default="en",
                    help="Language(s) for the white-box (real-activation) run, comma-separated.")
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    engine = CanyonEngine(args.config)

    combined = {"blackbox": {}, "whitebox": {}, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    if args.backend in ("black", "both"):
        combined["blackbox"] = run_blackbox(engine, args.model, args.langs.split(","))

    if args.backend in ("white", "both"):
        combined["whitebox"] = run_whitebox(engine, args.wl_lang.split(","))

    with open(os.path.join(RESULTS_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"\nWrote summary.json + per-language files to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
