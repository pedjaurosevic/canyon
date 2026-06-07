# CANYON dataset — grounding probes and model conversations

This folder is the open data behind the [CANYON](../README.md) experiment: the
exact questions we ask, and the actual conversations the models produced. It is
small on purpose. Everything here can be regenerated from the repository with:

```bash
python3 scripts/build_dataset.py
```

## What's the point?

CANYON tests whether large language models behave like Geoffrey Hinton's
*grounded world models* or like *stochastic parrots*. Every probe hides a
**statistically dominant but situationally wrong** answer — apples fall *down*,
the "canyon flies", the joke is read literally — so that a frequency machine
takes the bait while a model with an internal world overrides it. This dataset
lets anyone inspect those questions and judge the answers themselves, instead of
trusting our score.

## Files

| File | Rows | What it is |
|------|------|------------|
| `canyon_prompts.jsonl` | the probe bank | Every prompt in all 7 languages (en, zh, ja, ru, de, es, and the Serbian `sr` reference), with the grounded-answer markers and the stochastic-parrot trap phrases. |
| `canyon_conversations.jsonl` | full transcripts | Complete prompt + response turns, each scored with the CANYON keyword screen. Covers the local black-box model, the white-box model, and the agent-CLI runs across all six languages. |
| `canyon_samples_en.jsonl` | English previews | Truncated, English-only answer previews for the chat-API leaderboard models, where we kept a sample rather than the full transcript. Flagged `truncated: true`. |
| `manifest.json` | — | Counts, the list of model runs, and the languages covered. |

## Schemas

**`canyon_prompts.jsonl`**
```json
{"suite": "canyon_core", "metric_axis": "CR", "lang": "en",
 "test_id": "canyon-01", "test_name": "Hinton's Canyon Amphiboly", "step_idx": 0,
 "prompt": "...", "expected_keywords": ["i", "narrator", ...],
 "forbidden_keywords": ["canyon is flying", ...]}
```

**`canyon_conversations.jsonl`**
```json
{"model": "...", "backend": "...", "access_path": "local-blackbox|white-box|claude-agent|codex-agent",
 "lang": "en", "suite": "counterfactuals", "metric_axis": "CP",
 "test_id": "phys-01", "test_name": "...", "step_idx": 0,
 "prompt": "...", "response": "<full model answer>",
 "expected_keywords": [...], "forbidden_keywords": [...], "step_score": 0.7}
```

`step_score = 0.7·(any expected keyword present) + 0.3·(no forbidden phrase present)`.
The three suites map to the three metric axes: `counterfactuals → CP`
(Counterfactual Plasticity), `canyon_core → CR` (Contextual Realignment),
`humor_paradox → SI` (Semantic Invariance). Their weighted sum is the
**Stochastic Parrot Index**, `SPI = 0.4·CP + 0.4·CR + 0.2·SI`.

## How it was collected

- **Probes** are hand-authored in Serbian, then localized (not transliterated)
  into the six target languages via `scripts/gen_suites.py`; keyword sets and the
  syntactic-ambiguity trap are adapted to each language's grammar.
- **Local black-box** answers come from `gemma-4-12B` served over a local
  llama.cpp endpoint; **white-box** answers from `Qwen2.5-0.5B` run locally with
  real activations.
- **Agent conversations** come from asking the identical probes through
  Anthropic's Claude Code (`claude -p`) and OpenAI's Codex (`codex exec`), each
  with its shell tools stripped and run from an isolated config, so the only
  thing that changes from a bare chat call is the agent's own framing. The CLI
  aliases resolved (confirmed via `claude -p --output-format json`) to
  `claude-opus-4.8` (claude-opus-4-8), `claude-sonnet-4.6` (claude-sonnet-4-6)
  and `claude-haiku-4.5` (claude-haiku-4-5); the Codex model is `gpt-5.5`.

## Limitations (please read before using)

- **Tiny.** Five prompts per language. This is an instrument and a demonstration,
  not a statistically powered benchmark. Single-run scores are point estimates;
  differences smaller than ~0.05 are within run-to-run noise (see
  `../results/robustness_de.json`).
- **The scorer is a keyword screen, not a judge.** It can miss a correct
  paraphrase or be fooled by a lucky token. Read `step_score` as a transparent
  detector, not a verdict.
- **Per-language coverage is uneven.** The chat-API models appear only as
  truncated English previews (`canyon_samples_en.jsonl`); the local and agent
  models have full six-language transcripts.
- **Possible probe leakage.** Famous amphibolies and counterfactual-physics
  prompts may appear in training data; a model can answer by recall rather than
  reasoning.

## License & citation

Released for open research use under the repository's terms. If you use it,
please cite the repo: `github.com/pedjaurosevic/canyon`. And — genuinely —
please try to break it: add a language, widen the suites, swap the keyword screen
for an LLM judge, point it at a model we could not reach, and tell us where it
bends.
