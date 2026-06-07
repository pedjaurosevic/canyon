#!/usr/bin/env python3
"""
Assemble the public CANYON dataset under dataset/ from the suites and the
captured runs in results/. Everything here is reproducible from the repo.

Outputs (JSON Lines, UTF-8, HF-datasets friendly):

  dataset/canyon_prompts.jsonl
      The probe bank: every prompt in all 7 languages (en/zh/ja/ru/de/es + the
      Serbian `sr` reference), with its grounded-answer markers and stochastic-
      parrot trap phrases.

  dataset/canyon_conversations.jsonl
      Full transcripts (prompt + complete model response) for every run where we
      logged the whole answer: the local black-box model (gemma-4-12B, 6 langs),
      the white-box model (Qwen2.5-0.5B, 3 langs), and the agent-CLI runs
      (claude -p, codex exec) across all 6 languages. Each turn is scored with
      the exact CANYON keyword screen.

  dataset/canyon_samples_en.jsonl
      English-only preview samples for the chat-API leaderboard models, where we
      retained a truncated answer rather than the full transcript. Clearly
      flagged as partial so nobody mistakes them for full conversations.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from canyon.metrics import MetricsEngine

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "results")
SUITES = os.path.join(ROOT, "canyon", "suites")
OUT = os.path.join(ROOT, "dataset")

AXIS = {"counterfactuals": "CP", "canyon_core": "CR", "humor_paradox": "SI"}
BASES = ["canyon_core", "counterfactuals", "humor_paradox"]
LANGS = ["en", "zh", "ja", "ru", "de", "es", "sr"]


def _suite_lang(fname):
    stem = fname[:-5]  # strip .json
    for base in BASES:
        if stem == base:
            return base, "sr"            # unsuffixed originals are the Serbian reference
        if stem == f"{base}_sr":
            return base, "sr"
        for l in LANGS:
            if stem == f"{base}_{l}":
                return base, l
    return None, None


def build_prompts():
    rows, seen = [], set()
    for path in sorted(glob.glob(os.path.join(SUITES, "*.json"))):
        base, lang = _suite_lang(os.path.basename(path))
        if not base:
            continue
        with open(path, encoding="utf-8") as f:
            tests = json.load(f)
        for t in tests:
            for i, step in enumerate(t["steps"]):
                key = (base, lang, t["id"], i)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "suite": base, "metric_axis": AXIS[base], "lang": lang,
                    "test_id": t["id"], "test_name": t["name"], "step_idx": i,
                    "prompt": step["prompt"],
                    "expected_keywords": step.get("expected_keywords", []),
                    "forbidden_keywords": step.get("forbidden_keywords", []),
                })
    return rows


def _conv_row(model, backend, access_path, lang, r):
    score = MetricsEngine.calculate_step_score(r["output"], r.get("expected", []), r.get("forbidden", []))
    return {
        "model": model, "backend": backend, "access_path": access_path, "lang": lang,
        "suite": r["suite_id"], "metric_axis": AXIS.get(r["suite_id"], "?"),
        "test_id": r["test_id"], "test_name": r["test_name"], "step_idx": r["step_idx"],
        "prompt": r["prompt"], "response": r["output"],
        "expected_keywords": r.get("expected", []), "forbidden_keywords": r.get("forbidden", []),
        "step_score": score,
    }


def build_conversations():
    rows = []
    # local black-box (gemma) + white-box (qwen): full raw_results
    for prefix, access in [("blackbox", "local-blackbox"), ("whitebox", "white-box")]:
        for path in sorted(glob.glob(os.path.join(RESULTS, f"{prefix}_*.json"))):
            d = json.load(open(path, encoding="utf-8"))
            model, lang = d.get("model", "?"), d.get("lang", "?")
            for r in d.get("raw_results", []):
                rows.append(_conv_row(model, prefix, access, lang, r))
    # agent CLIs: full transcripts logged as JSONL
    for fname, access in [("transcripts_claude.jsonl", "claude-agent"),
                          ("transcripts_codex_toolsoff.jsonl", "codex-agent"),
                          ("transcripts_codex.jsonl", "codex-agent"),
                          ("transcripts_chatapi.jsonl", "chat-api")]:
        path = os.path.join(RESULTS, fname)
        if not os.path.exists(path):
            continue
        for line in open(path, encoding="utf-8"):
            t = json.loads(line)
            rows.append(_conv_row(t["model"], t["backend"], access, t["lang"], t))
    return rows


def build_samples_en():
    rows = []
    files = [("leaderboard.json", "chat-api"),
             ("leaderboard_claude.json", "claude-agent"),
             ("leaderboard_codex_toolsoff.json", "codex-agent")]
    for fname, access in files:
        path = os.path.join(RESULTS, fname)
        if not os.path.exists(path):
            continue
        d = json.load(open(path, encoding="utf-8"))
        for m in d.get("models", []):
            for s in m.get("en_samples", []):
                rows.append({
                    "model": m["model"], "access_path": access, "lang": "en",
                    "test_id": s.get("test_id"), "prompt": s.get("prompt"),
                    "response_preview": s.get("output"),
                    "truncated": True,
                    "note": "English preview only; response truncated. See canyon_conversations.jsonl for full transcripts.",
                })
    return rows


def _write(name, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  {name}: {len(rows)} rows")


def main():
    print("Building dataset/ ...")
    prompts = build_prompts()
    _write("canyon_prompts.jsonl", prompts)
    convs = build_conversations()
    _write("canyon_conversations.jsonl", convs)
    samples = build_samples_en()
    _write("canyon_samples_en.jsonl", samples)
    # manifest for the site / datasheet
    models = sorted({(r["access_path"], r["model"]) for r in convs})
    per_path = {}
    for a, _m in models:
        per_path[a] = per_path.get(a, 0) + 1
    manifest = {
        "prompts": len(prompts),
        "conversations": len(convs),
        "samples_en": len(samples),
        "languages": sorted({r["lang"] for r in convs}),
        "prompt_languages": sorted({r["lang"] for r in prompts}),
        "model_runs": [{"access_path": a, "model": m} for a, m in models],
        "runs_per_access_path": per_path,
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"  manifest.json: {len(convs)} conversations across {len(models)} model runs")


if __name__ == "__main__":
    main()
