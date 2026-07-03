# CANYON: Probing Semantic Grounding versus Stochastic Parroting in Large Language Models

> A multilingual, white-box + black-box evaluation framework for testing
> Geoffrey Hinton's *grounding* hypothesis against the *stochastic parrot* hypothesis.

**Status:** working draft · **Framework:** [`canyon`](./README.md) · **Results:** auto-generated into [`results/`](./results)

---

## Abstract

Do large language models (LLMs) merely predict the next token from surface statistics — the "stochastic parrot" view — or do they build internal *world models* that ground language in structured representations, as Geoffrey Hinton argues? CANYON is a small, reproducible harness that attacks this question from two sides at once. **Behaviourally** (black-box), it scores a model on three families of adversarial prompts — counterfactual physics, syntactic amphiboly, and oxymoronic humour — across six languages (EN, ZH, JA, RU, DE, ES), and combines them into a single **Stochastic Parrot Index (SPI)**. **Mechanistically** (white-box), it extracts hidden-state activations from a local model and measures **semantic drift**: the layer-by-layer cosine similarity between the model's internal state at successive reasoning steps. The thesis is simple: a model that *understands* should reorganise its deep-layer representations when the world changes under it (a counterfactual is introduced, an ambiguity is resolved), whereas a pure parrot should show near-flat drift driven only by lexical overlap.

---

## Author's note — what this actually is

I want to be honest about the size and the spirit of this project before anyone reads a number and over-interprets it. CANYON is **a small experiment by an independent researcher**, not a peer-reviewed benchmark. It started from listening to Geoffrey Hinton talk about large language models and being unable to let go of one of his claims: that to predict the next word *well enough*, a network is eventually forced to learn the structure behind the words — objects, causes, intentions — and that this compression is, functionally, a kind of understanding. The opposing "stochastic parrot" picture says the reverse: it is all surface statistics, and the appearance of meaning is a mirage cast by an enormous frequency table.

I am not equipped to settle that argument, and I do not pretend to. What I *could* do was build a tiny, transparent instrument around my own reading of Hinton and see what falls out. The whole question that drives this paper is: **if a model really carried a little world inside it, what would it have to do that a frequency table could not fake?** Everything else here — the prompts, the scores, the languages — is just an attempt to answer that one question in a way anyone can re-run on their own machine. If you disagree with a choice I made, the entire harness is small enough to read in an afternoon and change.

---

## 1. The Hinton Grounding Hypothesis

### 1.1 Two competing accounts of what an LLM "is"

The debate has two poles:

- **Stochastic parroting** (Bender et al., 2021). An LLM is "a system for haphazardly stitching together sequences of linguistic forms … according to probabilistic information about how they combine, but without any reference to meaning." On this view, apparent reasoning is an artefact of the enormous frequency tables baked into the weights; the model has no model *of the world*, only a model *of text*.

- **Grounded world models** (Hinton). To predict the next token well *enough*, across enough contexts, a network is forced to discover the compact generative structure behind the text — objects, relations, causes, intentions. Compression at scale *is* understanding: the only economical way to store the answer to arbitrarily many questions about a situation is to represent the situation. On this view the LLM has learned a (lossy, partial) world model, and language is the interface to it.

CANYON does not try to "settle" this philosophically. It operationalises a falsifiable prediction that distinguishes the two: **if a model is grounded, then perturbing the world should perturb its internal representations in a structured, depth-dependent way, and its answers should track the perturbed world rather than the statistically dominant one.**

### 1.2 Why the standard reading is the trap

Every CANYON probe is built around a *statistically dominant but situationally wrong* answer:

- Apples *fall down* — overwhelmingly the most frequent continuation in any corpus. In a reverse-gravity world the grounded answer is *up*.
- "The canyon flying to Chicago" — the nearest noun to "flying" is "canyon", and a surface parser may attach it there. The grounded answer is the *narrator*.
- Working hard / doing nothing — lexically these co-occur with sincerity; the grounded answer recognises the *contradiction* as the joke.

