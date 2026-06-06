# CANYON 🏜️
### Framework za mehanističku i bihevioralnu evaluaciju semantičkog utemeljenja LLM-ova

`CANYON` je open-source istraživački harness i benchmark alat dizajniran za testiranje hipoteze Geoffreya Hintona o funkcionalnom razumevanju i unutrašnjim modelima sveta kod velikih jezičkih modela (LLM). Nazvan po poznatom Hintonovom primeru sa Velikim kanjonom, ovaj alat ima za cilj da razlikuje puko statističko nadovezivanje reči ("stohastički papagaj") od dinamičkog semantičkog utemeljenja (*semantic grounding*).

---

## 🚀 Ključne karakteristike

- **Bihevioralna evaluacija (Black-Box):** Testiranje kroz semantičke zamke, kontrafaktičku fiziku (svetovi sa obrnutim zakonima gravitacije/vremena) i prepoznavanje humora/paradoksa preko `LiteLLM` integracije.
- **Mehanistička evaluacija (White-Box):** Direktno sondiranje skrivenih stanja (*hidden states*) i neurona lokalnih modela (npr. Gemma, Llama, Qwen) pomoću PyTorch forward hooks.
- **Linear Probing:** Mogućnost treniranja linearnih klasifikatora (Logistic Regression) nad aktivacijama slojeva modela kako bi se otkrilo postojanje unutrašnjih koncepata o fizičkoj mogućnosti.
- **Prelep TUI (Terminal UI):** Moderan, interaktivan ispis grafikona i tabela sa metrikama u terminalu preko `rich` biblioteke.

---

## 🛠️ Instalacija

1. Klonirajte repozitorijum:
   ```bash
   git clone https://github.com/pedjaurosevic/canyon.git
   cd canyon
   ```

2. Instalirajte zavisnosti:
   ```bash
   pip install -r requirements.txt
   ```

3. Instalirajte paket u razvojnom režimu:
   ```bash
   pip install -e .
   ```

---

## ⚙️ Konfiguracija

Podesite modele i parametre u `config.yaml` (napravite kopiju od `config.example.yaml`):

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

## 💻 Korišćenje (TUI / CLI)

### 1. Pokretanje kompletnog benchmarka (LiteLLM / API)
```bash
python -m canyon.cli run --config config.example.yaml --model gpt-4o
```

### 2. Izlistavanje dostupnih test-scenarija (Suites)
```bash
python -m canyon.cli list-suites
```

### 3. Pokretanje linear probing-a nad skrivenim stanjima lokalnog modela
```bash
python -m canyon.cli probe --layer 12 --config config.example.yaml
```

### 4. Multilingvalno pokretanje (EN, ZH, JA, RU, DE, ES)
Suite-ovi postoje na 6 jezika (`<suite>_<lang>.json`), uz srpski original kao referencu:
```bash
# jedan jezik preko lokalnog llama.cpp endpointa
python -m canyon.cli run --lang en --model openai/<served-model>.gguf
```

---

## 🌍 Multilingvalni benchmark i izveštaj

```bash
# Bihevioralni sweep kroz svih 6 jezika (black-box, llama.cpp endpoint)
python3 scripts/run_benchmark.py --backend black --model openai/<served-model>.gguf

# Realne aktivacije + drift na lokalnom HF modelu (CPU)
python3 scripts/run_benchmark.py --backend white --wl-lang en,zh,ru

# Generisanje §4 whitepaper-a i podataka za sajt iz results/
python3 scripts/build_report.py
```

- 📄 **Whitepaper:** [`WHITEPAPER.md`](./WHITEPAPER.md) — hipoteza, metodologija (CP/CR/SI/SPI), latent-space drift, rezultati po jezicima.
- 🌐 **GitHub Pages sajt:** [`docs/`](./docs) — interaktivne tabele SPI benchmarka i SVG drift grafovi.
- 🧪 **Suite-ovi:** [`canyon/suites/`](./canyon/suites) (regeneracija: `python3 scripts/gen_suites.py`).

---

## 📊 Stochastic Parrot Index (SPI)

Rezultat testiranja se izražava kroz tri specifične metričke ose:
1. **Counterfactual Plasticity (CP-Score):** Sposobnost modela da dosledno razmišlja unutar izmenjenih zakona logike ili fizike.
2. **Contextual Realignment (CR-Score):** Brzina i geometrijska oštrina kojom model menja svoja unutrašnja stanja kada mu se ukaže na implicitnu grešku.
3. **Semantic Invariance (SI-Score):** Stabilnost apstraktne reprezentacije problema pri parafraziranju ili prevodu.

Zajedno, ove ose formiraju **Stochastic Parrot Index (SPI)** koji klasifikuje model kao:
- **Strong Grounding (World Model)** (SPI >= 0.75)
- **Weak Grounding (Hybrid)** (SPI >= 0.50)
- **Stochastic Parrot** (SPI < 0.50)

---

## 🤝 Doprinos

Projekat je u potpunosti otvoren za zajednicu! Slobodno dodajte nove test scenarije u `canyon/suites/` ili proširite mehanističke provajdere.
