#!/usr/bin/env python3
"""
CANYON black-box leaderboard via **GitHub Models** (https://models.github.ai).

These are plain chat-completion calls (no agent wrapper), so results are tagged
backend="chat-api" and merge straight into results/leaderboard.json — they fill
gaps the NVIDIA NIM / DeepSeek runs could not reach (OpenAI gpt-4o/gpt-4.1/gpt-5,
o-series, Microsoft Phi-4, Cohere, DeepSeek-R1, Llama-3.1-405B, ...).

Auth: a GitHub token with the **Models: read-only** permission, from
$GITHUB_MODELS_TOKEN or $GITHUB_API_KEY (the gh-CLI OAuth token usually lacks the
models permission and returns 401). The token is read from the environment only
and never written anywhere.

Usage:
  export GITHUB_MODELS_TOKEN=...        # fine-grained PAT, Models: read-only
  python3 scripts/run_github.py --merge
  python3 scripts/run_github.py --models openai/gpt-4o-mini,microsoft/phi-4 --langs en,ru
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from canyon.engine import CanyonEngine

LANGS = ["en", "zh", "ja", "ru", "de", "es"]
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))
ENDPOINT = "https://models.github.ai/inference/chat/completions"
ERR_PREFIX = "Error during github-models"

# Gap-fillers: models we did not already have via NVIDIA NIM / DeepSeek / agents.
CURATED = [
    "openai/gpt-4o", "openai/gpt-4o-mini",
    "openai/gpt-4.1", "openai/gpt-4.1-mini",
    "openai/gpt-5-mini", "openai/gpt-5-chat",
    "openai/o3-mini", "openai/o1-mini",
    "microsoft/phi-4", "microsoft/phi-4-reasoning",
    "cohere/cohere-command-a",
    "mistral-ai/mistral-medium-2505",
    "deepseek/deepseek-v3-0324", "deepseek/deepseek-r1-0528",
    "meta/meta-llama-3.1-405b-instruct",
]


def _token():
    return (os.environ.get("GITHUB_MODELS_TOKEN") or os.environ.get("GITHUB_API_KEY")
            or os.environ.get("GH_MODELS_TOKEN") or "")


class GithubRouter:
    """Drop-in for APIRouter: POSTs to the GitHub Models inference endpoint."""

    def __init__(self, timeout=120, max_tokens=512, temperature=0.1):
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.token = _token()

    def generate(self, prompt: str, model: str = None) -> str:
        if not self.token:
            return f"{ERR_PREFIX}: no token (set GITHUB_MODELS_TOKEN)"
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                d = json.loads(r.read().decode("utf-8"))
            ch = d.get("choices", [{}])[0].get("message", {})
            text = (ch.get("content") or "").strip()
            # some reasoning models put the answer in a separate field
            if not text and ch.get("reasoning_content"):
                text = ch["reasoning_content"].strip()
            return text or f"{ERR_PREFIX}: empty response"
        except urllib.error.HTTPError as e:
            return f"{ERR_PREFIX}: HTTP {e.code} {e.reason}"
        except Exception as e:
            return f"{ERR_PREFIX}: {type(e).__name__} {str(e)[:120]}"


def _is_error(text: str) -> bool:
    return text.strip().lower().startswith(ERR_PREFIX.lower())


def run_model(engine, model, langs, delay=0.0, transcripts=None):
    per_lang, valid, samples = {}, [], []
    err = total = 0
    for li, lang in enumerate(langs):
        if delay and li:
            time.sleep(delay)
        report = engine.run_eval(model=model, use_local=False, lang=lang)
        if transcripts is not None:
            for r in report["raw_results"]:
                if _is_error(r["output"]):
                    continue
                transcripts.append({"model": model, "backend": "chat-api", "lang": lang,
                                    "suite_id": r["suite_id"], "test_id": r["test_id"],
                                    "test_name": r["test_name"], "step_idx": r["step_idx"],
                                    "prompt": r["prompt"], "output": r["output"],
                                    "expected": r["expected"], "forbidden": r["forbidden"]})
        n_err = sum(1 for r in report["raw_results"] if _is_error(r["output"]))
        total += len(report["raw_results"]); err += n_err
        if lang == "en":
            samples = [{"test_id": r["test_id"], "prompt": r["prompt"][:80],
                        "output": r["output"][:160]} for r in report["raw_results"]]
        if n_err:
            per_lang[lang] = {"status": "rate_limited", "errored_steps": n_err}
            print(f"    {model:42s} {lang}  N/A ({n_err} errored)", flush=True)
        else:
            m = report["metrics"]
            per_lang[lang] = {**m, "classification": report["classification"], "status": "ok"}
            valid.append(lang)
            print(f"    {model:42s} {lang}  SPI={m['stochastic_parrot_index']:.2f}", flush=True)

    keys = ["cp_score", "cr_score", "si_score", "stochastic_parrot_index"]
    if valid:
        mean = {k: round(sum(per_lang[l][k] for l in valid) / len(valid), 3) for k in keys}
        spi = mean["stochastic_parrot_index"]
        cls = ("Strong Grounding (World Model)" if spi >= 0.75
               else "Weak Grounding (Hybrid)" if spi >= 0.5 else "Stochastic Parrot")
    else:
        mean, cls = {}, "INSUFFICIENT DATA (rate-limited)"
    return {"model": model, "per_lang": per_lang, "mean": mean, "valid_langs": valid,
            "classification": cls, "error_rate": round(err / total, 3) if total else 1.0,
            "en_samples": samples}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--models", default=",".join(CURATED))
    ap.add_argument("--langs", default=",".join(LANGS))
    ap.add_argument("--delay", type=float, default=3.0, help="Sleep between languages (free-tier pacing).")
    ap.add_argument("--model-delay", type=float, default=8.0)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--merge", action="store_true", help="Merge into results/leaderboard.json.")
    ap.add_argument("--out", default=os.path.join(RESULTS_DIR, "leaderboard.json"))
    args = ap.parse_args()

    if not _token():
        print("ERROR: set GITHUB_MODELS_TOKEN (a fine-grained PAT with Models: read-only).")
        sys.exit(1)

    engine = CanyonEngine(args.config if os.path.exists(args.config) else None)
    engine.api_router = GithubRouter(timeout=args.timeout, max_tokens=args.max_tokens)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]

    existing = {}
    if args.merge and os.path.exists(args.out):
        prev = json.load(open(args.out, encoding="utf-8"))
        existing = {m["model"]: m for m in prev.get("models", [])}

    transcripts = []
    rows = dict(existing)
    for i, model in enumerate(models):
        if i:
            time.sleep(args.model_delay)
        print(f"[{i+1}/{len(models)}] {model}", flush=True)
        t0 = time.time()
        row = run_model(engine, model, langs, delay=args.delay, transcripts=transcripts)
        row["elapsed_s"] = round(time.time() - t0, 1)
        rows[model] = row
        ordered = sorted(rows.values(),
                         key=lambda r: r.get("mean", {}).get("stochastic_parrot_index", -1),
                         reverse=True)
        out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "langs": langs, "models": ordered}
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)

    tpath = os.path.join(RESULTS_DIR, "transcripts_github.jsonl")
    merged, ran = [], set(models)
    if os.path.exists(tpath):
        for line in open(tpath, encoding="utf-8"):
            old = json.loads(line)
            if old.get("model") not in ran:
                merged.append(old)
    merged.extend(transcripts)
    with open(tpath, "w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {args.out} + {tpath} ({len(merged)} turns, {len(transcripts)} new)")


if __name__ == "__main__":
    main()