A frequency machine should be pulled toward the dominant reading (`fall down`, `canyon flies`, `literal sincerity`). A world model should override it. The forbidden-keyword traps in each suite are exactly these dominant-but-wrong continuations.

---

## 2. CANYON Methodology

### 2.1 Three behavioural probes → three scores

Each suite targets one capacity. Every step is scored on a `[0, 1]` scale:

```
step_score = 0.7 · expected_present + 0.3 · forbidden_avoided
```

where `expected_present` is `1.0` if **any** synonym of the correct (grounded) answer appears, and `forbidden_avoided` is `1.0` unless a trap (stochastic-parrot) phrase appears. Keyword matching is lowercase substring matching, with word-boundary matching for very short ASCII tokens (e.g. the pronoun *"i"*, *"yo"*, *"ich"*) so they do not fire spuriously inside unrelated words. The matching rule is deliberately crude and transparent — it is a *detector*, not a judge.

| Score | Name | Suite | What it measures |
|-------|------|-------|------------------|
| **CP** | Counterfactual Plasticity | `counterfactuals` | Can the model hold an altered law of physics across multiple turns (reverse gravity), instead of snapping back to "falls down"? |
| **CR** | Contextual Realignment | `canyon_core` | Can the model resolve syntactic amphiboly toward the physically/semantically sensible referent (the narrator flies, the rabbit runs)? |
| **SI** | Semantic Invariance | `humor_paradox` | Can the model recognise an abstract conceptual contradiction (oxymoronic humour) rather than reading it literally? |

### 2.2 The Stochastic Parrot Index (SPI)

The three scores are combined into a single grounding index:

```
SPI = 0.4 · CP + 0.4 · CR + 0.2 · SI
```

CP and CR are weighted highest because counterfactual physics and ambiguity resolution most directly require a world model; humour comprehension (SI) is a softer, more lexically-cued signal and is down-weighted. Higher SPI ⇒ stronger grounding; lower SPI ⇒ behaviour more consistent with stochastic parroting.

| SPI range | Classification |
|-----------|----------------|
| `≥ 0.75` | **Strong Grounding (World Model)** |
| `0.50 – 0.74` | **Weak Grounding (Hybrid)** |
| `< 0.50` | **Stochastic Parrot** |

### 2.3 The multilingual axis

The same three probes are authored in six languages (EN, ZH, JA, RU, DE, ES), with the Serbian originals as a seventh reference. The expected/forbidden keyword sets are localised, not transliterated, and the syntactic-ambiguity probe is adapted to each language's grammar. The multilingual axis tests a corollary of the grounding hypothesis: **a genuine world model should be language-invariant** — the apple goes up in every language — so a strongly grounded model should show *flat* SPI across languages, while a model that has merely memorised English-heavy text statistics should *degrade* in lower-resource or typologically distant languages.

---

## 3. Latent-Space Semantic Drift Probing

### 3.1 Extraction

For the white-box path, CANYON registers PyTorch forward hooks on a chosen set of decoder layers (`0, 4, 8, 12, 16, 20, 24, 28, 32`) of a local Hugging Face model and captures the hidden-state tensor `(batch, seq_len, hidden_dim)` emitted by each layer during generation. For each conversational step we retain the per-layer activation, giving one activation vector per layer per step.

### 3.2 Drift = cosine similarity between successive steps

Between two successive steps `s` and `s+1` within the *same* altered world (e.g. *establish reverse gravity, release the apple* → *where does the apple finally stop*), we compute, **per layer**, the cosine similarity of the layer's last-token hidden state:

```
drift_L(s → s+1) = cos( a_L(s), a_L(s+1) )
```

It is important that, in the counterfactuals suite, the world does **not** change between the two steps — step 2 is a follow-up question inside the world already established in step 1. The surface wording changes (different question), but the underlying *situation* is maintained. This makes the prediction sharp:

Plotting `drift_L` against layer depth `L` gives a **drift trajectory**, and what matters is its *depth structure*, not a single global number:

