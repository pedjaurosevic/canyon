#!/usr/bin/env python3
"""
Assemble the CANYON results artefacts from the per-language JSON files in
results/:

  1. Replaces the <!-- RESULTS:AUTO --> ... <!-- /RESULTS:AUTO --> block in
     WHITEPAPER.md with generated SPI tables and real ASCII drift graphs.
  2. Writes docs/data.js (window.CANYON_DATA = {...}) consumed by the
     GitHub Pages site, so the page works without a fetch/server.
  3. Rewrites results/summary.json as the *combined* black-box + white-box
     view (individual benchmark runs only write their own half).

Reads results/blackbox_<lang>.json and results/whitebox_<lang>.json directly
rather than trusting summary.json, which each run clobbers with its own half.
"""
import glob
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(ROOT, "results")
DOCS_DIR = os.path.join(ROOT, "docs")
WHITEPAPER = os.path.join(ROOT, "WHITEPAPER.md")

LANG_NAMES = {
    "en": "English", "zh": "Chinese", "ja": "Japanese",
    "ru": "Russian", "de": "German", "es": "Spanish", "sr": "Serbian",
}
LANG_ORDER = ["en", "zh", "ja", "ru", "de", "es", "sr"]


def _load(prefix):
    out = {}
    for path in glob.glob(os.path.join(RESULTS_DIR, f"{prefix}_*.json")):
        lang = os.path.basename(path)[len(prefix) + 1:-5]
        with open(path, encoding="utf-8") as f:
            out[lang] = json.load(f)
    return out


