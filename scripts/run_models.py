#!/usr/bin/env python3
"""
Multi-model black-box leaderboard for CANYON.

Runs the behavioural suites over a set of API models (default: a curated
text set of Gemini / Gemma models on Google's Generative Language API) across
all six languages, and writes results/leaderboard.json — consumed by
build_report.py for the whitepaper §4.3 table and the docs site.

The API key is read from the environment only (GEMINI_API_KEY / GOOGLE_API_KEY)
and is never written to any file.

Usage:
  export GEMINI_API_KEY=...        # never committed
  python3 scripts/run_models.py
  python3 scripts/run_models.py --models gemini/gemini-2.5-flash,gemini/gemini-2.5-pro
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.engine import CanyonEngine

LANGS = ["en", "zh", "ja", "ru", "de", "es"]
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

CURATED = [
    "gemini/gemini-3.5-flash",
    "gemini/gemini-3-pro-preview",
    "gemini/gemini-3-flash-preview",
    "gemini/gemini-2.5-pro",
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.5-flash-lite",
    "gemini/gemini-2.0-flash",
    "gemini/gemma-4-31b-it",
    "gemini/gemma-4-26b-a4b-it",
]


def _is_error(text):
    return text.strip().lower().startswith("error during litellm")


def run_model(engine, model, langs, delay=0.0):
    per_lang = {}
    valid = []
    err = total = 0
    samples = []
    for li, lang in enumerate(langs):
        if delay and li:
            time.sleep(delay)  # pace to stay under free-tier per-minute limits
        report = engine.run_eval(model=model, use_local=False, lang=lang)
        n_err = sum(1 for r in report["raw_results"] if _is_error(r["output"]))
        total += len(report["raw_results"])
        err += n_err
        if lang == "en":
            samples = [{"test_id": r["test_id"], "prompt": r["prompt"][:80],
                        "output": r["output"][:160]} for r in report["raw_results"]]
        if n_err:
            # Any errored (rate-limited / quota) step makes this language untrustworthy:
            # mark N/A rather than fake a floor score that would pollute the leaderboard.
            per_lang[lang] = {"status": "rate_limited", "errored_steps": n_err}
            print(f"    {model:38s} {lang}  N/A ({n_err} errored steps)")
        else:
            m = report["metrics"]
            per_lang[lang] = {**m, "classification": report["classification"], "status": "ok"}
            valid.append(lang)
            print(f"    {model:38s} {lang}  SPI={m['stochastic_parrot_index']:.2f} "
                  f"(CP={m['cp_score']:.2f} CR={m['cr_score']:.2f} SI={m['si_score']:.2f})")

    keys = ["cp_score", "cr_score", "si_score", "stochastic_parrot_index"]
    if valid:
        mean = {k: round(sum(per_lang[l][k] for l in valid) / len(valid), 3) for k in keys}
        spi = mean["stochastic_parrot_index"]
        cls = ("Strong Grounding (World Model)" if spi >= 0.75
               else "Weak Grounding (Hybrid)" if spi >= 0.5 else "Stochastic Parrot")
    else:
        mean = {}
        cls = "INSUFFICIENT DATA (rate-limited)"
    return {
        "model": model,
        "per_lang": per_lang,
        "mean": mean,
        "valid_langs": valid,
        "classification": cls,
        "error_rate": round(err / total, 3) if total else 1.0,
        "en_samples": samples,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--models", default=",".join(CURATED))
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--delay", type=float, default=6.0,
                    help="Seconds to sleep between language evals (free-tier pacing).")
    ap.add_argument("--model-delay", type=float, default=15.0,
                    help="Seconds to sleep between models.")
    ap.add_argument("--timeout", type=float, default=None,
                    help="Per-request timeout (s) so slow/cold models become N/A instead of hanging.")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="Override max_tokens (reasoning models like DeepSeek V4 need a big budget).")
    ap.add_argument("--merge", action="store_true",
                    help="Merge into existing results/leaderboard.json instead of overwriting.")
    args = ap.parse_args()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print("WARNING: no GEMINI_API_KEY / GOOGLE_API_KEY in environment.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    engine = CanyonEngine(args.config)
    if args.timeout is not None:
        engine.api_router.timeout = args.timeout
    if args.max_tokens is not None:
        engine.api_router.max_tokens = args.max_tokens
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]

    entries = []
    for mi, model in enumerate(models):
        if args.model_delay and mi:
            time.sleep(args.model_delay)
        print(f"[model] {model}", flush=True)
        t0 = time.time()
        try:
            entry = run_model(engine, model, langs, delay=args.delay)
        except Exception as e:
            print(f"    !! {model} failed: {e}")
            entry = {"model": model, "per_lang": {}, "mean": {}, "classification": "ERROR",
                     "error_rate": 1.0, "en_samples": [], "error": str(e)[:300]}
        entry["elapsed_s"] = round(time.time() - t0, 1)
        entries.append(entry)

    lb_path = os.path.join(RESULTS_DIR, "leaderboard.json")
    if args.merge and os.path.exists(lb_path):
        with open(lb_path, encoding="utf-8") as f:
            existing = json.load(f).get("models", [])
        new_ids = {e["model"] for e in entries}
        # keep previously-measured models that we didn't just re-run
        entries = entries + [e for e in existing if e["model"] not in new_ids]
        print(f"Merged with {len(existing)} existing models from leaderboard.json")

    # rank: usable models first (low error rate), then by mean SPI
    entries.sort(key=lambda e: (e.get("error_rate", 1.0) > 0.5,
                                -(e.get("mean", {}).get("stochastic_parrot_index", 0))))

    out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "langs": langs, "models": entries}
    with open(os.path.join(RESULTS_DIR, "leaderboard.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n=== Leaderboard (mean SPI) ===")
    for e in entries:
        spi = e.get("mean", {}).get("stochastic_parrot_index", 0)
        tag = "" if e.get("error_rate", 0) < 0.5 else "  [ERRORS]"
        print(f"  {spi:.3f}  {e['model']}{tag}")
    print(f"\nWrote {os.path.join(RESULTS_DIR, 'leaderboard.json')}")


if __name__ == "__main__":
    main()
