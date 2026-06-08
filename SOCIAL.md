# CANYON — Social media posts

Ready-to-post announcements for the CANYON benchmark.
Copy-paste what fits your platform.

**Links to use in posts:**
- Main site: https://pedjaurosevic.github.io/canyon/
- GitHub repo: https://github.com/pedjaurosevic/canyon
- Whitepaper: https://github.com/pedjaurosevic/canyon/blob/main/WHITEPAPER.md

---

## Twitter / X

### Post 1 — Launch (long, ~280 chars)

> Do LLMs really understand, or are they just next-token parrots?
>
> I built CANYON — a multilingual benchmark that asks trick questions where the
> statistically obvious answer is wrong. If the model overrides the trap, it
> passes. 6 languages, 18 models, full transcripts published.
>
> 🧵 https://pedjaurosevic.github.io/canyon/

### Post 2 — The Hinton question

> Geoffrey Hinton says LLMs build internal world models. The "stochastic parrot"
> camp says it's all surface statistics.
>
> CANYON tests this with a simple idea: ask questions where the common answer is
> wrong. An apple in reverse gravity doesn't fall down — does the model say
> "up" or default to "down"?
>
> Results → https://pedjaurosevic.github.io/canyon/

### Post 3 — Multilingual angle

> Does a model's "understanding" survive language changes?
>
> CANYON runs the same adversarial probes in EN, ZH, JA, RU, DE, ES. A real
> world model should be language-invariant — gravity doesn't change because you
> ask in Russian.
>
> SPI scores per language → https://pedjaurosevic.github.io/canyon/

### Post 4 — Open data

> Every CANYON result is published as full conversation transcripts — not just
> scores. You can read the actual model answers and judge for yourself.
>
> 525 scored turns, 18 model runs, plain JSONL.
>
> Dataset: https://github.com/pedjaurosevic/canyon/tree/main/dataset
> Interactive viz: https://pedjaurosevic.github.io/canyon/

### Post 5 — Honest note (thread start)

> I built CANYON as an independent researcher, not a lab. It's small — 5 prompts
> per language. The numbers aren't proof; they're an instrument.
>
> The most useful outcome wouldn't be agreement, but someone finding where
> this simple test is wrong. Please break it.
>
> Repo: https://github.com/pedjaurosevic/canyon

---

## LinkedIn

### Post — Full announcement

> **CANYON: Testing whether LLMs actually understand — or just predict words**
>
> I've been thinking about Geoffrey Hinton's claim that large language models,
> by learning to predict the next word well enough, are forced to build internal
> world models. The opposing view — the "stochastic parrot" hypothesis — says
> it's all surface statistics with no real understanding.
>
> To explore this, I built CANYON: an open-source benchmark that asks models
> trick questions where the statistically obvious answer is wrong. For example:
> "Gravity now pushes everything up. You drop an apple. What happens?"
> A parrot says "falls down." A model with a world model says "rises."
>
> The benchmark runs in 6 languages (EN, ZH, JA, RU, DE, ES), measures three
> metric axes (counterfactual plasticity, contextual realignment, semantic
> invariance), and rolls them into a single Stochastic Parrot Index (SPI).
>
> **What I found:** Today's strongest models behave much more like grounded
> world-models than like parrots — they override the obvious wrong answer and
> hold counterfactual worlds across turns. But this is a small experiment, and
> differences below ~0.05 SPI are within noise.
>
> **What's different about this benchmark:** Every result is published as full
> conversation transcripts. You don't have to trust a score — you can read the
> actual model answers yourself.
>
> I'd love for people to reproduce this, add languages, widen the suites, or
> point it at models I couldn't reach. The whole thing is small enough to read
> in an afternoon.
>
> 🔗 Interactive leaderboard: https://pedjaurosevic.github.io/canyon/
> 🔗 GitHub repo: https://github.com/pedjaurosevic/canyon
> 🔗 Whitepaper: https://github.com/pedjaurosevic/canyon/blob/main/WHITEPAPER.md
>
> #LLM #AIResearch #MachineLearning #MechanisticInterpretability #OpenSource

---

## Reddit

### r/MachineLearning — [R] Discussion / results

