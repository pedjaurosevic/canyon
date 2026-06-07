# CANYON: A framework for mechanistic and behavioural evaluation of semantic grounding in LLMs

`CANYON` is an open-source research harness and benchmark designed to test Geoffrey Hinton's hypothesis about functional understanding and internal world models in large language models (LLMs). Named after Hinton's well-known Grand Canyon example, the tool aims to distinguish mere statistical word-stitching ("stochastic parrot") from dynamic *semantic grounding*.

This document defines the architecture, modules, metrics, and development phases of the project, tailored to run on Linux with local models (such as Gemma 4 12b) and external APIs.

---

## 1. Core architectural modules

The project is split into three independent but complementary layers:

```
              +---------------------------------------+
              |         CANYON CLI / TUI              |
              +---------------------------------------+
                                  |
        +-------------------------+-------------------------+
        |                                                   |
        v                                                   v
+-----------------------+                           +-----------------------+
|   Evaluation Layer    |                           |   Acquisition Layer   |
|    (Behavioural)      |                           |    (Mechanistic)      |
+-----------------------+                           +-----------------------+
| - Counterfactual test |                           | - HF Transformers     |
| - Amphiboly (Canyon)  |                           | - Hidden-state hooks  |
| - Layered humour      |                           | - Linear probing      |
+-----------------------+                           +-----------------------+
|                                                   |
+-------------------------+-------------------------+
                          |
                          v
            +---------------------------+
            |      Metrics Engine       |
            | (Stochastic Parrot Index) |
            +---------------------------+
```

### 1.1. Behavioural module ("black-box")
Probes the model through specifically designed prompt sequences that violate the usual statistical distributions the models were trained on.
* **The Canyon Suite (syntactic traps):** Sentences with semantic ambiguity that require world-physics knowledge to resolve (e.g. checking whether the model understands the change of subject in "I watched the Grand Canyon flying to Chicago").
* **The Counterfactual Physics Suite (world plasticity):** Generating worlds with altered axioms (e.g. gravity that pushes upward, time that flows backward). We track the model's ability to stay consistent across a long dialogue inside the altered coordinate system.
* **The Oxymoron Suite (layered humour):** Testing recognition of multi-layered conceptual paradoxes, metaphors, and wordplay that cannot be decoded from surface dictionary definitions.

### 1.2. Mechanistic module ("white-box")
Exclusively for local models (Gemma 4, Llama 3, Qwen) via the `transformers` or `vLLM` libraries.
* **Activation Tracker:** Registers and stores activation vectors across the middle and final layers of the network during the generation of each token.
* **Semantic Drift Probe:** Measures the geometric distance (cosine similarity / Euclidean distance) in latent space between key concepts before and after the user corrects a contextual mistake of the model.
* **Linear Classifier Probes:** Lets the user train mini regression models over hidden states to determine whether a representation of "truth" or "physical plausibility" exists inside the layers before the model emits any text at all.

### 1.3. Core & API layer
* Integration with the `LiteLLM` router so behavioural tests can run effortlessly against local Ollama/vLLM instances or external APIs (Anthropic, OpenAI, Groq).

---

## 2. Metrics and evaluation (The Stochastic Parrot Index)

Instead of classic accuracy/F1 scores, `CANYON` introduces three specific metric axes:

1.  **Counterfactual Plasticity (CP-Score):** The ability to maintain altered laws of logic/physics. We measure the rate at which the model slips back into "normal" statistical patterns during the conversation.
2.  **Contextual Realignment (CR-Score):** The speed and geometric sharpness with which the model changes its internal states when pointed at an implicit error (re-grounding).
3.  **Semantic Invariance (SI-Score):** The stability of the abstract representation of humour or a logical problem when the same prompt is paraphrased, translated into another language, or pushed through slang.

---

## 3. Phased implementation plan

### Phase 1: Base architecture and CLI (MVP)
* [ ] Set up the project structure and configuration system (`config.yaml`).
* [ ] Develop the core CLI for the terminal.
* [ ] Integrate the `LiteLLM` layer for universal prompt dispatch.
* [ ] Create the first version of the behavioural tests (JSON format with step sequences).

### Phase 2: Mechanistic instrumentation (local models only)
* [ ] Implement hooks to extract hidden states (`hidden_states`) from Hugging Face models.
* [ ] Optimise for the local **Gemma 4 12b** model (layer mapping, bfloat16 support).
* [ ] Build the math module that tracks the trajectory of vectors across layers during a dialogue.

### Phase 3: Metrics Engine & analytics
* [ ] Develop the algorithms for computing the CP, CR, and SI scores.
* [ ] Automated generation of Markdown reports with detailed tables and insights.
* [ ] Implement basic visualisations of vector movement inside the terminal (TUI charts).

### Phase 4: Open-source packaging and extensions
* [ ] Package the tool as an installable Python package (`pip install canyon-bench`).
* [ ] Add support for Ollama local endpoints.
* [ ] Open the repository to the community so researchers can contribute their own "traps" and test scenarios.

---

## 4. Proposed repository structure

```text
canyon/
│
├── canyon/
│   ├── __init__.py
│   ├── cli.py              # CLI commands and arguments
│   ├── engine.py           # Main test orchestrator
│   │
│   ├── providers/          # Support for different backends
│   │   ├── __init__.py
│   │   ├── local_hf.py     # White-box work with local Transformers models
│   │   └── api_router.py   # Black-box work via LiteLLM
│   │
│   ├── suites/             # Test scenarios
│   │   ├── canyon_core.json
│   │   ├── counterfactuals.json
│   │   └── humor_paradox.json
│   │
│   └── metrics.py          # Stochastic Parrot Index computation
│
├── tests/                  # Unit tests for the framework
├── config.example.yaml     # Example configuration file
├── requirements.txt
├── README.md
└── PLAN.md                 # This file
```

---

## 5. Technology stack

* **Language:** Python 3.10+
* **ML libraries:** `torch`, `transformers`, `accelerate` (for pulling activations locally from Gemma 4)
* **API router:** `litellm`
* **Terminal UI:** `rich` / `click` (for clean, modern CLI output with tables and colour)
* **Configuration:** `pyyaml`