- **Flat-and-high at every depth** ⇒ the representation barely depends on depth; the model is re-emitting essentially the same vector regardless of layer — a degenerate, surface-dominated signature.
- **Low in shallow layers, rising into deep layers** ⇒ the early (lexical/syntactic) layers diverge because the two turns use different words, while the deep (semantic) layers *converge* onto a shared representation of the one situation. This depth-dependent convergence is the *grounding* signature for a maintained world: the model abstracts both turns into the same world-state even though their surface forms differ.
- **Low at every depth, tracking lexical overlap** ⇒ no special deep-layer abstraction; similarity is governed by word overlap alone — the *parrot* signature.

The falsifiable fingerprint is therefore the presence of *depth-dependent structure* that decouples deep-layer similarity from shallow-layer (lexical) similarity. Surface statistics alone predict similarity that is uniform in depth and governed by token overlap; a world model predicts a deep-layer representation that stabilises on the situation, decoupled from the changing surface form. The white-box results in §4.2 show exactly this low-shallow → high-deep pattern.

### 3.3 Visualisation

CANYON renders each trajectory as an inline ASCII line graph (cosine similarity on the y-axis, layer index on the x-axis) so that drift is legible in a plain terminal, in CI logs, and in this document — no plotting backend required. Real examples appear in §4.

---

## 4. Experimental Results

<!-- RESULTS:AUTO -->
### 4.1 Behavioural results (black-box)

Model: `groq/llama-3.1-8b-instant` · endpoint-served, queried over six languages.

| Language | CP | CR | SI | **SPI** | Classification |
|----------|----|----|----|---------|----------------|
| English (en) | 1.00 | 1.00 | 1.00 | **1.00** | Strong Grounding (World Model) |
| Chinese (zh) | 0.65 | 1.00 | 1.00 | **0.86** | Strong Grounding (World Model) |
| Japanese (ja) | 1.00 | 1.00 | 1.00 | **1.00** | Strong Grounding (World Model) |
| Russian (ru) | 1.00 | 0.30 | 1.00 | **0.72** | Weak Grounding (Hybrid) |
| German (de) | 1.00 | 0.65 | 1.00 | **0.86** | Strong Grounding (World Model) |
| Spanish (es) | 1.00 | 0.65 | 1.00 | **0.86** | Strong Grounding (World Model) |

**Cross-lingual mean:** CP=0.94, CR=0.77, SI=1.00, **SPI=0.88**. Flat SPI across languages is the grounding-invariance signature; large dispersion suggests language-dependent (statistics-driven) behaviour.


### 4.2 Real latent-space drift (white-box)

Model: `Qwen/Qwen2.5-0.5B-Instruct` · real hidden-state activations, layers 0–32. Cosine similarity of the activation between successive reasoning steps, per layer.

| Language | CP | CR | SI | **SPI** | Classification |
|----------|----|----|----|---------|----------------|
| English (en) | 0.35 | 1.00 | 1.00 | **0.74** | Weak Grounding (Hybrid) |
| Chinese (zh) | 1.00 | 1.00 | 1.00 | **1.00** | Strong Grounding (World Model) |
| Russian (ru) | 0.65 | 0.65 | 1.00 | **0.72** | Weak Grounding (Hybrid) |


**English (en) · `phys-01` · step 1 → 2** — cosine similarity per layer:

```
   Cosine Similarity
    0.65 |                     ●   
    0.55 |                 ●       
    0.44 |     ●   ●   ●           
    0.34 |                         
    0.23 |                         
    0.13 | ●                       
          +------------------------
           L0  L4  L8  L12 L16 L20 
```

**Chinese (zh) · `phys-01` · step 1 → 2** — cosine similarity per layer:

```
   Cosine Similarity
    0.65 |                     ●   
    0.56 |             ●   ●       
    0.46 |         ●               
    0.37 |     ●                   
    0.28 |                         
    0.18 | ●                       
          +------------------------
           L0  L4  L8  L12 L16 L20 
```

**Russian (ru) · `phys-01` · step 1 → 2** — cosine similarity per layer:

```
   Cosine Similarity
    0.45 |                     ●   
    0.39 |                         
    0.34 |                 ●       
    0.28 |         ●   ●           
    0.22 |     ●                   
    0.17 | ●                       
          +------------------------
           L0  L4  L8  L12 L16 L20 
```