> **\[R\] CANYON — a multilingual benchmark testing whether LLMs have internal
> world models (Hinton's hypothesis)**

> I built a small benchmark that tests Geoffrey Hinton's grounding hypothesis
> against the stochastic parrot view. The core idea: ask adversarial questions
> where the statistically dominant answer is situationally wrong, then check if
> the model overrides the trap.
>
> **Three probe families:**
> - Counterfactual physics (reverse gravity, time reversal)
> - Syntactic amphiboly (who flies in "I watched the Grand Canyon flying to Chicago"?)
> - Oxymoronic humour (paradox detection)
>
> **6 languages:** English, Mandarin, Japanese, Russian, German, Spanish
> (Serbian originals published as reference)
>
> **Metric:** Stochastic Parrot Index (SPI) = 0.4·CP + 0.4·CR + 0.2·SI
>
> **18 models tested** including Qwen3, DeepSeek V4 Flash/Pro, Gemma 4
> (local + API), GPT-5.x, Claude 4.x, Llama 3.3/4, Qwen 2.5-0.5B
>
> **Key finding:** Top models cluster around SPI 0.93–0.97 on the primary
> leaderboard (Strong Grounding). Differences below ~0.05 are run-to-run noise.
>
> **What makes this different:** Full conversation transcripts are published as
> JSONL — you can read every model answer yourself instead of trusting a score.
> Also includes white-box latent-space drift analysis (real hidden-state
> activations).
>
> Interactive leaderboard: https://pedjaurosevic.github.io/canyon/
> Repo: https://github.com/pedjaurosevic/canyon
> Whitepaper: https://github.com/pedjaurosevic/canyon/blob/main/WHITEPAPER.md
>
> Honest note: this is a small experiment by an independent researcher, not a
> peer-reviewed benchmark. 5 prompts per language. Please reproduce and break it.

### r/LocalLLaMA — Local models focus

> **Local LLM grounding benchmark — CANYON results with Gemma 4 12B (llama.cpp)**

> I ran the CANYON semantic grounding benchmark locally with
> Gemma 4 12B Q4_K_M on llama.cpp. Full results with transcripts:
>
> SPI scores per language:
> - EN: 1.00
> - ZH: 1.00
> - JA: 1.00
> - RU: 1.00
> - DE: 1.00
> - ES: 0.94
>
> Also ran white-box probing with Qwen 2.5-0.5B (hidden-state activations,
> semantic drift across layers).
>
> The benchmark asks trick physics/counterfactual questions and checks if the
> model overrides the statistically-obvious-but-wrong answer. Full repo is
> Python — easy to run against any local model via llama.cpp or HF.
>
> Repo: https://github.com/pedjaurosevic/canyon
> Site: https://pedjaurosevic.github.io/canyon/

---

## Hacker News — Show HN

> **Show HN: CANYON — open-source benchmark testing if LLMs really understand
> or just predict words**

> I built CANYON to test Geoffrey Hinton's claim that LLMs build internal world
> models. The approach: ask trick questions where the common answer is wrong,
> then see if the model falls for it.
>
> Three test families: counterfactual physics (reverse gravity), syntactic traps
> (who flies in "I watched the Grand Canyon flying to Chicago"?), and oxymoronic
> humour.
>
> The results are published as full conversation transcripts — you can read
> the actual model answers, not just scores. 18 models, 6 languages.
>
> Interactive leaderboard: https://pedjaurosevic.github.io/canyon/
> GitHub: https://github.com/pedjaurosevic/canyon
>
> It's small (5 prompts per language), Python, and easy to run against any
> local GGUF or API. Please try to break it — the most useful outcome would
> be someone finding where this simple test is wrong.

---

## Mastodon / Bluesky

### Version A (short, 500 chars)

> I built CANYON — a multilingual benchmark that tests whether LLMs really
> understand or just predict words. It asks trick questions where the obvious
> answer is wrong (reverse gravity, syntactic traps). 6 languages, 18 models,
> full transcripts published.
>
> Results → https://pedjaurosevic.github.io/canyon/
> Repo → https://github.com/pedjaurosevic/canyon

### Version B (with context, ~900 chars)

> Geoffrey Hinton argues that to predict the next word well enough, LLMs are
> forced to build internal world models. The "stochastic parrot" view says it's
> all surface statistics.
>
> I built CANYON to test this. The idea is simple: ask questions where the
> statistically obvious answer is wrong, then check if the model overrides it.
> An apple in reverse gravity doesn't fall down — does the model say "up"?
>
> It runs in 6 languages, measures 3 metric axes (CP/CR/SI), and rolls them
> into a Stochastic Parrot Index (SPI). Every result comes with full
> conversation transcripts so you can judge the answers yourself.
>
> https://pedjaurosevic.github.io/canyon/
> https://github.com/pedjaurosevic/canyon

---

## Short quotes for images / cards

- "Do LLMs build world models or just stitch words together? CANYON asks trick questions to find out."
- "An apple in reverse gravity doesn't fall down. Does your model know that?"
- "6 languages. 18 models. 525 scored turns. Full transcripts. Zero black box."
- "Small enough to read in an afternoon. Please break it."
- "SPI = 0.4·CP + 0.4·CR + 0.2·SI — higher means more grounded."
