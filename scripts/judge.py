#!/usr/bin/env python3
"""
LLM-judge re-scoring for CANYON.

The default keyword screen is brittle: it marks a correct paraphrase wrong (e.g.
"the apple won't stop, it keeps going up into the sky" misses the literal
keywords space/never/atmosphere). This re-scores every SAVED conversation turn
with a semantic judge — no models are re-called, we only re-grade stored answers.

Judge = OpenAI gpt-5.5 via the Codex CLI (neutral to the local gemma model that
tops the keyword leaderboard). Turns are judged in batches for speed. Each turn
gets grounded=true/false; we re-aggregate into CP/CR/SI/SPI exactly like the
keyword metric, and write results/leaderboard_judged.json + results/judged_turns.jsonl.

Usage:
  python3 scripts/judge.py
  python3 scripts/judge.py --batch 8 --model gpt-5.5
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(ROOT, "results")
CONV = os.path.join(ROOT, "dataset", "canyon_conversations.jsonl")
AXIS = {"counterfactuals": "CP", "canyon_core": "CR", "humor_paradox": "SI"}

JUDGE_INSTRUCTIONS = (
    "You are a STRICT, fair grader for a grounding benchmark. Each item gives a "
    "QUESTION that hides a statistically common but situationally WRONG answer "
    "(the trap), and a GROUNDED correct answer. You read the MODEL RESPONSE and "
    "decide a single boolean: does the response commit to the GROUNDED/correct "
    "meaning (accept paraphrases and synonyms; ignore verbosity and language) "
    "WITHOUT asserting the trap? Be semantic, not keyword-based: "
    "'it won't stop, it keeps rising into the sky' is grounded even if it never "
    "says the word 'space'. Return ONLY a JSON array, one object per item, "
    'in order: [{"i":0,"grounded":true},{"i":1,"grounded":false},...]. No prose.'
)


def codex_call(prompt, model, codex_home, timeout=120):
    with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as tf:
        out = tf.name
    cmd = ["codex", "exec", "-m", model, "--disable", "shell_tool",
           "--sandbox", "read-only", "--skip-git-repo-check", "-o", out, prompt]
    env = dict(os.environ)
    if codex_home:
        env["CODEX_HOME"] = codex_home
    try:
        subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
        with open(out, encoding="utf-8") as f:
            return f.read().strip()
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def _extract_json(text):
    a, b = text.find("["), text.rfind("]")
    if a == -1 or b == -1:
        return None
    try:
        return json.loads(text[a:b + 1])
    except Exception:
        return None


def build_item(t, i):
    return (f'ITEM {i}\n'
            f'QUESTION: {t["prompt"]}\n'
            f'GROUNDED answer is about: {", ".join(t.get("expected_keywords", [])) or "the correct reading"}\n'
            f'TRAP (wrong) answer: {", ".join(t.get("forbidden_keywords", [])) or "the obvious-but-wrong reading"}\n'
            f'MODEL RESPONSE: {t["response"][:700]}\n')


def judge_batch(turns, model, codex_home):
    body = JUDGE_INSTRUCTIONS + "\n\n" + "\n".join(build_item(t, i) for i, t in enumerate(turns))
    raw = codex_call(body, model, codex_home)
    arr = _extract_json(raw)
    verdict = {}
    if isinstance(arr, list):
        for o in arr:
            if isinstance(o, dict) and "i" in o and "grounded" in o:
                verdict[int(o["i"])] = 1.0 if o["grounded"] else 0.0
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--model", default="gpt-5.5")
    ap.add_argument("--codex-home", default="/tmp/codex_clean")
    ap.add_argument("--reuse-existing", action="store_true",
                    help="Reuse results/judged_turns.jsonl entries and judge only missing turns.")
    args = ap.parse_args()

    turns = [json.loads(l) for l in open(CONV, encoding="utf-8")]
    key_fields = ("model", "access_path", "lang", "suite", "test_id", "step_idx")
    existing = {}
    judged_path = os.path.join(RESULTS, "judged_turns.jsonl")
    if args.reuse_existing and os.path.exists(judged_path):
        for line in open(judged_path, encoding="utf-8"):
            row = json.loads(line)
            existing[tuple(row.get(k) for k in key_fields)] = row.get("grounded", 0.0)

    print(f"Judging {len(turns)} saved turns with {args.model} (batch {args.batch})...", flush=True)
    if existing:
        print(f"  reusing {len(existing)} existing judgments", flush=True)

    scored = []
    pending = []
    for t in turns:
        key = tuple(t.get(k) for k in key_fields)
        if key in existing:
            t2 = dict(t)
            t2["grounded"] = existing[key]
            scored.append(t2)
        else:
            pending.append(t)

    for start in range(0, len(pending), args.batch):
        batch = pending[start:start + args.batch]
        v = judge_batch(batch, args.model, args.codex_home)
        if len(v) < len(batch):  # retry per-item on misalignment / bad JSON
            for j, t in enumerate(batch):
                if j not in v:
                    v[j] = judge_batch([t], args.model, args.codex_home).get(0, 0.0)
        for j, t in enumerate(batch):
            t2 = dict(t)
            t2["grounded"] = v.get(j, 0.0)
            scored.append(t2)
        print(f"  {len(scored)}/{len(turns)}", flush=True)

    # persist per-turn judgments
    with open(os.path.join(RESULTS, "judged_turns.jsonl"), "w", encoding="utf-8") as f:
        for t in scored:
            f.write(json.dumps({k: t[k] for k in ("model", "access_path", "lang", "suite",
                    "test_id", "step_idx", "grounded")}, ensure_ascii=False) + "\n")

    # aggregate: per (model, access_path) -> per suite mean -> CP/CR/SI/SPI per lang, then mean
    from collections import defaultdict
    by = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # (model,access)->lang->suite->[grounded]
    for t in scored:
        by[(t["model"], t["access_path"])][t["lang"]][t["suite"]].append(t["grounded"])

    models = []
    langs_seen = set()
    for (model, access), per_lang_data in by.items():
        per_lang = {}
        for lang, suites in per_lang_data.items():
            langs_seen.add(lang)
            cp = suites.get("counterfactuals"); cr = suites.get("canyon_core"); si = suites.get("humor_paradox")
            def m(x): return round(sum(x) / len(x), 2) if x else None
            cps, crs, sis = m(cp), m(cr), m(si)
            if None in (cps, crs, sis):
                continue
            spi = round(0.4 * cps + 0.4 * crs + 0.2 * sis, 3)
            per_lang[lang] = {"cp_score": cps, "cr_score": crs, "si_score": sis,
                              "stochastic_parrot_index": spi}
        if not per_lang:
            continue
        keys = ["cp_score", "cr_score", "si_score", "stochastic_parrot_index"]
        mean = {k: round(sum(per_lang[l][k] for l in per_lang) / len(per_lang), 3) for k in keys}
        spi = mean["stochastic_parrot_index"]
        cls = ("Strong Grounding (World Model)" if spi >= 0.75
               else "Weak Grounding (Hybrid)" if spi >= 0.5 else "Stochastic Parrot")
        models.append({"model": model, "access_path": access, "per_lang": per_lang,
                       "mean": mean, "classification": cls})

    models.sort(key=lambda x: x["mean"]["stochastic_parrot_index"], reverse=True)
    order = ["en", "zh", "ja", "ru", "de", "es"]
    langs = [l for l in order if l in langs_seen] + [l for l in langs_seen if l not in order]
    out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "judge": args.model,
           "langs": langs, "models": models}
    with open(os.path.join(RESULTS, "leaderboard_judged.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nJudged ranking:")
    for i, m in enumerate(models, 1):
        print(f"  {i:2}. {m['mean']['stochastic_parrot_index']:.3f}  [{m['access_path']}]  {m['model'].split('/')[-1]}")


if __name__ == "__main__":
    main()
