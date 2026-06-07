#!/usr/bin/env python3
"""
CANYON black-box leaderboard via the **Codex CLI** (ChatGPT-plan models).

Unlike scripts/run_models.py (which hits plain chat-completion APIs through
litellm), this drives each prompt through `codex exec`, i.e. the model wrapped
in the Codex coding-agent persona + tool sandbox. The answers are therefore
NOT 1:1 comparable with the clean chat-completion leaderboard, so results are
written to a SEPARATE file (results/leaderboard_codex.json) and tagged
backend="codex-agent".

Auth comes from the existing `codex login` (ChatGPT). No API keys are read or
written here.

Usage:
  python3 scripts/run_codex.py
  python3 scripts/run_codex.py --models gpt-5.5,o3 --langs en,ru
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from canyon.engine import CanyonEngine

LANGS = ["en", "zh", "ja", "ru", "de", "es"]
RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

# Models confirmed available through the ChatGPT-plan Codex CLI.
CURATED = [
    "gpt-5.5",
    "gpt-5.5-codex",
    "gpt-5.1",
    "gpt-5.1-codex",
    "gpt-5",
    "o3",
    "o4-mini",
]

ERR_PREFIX = "Error during codex"


class CodexRouter:
    """Drop-in replacement for APIRouter that shells out to `codex exec`.

    Mirrors the only method CanyonEngine.run_eval calls: generate(prompt, model).
    On any failure it returns a string starting with ERR_PREFIX so the N/A
    aggregation logic below can treat the language as rate-limited/untrustworthy
    instead of faking a floor score.
    """

    def __init__(self, timeout=180, tools_off=False, codex_home=None):
        self.timeout = timeout
        self.tools_off = tools_off      # strip the shell tool for parity with claude --disallowedTools
        self.codex_home = codex_home    # isolated CODEX_HOME (no plugins/MCP) for a fair tools-off run
        # attributes the engine/CLI may poke at; harmless here
        self.max_tokens = None
        self.temperature = 0.1

    def generate(self, prompt: str, model: str = None) -> str:
        model = model or "gpt-5.5"
        with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as tf:
            out_path = tf.name
        cmd = ["codex", "exec", "-m", model,
               "--sandbox", "read-only", "--skip-git-repo-check",
               "-o", out_path]
        if self.tools_off:
            cmd += ["--disable", "shell_tool"]
        cmd.append(prompt)
        env = dict(os.environ)
        if self.codex_home:
            env["CODEX_HOME"] = self.codex_home
        try:
            proc = subprocess.run(
                cmd, env=env,
                capture_output=True, text=True, timeout=self.timeout,
            )
            with open(out_path, "r", encoding="utf-8") as f:
                answer = f.read().strip()
            if proc.returncode != 0 and not answer:
                tail = (proc.stderr or "").strip().splitlines()[-1:] or [""]
                return f"{ERR_PREFIX}: rc={proc.returncode} {tail[0][:160]}"
            if not answer:
                return f"{ERR_PREFIX}: empty response"
            return answer
        except subprocess.TimeoutExpired:
            return f"{ERR_PREFIX}: timeout after {self.timeout}s"
        except Exception as e:
            return f"{ERR_PREFIX}: {type(e).__name__} {str(e)[:160]}"
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass


def _is_error(text: str) -> bool:
    return text.strip().lower().startswith(ERR_PREFIX.lower())


def run_model(engine, model, langs, delay=0.0):
    per_lang = {}
    valid = []
    err = total = 0
    samples = []
    for li, lang in enumerate(langs):
        if delay and li:
            time.sleep(delay)
        report = engine.run_eval(model=model, use_local=False, lang=lang)
        n_err = sum(1 for r in report["raw_results"] if _is_error(r["output"]))
        total += len(report["raw_results"])
        err += n_err
        if lang == "en":
            samples = [{"test_id": r["test_id"], "prompt": r["prompt"][:80],
                        "output": r["output"][:160]} for r in report["raw_results"]]
        if n_err:
            per_lang[lang] = {"status": "rate_limited", "errored_steps": n_err}
            print(f"    {model:16s} {lang}  N/A ({n_err} errored steps)", flush=True)
        else:
            m = report["metrics"]
            per_lang[lang] = {**m, "classification": report["classification"], "status": "ok"}
            valid.append(lang)
            print(f"    {model:16s} {lang}  SPI={m['stochastic_parrot_index']:.2f} "
                  f"(CP={m['cp_score']:.2f} CR={m['cr_score']:.2f} SI={m['si_score']:.2f})",
                  flush=True)

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
        "backend": "codex-agent",
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
    ap.add_argument("--delay", type=float, default=0.0,
                    help="Seconds to sleep between language evals.")
    ap.add_argument("--model-delay", type=float, default=2.0,
                    help="Seconds to sleep between models.")
    ap.add_argument("--timeout", type=float, default=180.0,
                    help="Per-prompt codex timeout (s).")
    ap.add_argument("--tools-off", action="store_true",
                    help="Strip the shell tool (--disable shell_tool) for parity with claude --disallowedTools.")
    ap.add_argument("--codex-home", default=None,
                    help="Isolated CODEX_HOME (no plugins/MCP) for a fair tools-off run.")
    ap.add_argument("--merge", action="store_true",
                    help="Merge into existing output file instead of overwriting.")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out is None:
        args.out = os.path.join(
            RESULTS_DIR,
            "leaderboard_codex_toolsoff.json" if args.tools_off else "leaderboard_codex.json")

    engine = CanyonEngine(args.config if os.path.exists(args.config) else None)
    engine.api_router = CodexRouter(timeout=args.timeout,
                                    tools_off=args.tools_off,
                                    codex_home=args.codex_home)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]

    existing = {}
    if args.merge and os.path.exists(args.out):
        prev = json.load(open(args.out, encoding="utf-8"))
        existing = {m["model"]: m for m in prev.get("models", [])}

    rows = dict(existing)
    for i, model in enumerate(models):
        if i:
            time.sleep(args.model_delay)
        print(f"[{i+1}/{len(models)}] {model}", flush=True)
        t0 = time.time()
        row = run_model(engine, model, langs, delay=args.delay)
        row["elapsed_s"] = round(time.time() - t0, 1)
        rows[model] = row
        # write incrementally so a crash/interrupt keeps finished models
        ordered = sorted(rows.values(),
                         key=lambda r: r["mean"].get("stochastic_parrot_index", -1),
                         reverse=True)
        out = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "backend": "codex-agent", "langs": langs, "models": ordered}
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\nWrote {args.out} ({len(rows)} models)")


if __name__ == "__main__":
    main()
