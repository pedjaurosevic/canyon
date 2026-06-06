# CANYON: Framework za mehanističku i bihevioralnu evaluaciju semantičkog utemeljenja LLM-ova

`CANYON` je open-source istraživački harness i benchmark alat dizajniran za testiranje hipoteze Geoffreya Hintona o funkcionalnom razumevanju i unutrašnjim modelima sveta kod velikih jezičkih modela (LLM). Nazvan po poznatom Hintonovom primeru sa Velikim kanjonom, ovaj alat ima za cilj da razlikuje puko statističko nadovezivanje reči ("stohastički papagaj") od dinamičkog semantičkog utemeljenja (*semantic grounding*).

Ovaj dokument definiše arhitekturu, module, metriku i faze razvoja projekta prilagođenog za rad u Linux okruženju sa lokalnim modelima (poput Gemma 4 12b) i eksternim API-jevima.

---

## 1. Osnovni arhitektonski moduli

Projekt je podeljen na tri nezavisna ali komplementarna sloja:

```
              +---------------------------------------+
              |         CANYON CLI / TUI              |
              +---------------------------------------+
                                  |
        +-------------------------+-------------------------+
        |                                                   |
        v                                                   v
+-----------------------+                           +-----------------------+
|   Sloj Evaluacije     |                           |    Sloj Akvizicije    |
|   (Bihevioralni)      |                           |    (Mehanistički)     |
+-----------------------+                           +-----------------------+
| - Kontrafaktički test |                           | - HF Transformers     |
| - Amfibolije (Canyon) |                           | - Kuke za Hidden State|
| - Složeni humor       |                           | - Linear Probing      |
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

### 1.1. Bihevioralni modul ("Black-Box")
Testira model kroz specifično dizajnirane prompt sekvence koje krše uobičajene statističke distribucije na kojima su modeli trenirani.
* **The Canyon Suite (Sintaksičke zamke):** Rečenice sa semantičkom dvosmislenošću koje zahtevaju poznavanje fizike sveta da bi se rešile (npr. provera da li model shvata promenu subjekta u rečenici "Gledao sam Veliki kanjon leteći za Čikago").
* **The Counterfactual Physics Suite (Plastičnost sveta):** Generisanje svetova sa izmenjenim aksiomima (npr. gravitacija koja gura nagore, vreme koje teče unazad). Prati se sposobnost modela da zadrži konzistentnost kroz dug dijalog unutar izmenjenog koordinatnog sistema.
* **The Oxymoron Suite (Slojeviti humor):** Testiranje prepoznavanja višeslojnih konceptualnih paradoksa, metafora i igara reči koji se ne mogu dešifrovati površinskim rečničkim definicijama.

### 1.2. Mehanistički modul ("White-Box")
Ekskluzivno za lokalne modele (Gemma 4, Llama 3, Qwen) preko `transformers` ili `vLLM` biblioteka.
* **Activation Tracker:** Registruje i čuva aktivacione vektore kroz središnje i poslednje slojeve mreže tokom generisanja svakog tokena.
* **Semantic Drift Probe:** Meri geometrijsku distancu (Cosine Similarity/Euclidean Distance) u latentnom prostoru između ključnih koncepata pre i nakon što korisnik ispravi kontekstualnu grešku modela.
* **Linear Classifier Probes:** Omogućava korisniku da istrenira mini-regresione modele nad skrivenim stanjima kako bi se utvrdilo da li unutar slojeva postoji reprezentacija "istinitosti" ili "fizičke mogućnosti" pre nego što model uopšte ispiše tekst.

### 1.3. Core & API Sloj
* Integracija sa `LiteLLM` ruterom kako bi se bihevioralni testovi mogli bez napora izvršavati na lokalnim Ollama/vLLM instancama ili eksternim API-jevima (Anthropic, OpenAI, Groq).

---

## 2. Metrike i Evaluacija (The Stochastic Parrot Index)

Umesto klasičnih Accuracy/F1 skorova, `CANYON` uvodi tri specifične metričke ose:

1.  **Counterfactual Plasticity (CP-Score):** Sposobnost održavanja izmenjenih zakona logike/fizike. Meri se procenat skretanja modela nazad u "normalne" statističke šablone tokom konverzacije.
2.  **Contextual Realignment (CR-Score):** Brzina i geometrijska oštrina kojom model menja svoja unutrašnja stanja kada mu se ukaže na implicitnu grešku (re-grounding).
3.  **Semantic Invariance (SI-Score):** Stabilnost apstraktne reprezentacije humora ili logičkog problema kada se isti prompt parafrazira, prevede na drugi jezik ili provuče kroz žargon.

---

## 3. Plan Implementacije po Fazama

### Faza 1: Arhitektura baze i CLI (MVP)
* [ ] Postavljanje strukture projekta i konfiguracionog sistema (`config.yaml`).
* [ ] Razvoj core CLI interfejsa za terminal.
* [ ] Integracija `LiteLLM` sloja za univerzalno slanje promptova.
* [ ] Kreiranje prve verzije bihevioralnih testova (JSON format sa sekvencama koraka).

### Faza 2: Mehanistička instrumentacija (Samo za lokalne modele)
* [ ] Implementacija kuka (*hooks*) za ekstrakciju skrivenih stanja (`hidden_states`) iz Hugging Face modela.
* [ ] Optimizacija za lokalni **Gemma 4 12b** model (mapiranje slojeva, bfloat16 podrška).
* [ ] Razvoj matematičkog modula za praćenje trajektorije vektora kroz slojeve tokom dijaloga.

### Faza 3: Metrics Engine & Analitika
* [ ] Razvoj algoritama za izračunavanje CP, CR i SI skorova.
* [ ] Automatizovano generisanje Markdown izveštaja sa detaljnim tabelama i uvidima.
* [ ] Implementacija bazičnih vizuelnih prikaza vektorskog pomeranja unutar terminala (TUI grafikoni).

### Faza 4: Open-Source Paketiranje i Ekstenzije
* [ ] Pakovanje alata kao instalabilnog Python paketa (`pip install canyon-bench`).
* [ ] Dodavanje podrške za Ollama lokalne endpointove.
* [ ] Otvaranje repozitorijuma za zajednicu kako bi istraživači mogli da doprinose svojim "zamkama" i test-scenarijima.

---

## 4. Predložena struktura repozitorijuma

```text
canyon/
│
├── canyon/
│   ├── __init__.py
│   ├── cli.py              # CLI komande i argumenti
│   ├── engine.py           # Glavni orkestrator testova
│   │
│   ├── providers/          # Podrška za različite backend-ove
│   │   ├── __init__.py
│   │   ├── local_hf.py     # White-box rad sa lokalnim Transformers modelima
│   │   └── api_router.py   # Black-box rad preko LiteLLM-a
│   │
│   ├── suites/             # Test scenariji
│   │   ├── canyon_core.json
│   │   ├── counterfactuals.json
│   │   └── humor_paradox.json
│   │
│   └── metrics.py          # Proračun Stochastic Parrot Indeksa
│
├── tests/                  # Unit testovi za framework
├── config.example.yaml     # Primer konfiguracionog fajla
├── requirements.txt
├── README.md
└── PLAN.md                 # Ovaj fajl
```

---

## 5. Tehnološki Stack

* **Jezik:** Python 3.10+
* **ML Biblioteke:** `torch`, `transformers`, `accelerate` (za lokalno čupanje aktivacija sa Gemme 4)
* **API Ruter:** `litellm`
* **Terminal UI:** `rich` / `click` (za čist, moderan CLI ispis sa tabelama i bojama)
* **Konfiguracija:** `pyyaml`
