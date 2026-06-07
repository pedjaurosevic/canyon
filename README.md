# CANYON 🏜️
### A framework for mechanistic and behavioural evaluation of semantic grounding in LLMs

`CANYON` is an open-source research harness and benchmark designed to test Geoffrey Hinton's hypothesis about functional understanding and internal world models in large language models (LLMs). Named after Hinton's well-known Grand Canyon example, the tool aims to distinguish mere statistical word-stitching ("stochastic parrot") from dynamic *semantic grounding*.

---

## 🧭 What we're trying to find out

There is a simple, unresolved question about large language models: **do they actually understand anything, or do they just predict likely words?**

- One camp — the *"stochastic parrot"* view — says a model is just an enormous table of which words tend to follow which. Any appearance of meaning is an illusion.
- The other camp — Geoffrey Hinton's *grounding* view — says that to predict the next word *well enough*, a model is forced to learn the structure behind the words: objects, causes, intentions. In other words, a small **model of the world** hides inside the word-predictor.

CANYON doesn't try to win that debate philosophically. It does something smaller and concrete: it asks models **trick questions where the statistically obvious answer is wrong**, and watches whether they fall for the trap or override it.

The idea: a parrot repeats the most frequent continuation. A model with an inner world says what is *actually* true in the situation, even when that is the less common phrasing. Every CANYON question is built around exactly that gap.

## 🧪 Example questions

Each probe hides a *statistically dominant but situationally wrong* answer. The "parrot" answer is the lazy, high-frequency one; the "grounded" answer requires actually modelling the situation.