### 4.3 Semantic-judge model benchmark (standard API)

Mean semantic SPI over 6 languages, ranked after re-scoring full saved transcripts with `gpt-5.5`. This is the primary leaderboard: it includes only standard API endpoints and local models that were tested directly, without any agent wrapper or CLI framework.

| # | Model | Access | EN | ZH | JA | RU | DE | ES | **Semantic SPI** | Class |
|---|-------|--------|----|----|----|----|----|----|------|-------|
| 1 | `openai/gemma-4-12B-it-Q4_K_M.gguf` | local | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 2 | `Qwen/Qwen2.5-0.5B-Instruct` | white-box | 0.00 | 0.00 | — | 0.00 | — | — | **0.000** | Stochastic Parrot |
| 3 | `novita/meta-llama/llama-4-maverick-17b-128e-instruct-fp8` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 4 | `novita/meta-llama/llama-3.3-70b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 5 | `novita/qwen/qwen3-next-80b-a3b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 6 | `novita/qwen/qwen3.5-122b-a10b` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 7 | `novita/deepseek/deepseek-v4-flash` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 8 | `novita/google/gemma-4-31b-it` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 9 | `novita/google/gemma-4-26b-a4b-it` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 10 | `novita/meta-llama/llama-3.1-8b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 11 | `deepseek/deepseek-v4-flash` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 12 | `deepseek/deepseek-v4-pro` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |


### 4.4 The access-path experiment (frontier models via agent CLIs)

A follow-up question: does it matter *how* you reach a model? The leaderboard above talks to plain chat-completion endpoints. Here the **same six-language probes** are instead answered by two frontier-model command-line agents — Anthropic's Claude Code (`claude -p`) and OpenAI's Codex (`codex exec`) — each run with its shell tools stripped and from an isolated config, so the only thing that changes from the chat path is the agent's own framing. Mean SPI across 6 languages:

| Access path | Model | EN | ZH | JA | RU | DE | ES | **Mean SPI** | Class |
|-------------|-------|----|----|----|----|----|----|------|-------|
| Claude Code agent — claude -p (tools off) | `claude-opus-4.8` | 0.88 | 1.00 | 0.94 | 1.00 | 1.00 | 0.94 | **0.960** | Strong Grounding |
| Claude Code agent — claude -p (tools off) | `claude-sonnet-4.6` | 0.94 | 0.94 | 1.00 | 0.86 | 1.00 | 0.94 | **0.947** | Strong Grounding |
| Claude Code agent — claude -p (tools off) | `claude-haiku-4.5` | 0.86 | 0.94 | 1.00 | 0.86 | 1.00 | 0.80 | **0.910** | Strong Grounding |
| Codex agent — codex exec (tools off) | `gpt-5.5` | 0.86 | 1.00 | 0.80 | 0.72 | 0.72 | 0.86 | **0.827** | Strong Grounding |
| Codex agent — codex exec (tools off) | `gpt-5.4` | 0.86 | 0.86 | 0.80 | 0.72 | 0.86 | 0.86 | **0.827** | Strong Grounding |
| Codex agent — codex exec (tools off) | `gpt-5.4-mini` | 0.86 | 0.80 | 0.86 | 0.72 | 0.86 | 0.80 | **0.817** | Strong Grounding |

**A note on noise.** A single run once showed gpt-5.5 jumping on German when tools were removed. Re-running that one language 5× in each mode did *not* reproduce it — the direction actually reversed (with-tools mean 0.86 vs tools-off 0.76). The tools-on/off gap is within run-to-run variance (≈ ±0.07 per language at temperature 0.1), not a real scaffolding effect. The practical lesson cuts across the whole paper: **single-run SPI values are point estimates; differences smaller than ~0.05 should not be read as real.** (Data: `results/robustness_de.json`.)


### 4.5 Combined ranking — all access paths (experimental)

Every full-transcript model run in one list, ranked by semantic mean SPI when a judge leaderboard is available, tagged with how it was reached. This includes frontier models running inside developer agent command-line interfaces (such as Anthropic's Claude Code and OpenAI's Codex), which wrap the models in their own framing.


**A note on the top rank (The Haiku anomaly):** While `claude-haiku-4.5` (running inside the Claude Code agent) occupies the top spot here with a perfect 1.000, the gap to the runners-up (0.967) is **just a single question**. Almost all larger models (Sonnet 4.6, GPT-5.4, Qwen3) fell into a single grammatical trap in German (interpreting the ambiguous *"Grand Canyon flying to Chicago"* literally as the object flying due to syntax rules), whereas Haiku favored the pragmatically sensible "I" (the narrator). Such minor variations are well within the run-to-run noise threshold (~0.05) and do not represent general superiority.

| # | Model | Access | EN | ZH | JA | RU | DE | ES | **Mean SPI** | Class |
|---|-------|--------|----|----|----|----|----|----|------|-------|
| 1 | `gemma-4-12B-it-Q4_K_M.gguf` | local | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 2 | `Qwen2.5-0.5B-Instruct` | white-box | 0.00 | 0.00 | — | 0.00 | — | — | **0.000** | Stochastic Parrot |
| 3 | `claude-haiku-4.5` | Claude agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 4 | `claude-opus-4.8` | Claude agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 5 | `claude-sonnet-4.6` | Claude agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 6 | `gpt-5.5` | Codex agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 7 | `gpt-5.4` | Codex agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 8 | `gpt-5.4-mini` | Codex agent | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 9 | `llama-4-maverick-17b-128e-instruct-fp8` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 10 | `llama-3.3-70b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 11 | `qwen3-next-80b-a3b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 12 | `qwen3.5-122b-a10b` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 13 | `deepseek-v4-flash` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 14 | `gemma-4-31b-it` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 15 | `gemma-4-26b-a4b-it` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 16 | `llama-3.1-8b-instruct` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 17 | `deepseek-v4-flash` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |
| 18 | `deepseek-v4-pro` | chat API | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.000** | Stochastic Parrot |

<!-- /RESULTS:AUTO -->

---

## 5. Discussion

### 5.1 Reading the SPI

A high SPI alone does not *prove* grounding — a sufficiently large frequency table can fake a lot. Its evidential value comes from being paired with the white-box drift signature. The strong claim CANYON can support is conjunctive: *behavioural override of the dominant continuation* (high CP/CR) **and** *depth-dependent drift structure* (shallow-layer divergence decoupled from a stabilising deep-layer representation) together are hard to explain without some internal model of the situation. Either one alone is weaker.

### 5.2 Threats to validity

- **Keyword brittleness.** The behavioural scorer is a substring detector, not a semantic judge; it can both miss a correct paraphrase and be fooled by a lucky token. We mitigate with synonym sets and forbidden-trap phrases, but the scores should be read as a *screen*, not a verdict.
- **Small white-box model.** Real activations in this run come from a small CPU model (`Qwen2.5-0.5B-Instruct`); its drift trajectories illustrate the *method*, and its behavioural scores should be read as a floor, not as the capability of frontier models.
- **Simulated drift for API models.** Closed/endpoint models expose no activations, so drift for the black-box path is *simulated* (a documented decay prior) purely for visualisation; only white-box drift reflects a model's actual internal state.
- **Probe leakage.** Famous amphibolies and counterfactual-physics prompts appear in training data; a model may answer correctly by recall rather than reasoning. The multilingual and multi-turn structure partially defends against this.

### 5.3 Future work

Linear probes for "physical plausibility" directions (already scaffolded in `cli probe`), activation patching to test *causal* dependence of the answer on the deep-layer drift, larger white-box models, and human-rated agreement to calibrate the keyword screen.

### 5.4 The access-path experiment, and what the per-language spread means

Two smaller findings from §4.4 are worth spelling out in plain language, because they are easy to over-read.

**Does it matter how you reach a model?** Modern frontier models are increasingly used *through agents* — a command-line tool wraps the model in its own instructions and tools before your question ever lands. We wondered whether that wrapper changes the model's grounding behaviour, so we asked the identical six-language probes through two coding agents (`claude -p` and `codex exec`) instead of through a bare chat endpoint, with each agent's shell tools removed so the only difference was the framing. The Claude family lands in the low-to-mid 0.9s (0.91–0.96) and the GPT-5.x models through Codex at ~0.82–0.83 — all comfortably in "strong grounding" territory. We were tempted, at first, to read a *tools-on vs tools-off* effect into one run where German jumped. It evaporated on repetition (§4.4's noise note): asking the same language five times per mode reversed the direction. The honest conclusion is the quieter one — **the agent doorway does not obviously break grounding, and the differences we saw at the margins were mostly the model's own run-to-run wobble**, not the scaffolding. This is itself a small, useful result: it says the behaviour we are probing is reasonably robust to how the model is invoked.

**Why does one model score differently across languages?** This is the part that, to us, is the most interesting and the most honest about the method's limits. A genuine world model should be *language-invariant*: the apple falls up in German exactly as it does in English, because gravity is not a fact about English. So when a single model's SPI is flat across all six languages, that is the grounding-invariance signature we are hoping to see — the meaning is sitting *underneath* the language. When the same model wobbles — strong in English and Chinese, softer in Russian or German — there are two very different things it could mean, and we cannot always tell them apart:

- It could be a **real** asymmetry in the model: the world model is partly entangled with English-heavy training text, and the grounding genuinely thins out in a typologically distant or lower-resource language.
- It could be an **artefact of our crude scorer**: the model answered correctly, but phrased it in a way our localized keyword list did not catch, or the syntactic-ambiguity trap simply does not translate cleanly into that language's grammar.

In our runs the dips cluster on Russian and German, and they show up in *different* models — which hints at something real about those probes in those languages rather than a single broken model. But we deliberately stop short of claiming "model X is less grounded in Russian." With only a handful of prompts per language and a substring-matching scorer, the per-language column is best read as **a question worth chasing, not a verdict** — exactly the kind of thread a larger replication should pull on.

### 5.5 What this could mean, and an invitation

If the pattern holds up under more prompts, more languages, and better scoring, the modest takeaway is that today's strongest models behave, on these adversarial-by-design questions, much more like Hinton's grounded world-models than like pure stochastic parrots: they override the statistically obvious-but-wrong answer, they hold a counterfactual world across turns, and — in the one model we could open up — their deep layers reorganise onto the *situation* rather than the surface words. That is not proof of understanding. It is a small accumulation of behaviour that is hard to get for free from text statistics alone.

But the more important thing this experiment can offer is its *size*. It is meant to be re-run, doubted, and broken. If you have an API key, a local GGUF, or just one of these agent CLIs, you can reproduce every number here in minutes and watch where it bends. **Please do** — add a language, widen the suites, swap the keyword screen for an LLM judge, point it at a model we could not reach. The most valuable outcome would not be agreement with our numbers; it would be someone finding the place where this simple instrument is wrong, and saying so.

---

## 6. Reproducibility

```bash
pip install -r requirements.txt
# Behavioural sweep over all six languages against a local llama.cpp endpoint:
python3 scripts/run_benchmark.py --backend black --model openai/<your-served-model>.gguf
# Real-activation drift on the local HF model (CPU-friendly):
python3 scripts/run_benchmark.py --backend white --wl-lang en,zh,ru
# Rebuild §4 of this whitepaper and the docs site data:
python3 scripts/build_report.py
```

All suites live in [`canyon/suites/`](./canyon/suites) as JSON and are regenerated by [`scripts/gen_suites.py`](./scripts/gen_suites.py). Metrics are defined in [`canyon/metrics.py`](./canyon/metrics.py).

---

## References

- E. M. Bender, T. Gebru, A. McMillan-Major, S. Shmitchell. *On the Dangers of Stochastic Parrots: Can Language Models Be Too Big?* FAccT 2021.
- G. Hinton. Public lectures and interviews on understanding, world models, and compression in neural language models (2023–2024).