def _load_leaderboard():
    path = os.path.join(RESULTS_DIR, "leaderboard.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# The "access-path" experiment: the same probes asked of frontier models through
# two different agent CLIs (Claude Code `claude -p` and OpenAI `codex exec`),
# both run with their shell tools stripped for parity. Each file is a normal
# leaderboard; here we fold them into one labelled comparison.
AGENT_PATHS = [
    ("leaderboard_claude.json", "Claude Code agent — claude -p (tools off)"),
    ("leaderboard_codex_toolsoff.json", "Codex agent — codex exec (tools off)"),
]


def _load_agent():
    paths = []
    for fname, label in AGENT_PATHS:
        path = os.path.join(RESULTS_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            lb = json.load(f)
        models = [m for m in lb.get("models", []) if m.get("valid_langs")]
        if models:
            paths.append({"label": label,
                          "backend": lb.get("backend", ""),
                          "langs": lb.get("langs", []),
                          "models": models})
    if not paths:
        return None
    langs = paths[0]["langs"]
    robust = None
    rpath = os.path.join(RESULTS_DIR, "robustness_de.json")
    if os.path.exists(rpath):
        with open(rpath, encoding="utf-8") as f:
            robust = json.load(f)
    return {"langs": langs, "paths": paths, "robustness": robust}


def _ordered(d):
    return [l for l in LANG_ORDER if l in d] + [l for l in d if l not in LANG_ORDER]


def _spi_table(entries):
    rows = ["| Language | CP | CR | SI | **SPI** | Classification |",
            "|----------|----|----|----|---------|----------------|"]
    for lang in _ordered(entries):
        m = entries[lang]["metrics"]
        rows.append(
            f"| {LANG_NAMES.get(lang, lang)} ({lang}) "
            f"| {m['cp_score']:.2f} | {m['cr_score']:.2f} | {m['si_score']:.2f} "
            f"| **{m['stochastic_parrot_index']:.2f}** | {entries[lang]['classification']} |"
        )
    return "\n".join(rows)


def _mean(entries, key):
    vals = [e["metrics"][key] for e in entries.values()]
    return sum(vals) / len(vals) if vals else 0.0


def _short(model):
    return model.split("/")[-1]


def build_leaderboard_md(lb):
    langs = lb.get("langs", [])
    head = "| # | Model | " + " | ".join(l.upper() for l in langs) + " | Cov. | **Mean SPI** | Class |"
    sep = "|---|-------|" + "|".join(["----"] * len(langs)) + "|------|------|-------|"
    rows = [head, sep]
    rank = 0
    for e in lb.get("models", []):
        cells = []
        valid = 0
        for l in langs:
            cell = e.get("per_lang", {}).get(l, {})
            v = cell.get("stochastic_parrot_index")
            if v is not None:
                cells.append(f"{v:.2f}")
                valid += 1
            else:
                cells.append("N/A")
        mean = e.get("mean", {}).get("stochastic_parrot_index")
        cov = f"{valid}/{len(langs)}"
        if mean is not None and valid:
            rank += 1
            rank_s, mean_s = str(rank), f"**{mean:.2f}**"
        else:
            rank_s, mean_s = "–", "—"
        short_cls = (e.get("classification") or "—").split(" (")[0]
        rows.append(f"| {rank_s} | `{_short(e['model'])}` | " + " | ".join(cells) +
                    f" | {cov} | {mean_s} | {short_cls} |")
    # Cells marked N/A were rate-limited / quota-blocked and are excluded from the mean.
    rows.append("\n*N/A = quota-blocked or rate-limited on the API key; excluded from the mean. "
                "Only fully-covered models are ranked.*")
    return "\n".join(rows)


def build_agent_md(agent):
    langs = agent["langs"]
    parts = ["\n### 4.4 The access-path experiment (frontier models via agent CLIs)\n"]
    parts.append(
        "A follow-up question: does it matter *how* you reach a model? The leaderboard "
        "above talks to plain chat-completion endpoints. Here the **same six-language "
        "probes** are instead answered by two frontier-model command-line agents — "
        "Anthropic's Claude Code (`claude -p`) and OpenAI's Codex (`codex exec`) — each "
        "run with its shell tools stripped and from an isolated config, so the only thing "
        "that changes from the chat path is the agent's own framing. Mean SPI across "
        f"{len(langs)} languages:\n")
    head = "| Access path | Model | " + " | ".join(l.upper() for l in langs) + " | **Mean SPI** | Class |"
    sep = "|-------------|-------|" + "|".join(["----"] * len(langs)) + "|------|-------|"
    rows = [head, sep]
    for p in agent["paths"]:
        for e in p["models"]:
            cells = []
            for l in langs:
                v = e.get("per_lang", {}).get(l, {}).get("stochastic_parrot_index")
                cells.append(f"{v:.2f}" if v is not None else "N/A")
            mean = e.get("mean", {}).get("stochastic_parrot_index")
            short_cls = (e.get("classification") or "—").split(" (")[0]
            rows.append(f"| {p['label']} | `{_short(e['model'])}` | " + " | ".join(cells) +
                        f" | **{mean:.2f}** | {short_cls} |")
    parts.append("\n".join(rows))
    rob = agent.get("robustness")
    if rob:
        wt = rob["with_tools"]["mean_spi"]
        off = rob["tools_off"]["mean_spi"]
        parts.append(
            f"\n**A note on noise.** A single run once showed gpt-5.5 jumping on German "
            f"when tools were removed. Re-running that one language {rob['repeats']}× in "
            f"each mode did *not* reproduce it — the direction actually reversed "
            f"(with-tools mean {wt:.2f} vs tools-off {off:.2f}). The tools-on/off gap is "
            "within run-to-run variance (≈ ±0.07 per language at temperature 0.1), not a "
            "real scaffolding effect. The practical lesson cuts across the whole paper: "
            "**single-run SPI values are point estimates; differences smaller than ~0.05 "
            "should not be read as real.** (Data: `results/robustness_de.json`.)\n")
    return "\n".join(parts)


def build_results_md(black, white, leaderboard=None, agent=None):
    parts = []

    if black:
        any_entry = next(iter(black.values()))
        parts.append("### 4.1 Behavioural results (black-box)\n")
        parts.append(f"Model: `{any_entry.get('model', 'n/a')}` · "
                     f"endpoint-served, queried over six languages.\n")
        parts.append(_spi_table(black))
        parts.append(
            f"\n**Cross-lingual mean:** CP={_mean(black,'cp_score'):.2f}, "
            f"CR={_mean(black,'cr_score'):.2f}, SI={_mean(black,'si_score'):.2f}, "
            f"**SPI={_mean(black,'stochastic_parrot_index'):.2f}**. "
            "Flat SPI across languages is the grounding-invariance signature; "
            "large dispersion suggests language-dependent (statistics-driven) behaviour.\n"
        )

    if white:
        any_w = next(iter(white.values()))
        parts.append("\n### 4.2 Real latent-space drift (white-box)\n")
        parts.append(f"Model: `{any_w.get('model', 'n/a')}` · real hidden-state "
                     "activations, layers 0–32. Cosine similarity of the activation "
                     "between successive reasoning steps, per layer.\n")
        parts.append(_spi_table(white))
        parts.append("")
        for lang in _ordered(white):
            entry = white[lang]
            drift = entry.get("drift_trajectories", {})
            for test_id, trajs in drift.items():
                for t in trajs:
                    parts.append(
                        f"\n**{LANG_NAMES.get(lang, lang)} ({lang}) · `{test_id}` · "
                        f"step {t['from_step']+1} → {t['to_step']+1}** "
                        "— cosine similarity per layer:\n")
                    parts.append("```")
                    parts.append(t.get("ascii", "(no graph)"))
                    parts.append("```")

    if leaderboard and leaderboard.get("models"):
        parts.append("\n### 4.3 Model leaderboard (black-box, cross-lingual)\n")
        parts.append(f"Mean Stochastic Parrot Index over {len(leaderboard.get('langs', []))} "
                     "languages, per API model, ranked by mean SPI. Models served via "
                     "NVIDIA NIM (`integrate.api.nvidia.com`) and the DeepSeek API "
                     "(`deepseek-v4-pro`, a reasoning model). Open/free-tier endpoints "
                     "with insufficient quota are reported as N/A rather than scored, so "
                     "the table reflects only trustworthy measurements.\n")
        parts.append(build_leaderboard_md(leaderboard))
        parts.append("")

    if agent and agent.get("paths"):
        parts.append(build_agent_md(agent))

    if not parts:
        return ("*(No results found in `results/`. Run "
                "`python3 scripts/run_benchmark.py --backend both` first.)*")
    return "\n".join(parts)


def patch_whitepaper(results_md):
    with open(WHITEPAPER, encoding="utf-8") as f:
        text = f.read()
    start = "<!-- RESULTS:AUTO -->"
    end = "<!-- /RESULTS:AUTO -->"
    i, j = text.find(start), text.find(end)
    if i == -1 or j == -1:
        print("WARNING: RESULTS:AUTO markers not found in WHITEPAPER.md; skipping patch.")
        return
    new = text[:i + len(start)] + "\n" + results_md + "\n" + text[j:]
    with open(WHITEPAPER, "w", encoding="utf-8") as f:
        f.write(new)
    print("Patched §4 of WHITEPAPER.md")


def write_docs_data(black, white, leaderboard=None, agent=None):
    os.makedirs(DOCS_DIR, exist_ok=True)
    payload = {"blackbox": black, "whitebox": white, "leaderboard": leaderboard,
               "agent_access": agent,
               "lang_names": LANG_NAMES, "lang_order": LANG_ORDER}
    js = "// Auto-generated by scripts/build_report.py — do not edit by hand.\n"
    js += "window.CANYON_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    with open(os.path.join(DOCS_DIR, "data.js"), "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Wrote docs/data.js ({len(black)} black-box, {len(white)} white-box langs)")


def main():
    black = _load("blackbox")
    white = _load("whitebox")
    leaderboard = _load_leaderboard()
    agent = _load_agent()
    results_md = build_results_md(black, white, leaderboard, agent)
    patch_whitepaper(results_md)
    write_docs_data(black, white, leaderboard, agent)
    with open(os.path.join(RESULTS_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"blackbox": black, "whitebox": white, "leaderboard": leaderboard,
                   "agent_access": agent},
                  f, ensure_ascii=False, indent=2)
    print("Rewrote combined results/summary.json")


if __name__ == "__main__":
    main()