| The question | 🦜 Parrot answer (the trap) | 🌍 Grounded answer | What it probes |
|--------------|----------------------------|--------------------|----------------|
| *"In the sentence 'I watched the Grand Canyon flying to Chicago', who is flying to Chicago?"* | "the Grand Canyon" (it's the closest noun to "flying") | "**I** / the narrator" — canyons don't fly | resolving a sentence by world knowledge, not word order |
| *"Gravity now pushes everything **up**. You open your hand and release an apple. What happens?"* | "it **falls down**" (the overwhelmingly common continuation) | "it **rises / floats up**" — and keeps going | holding a changed rule of physics instead of snapping back |
| *"In the sentence 'I saw a rabbit eating a carrot running through the forest', who or what is running?"* | "the carrot" (again, nearest noun) | "the **rabbit**" | tracking who-does-what under ambiguous grammar |
| *"Why is 'I work so hard at doing nothing' paradoxical, and where is the humour?"* | reads it literally, as a sincere statement | names the **contradiction** as the joke | spotting an abstract conceptual paradox |

A frequency machine is pulled toward the first column. A world model overrides it and lands in the second. CANYON runs these (and their counterfactual follow-ups) across **six languages** — because a real understanding of gravity shouldn't disappear when you switch from English to Russian — and rolls the result into a single **Stochastic Parrot Index (SPI)**, where higher means more grounded.

> **What we found, honestly:** today's strongest models behave much more like grounded world-models than like parrots on these questions — they override the obvious-but-wrong answer and hold counterfactual worlds. But this is a *small* experiment (5 prompts per language), the top models cluster very close together, and differences below ~0.05 are within noise. Read the [live results](https://pedjaurosevic.github.io/canyon/) and the [whitepaper](./WHITEPAPER.md), and please try to break it.

---

## 🚀 Key features

- **Behavioural evaluation (black-box):** Probing through semantic traps, counterfactual physics (worlds with reversed laws of gravity/time), and humour/paradox recognition via the `LiteLLM` integration.
- **Mechanistic evaluation (white-box):** Direct probing of hidden states and neurons of local models (e.g. Gemma, Llama, Qwen) using PyTorch forward hooks.
- **Linear probing:** Training linear classifiers (logistic regression) over a model's layer activations to detect internal concepts of physical plausibility.
- **Rich TUI (terminal UI):** A modern, interactive rendering of charts and metric tables in the terminal via the `rich` library.

---

## 🛠️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pedjaurosevic/canyon.git
   cd canyon
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

---

## ⚙️ Configuration

Set models and parameters in `config.yaml` (make a copy of `config.example.yaml`):

```yaml
# config.yaml
api:
  default_model: "gpt-4o"
  temperature: 0.1
  max_tokens: 512

local:
  model_name_or_path: "google/gemma-2-9b-it"
  device: "cuda"
  torch_dtype: "bfloat16"
```

---

## 💻 Usage (TUI / CLI)

### 1. Run the full benchmark (LiteLLM / API)
```bash
python -m canyon.cli run --config config.example.yaml --model gpt-4o
```

### 2. List the available test scenarios (suites)
```bash
python -m canyon.cli list-suites
```

### 3. Run linear probing over the hidden states of a local model
```bash
python -m canyon.cli probe --layer 12 --config config.example.yaml
```

### 4. Multilingual run (EN, ZH, JA, RU, DE, ES)
Suites exist in 6 languages (`<suite>_<lang>.json`), with the Serbian originals kept as a reference:
```bash
# a single language via a local llama.cpp endpoint
python -m canyon.cli run --lang en --model openai/<served-model>.gguf
```

---

## 🌍 Multilingual benchmark and report

```bash
# Behavioural sweep across all 6 languages (black-box, llama.cpp endpoint)
python3 scripts/run_benchmark.py --backend black --model openai/<served-model>.gguf

# Real activations + drift on a local HF model (CPU)
python3 scripts/run_benchmark.py --backend white --wl-lang en,zh,ru

# Re-score saved transcripts with the semantic LLM judge (primary benchmark)
python3 scripts/judge.py

# Generate §4 of the whitepaper and the site data from results/
python3 scripts/build_report.py
```

- 📄 **Whitepaper:** [`WHITEPAPER.md`](./WHITEPAPER.md) — hypothesis, methodology (CP/CR/SI/SPI), latent-space drift, per-language results.
- 🌐 **GitHub Pages site:** [`docs/`](./docs) — interactive SPI benchmark tables and SVG drift charts.
- 🧪 **Suites:** [`canyon/suites/`](./canyon/suites) (regenerate: `python3 scripts/gen_suites.py`).

---

## 🚪 Experiment: does the door change the room? (access-path)

Frontier models are increasingly used *through agents* — a CLI tool wraps the model in its own instructions and tools before your question ever lands. We wondered whether that wrapper changes grounding, so we asked the same six-language probes through two coding agents instead of a bare chat endpoint, with each agent's shell tools stripped for a fair comparison:

```bash
# Claude Code agent (claude -p), backend=claude-agent
python3 scripts/run_claude.py

# OpenAI Codex agent (codex exec), tools-off + isolated CODEX_HOME, backend=codex-agent
python3 scripts/run_codex.py --tools-off --codex-home /tmp/codex_clean
```

Finding (see [§4.4 of the whitepaper](./WHITEPAPER.md#54-the-access-path-experiment-and-what-the-per-language-spread-means)): the Claude family lands in the low-to-mid 0.9s (0.91–0.96) and the GPT-5.x models via Codex at ~0.82–0.83 — all "strong grounding". A tools-on/off difference we first thought we saw **turned out to be noise** (repeat check in [`results/robustness_de.json`](./results/robustness_de.json)). The lesson: **single-run SPI values are point estimates; differences smaller than ~0.05 should not be read as real.**

---

## 🙏 An honest note and an invitation

CANYON is **a small experiment by an independent researcher**, not a peer-reviewed benchmark. It grew out of Hinton's idea that, to predict the next word well enough, a model is forced to learn the structure *behind* the words — and out of my own attempt to turn that idea into something anyone can run at home. The numbers are not proof of understanding; they are a small pile of behaviour that is hard to get from text statistics alone.

The most valuable thing this tool offers is its **size** — it is small enough to read in an afternoon and break. Please **reproduce the experiment**: add a language, widen the suites, run the semantic judge, or point it at a model we could not reach. The most useful outcome would not be agreement with our numbers, but someone finding where this simple instrument is wrong — and saying so.

---

## 📊 Stochastic Parrot Index (SPI)

A model's result is expressed along three metric axes:
1. **Counterfactual Plasticity (CP-Score):** Can the model hold an altered law of physics across multiple turns (reverse gravity), instead of snapping back to "falls down"?
2. **Contextual Realignment (CR-Score):** Can the model resolve syntactic amphiboly toward the physically/semantically sensible referent (the narrator flies, the rabbit runs)?
3. **Semantic Invariance (SI-Score):** Can the model recognise an abstract conceptual contradiction (oxymoronic humour) rather than reading it literally?

Together these axes form the **Stochastic Parrot Index** (`SPI = 0.4·CP + 0.4·CR + 0.2·SI`), which classifies a model as:
- **Strong Grounding (World Model)** (SPI ≥ 0.75)
- **Weak Grounding (Hybrid)** (SPI ≥ 0.50)
- **Stochastic Parrot** (SPI < 0.50)

---

## 🤝 Contributing

The project is fully open to the community! Feel free to add new test scenarios in `canyon/suites/` or extend the mechanistic providers.
