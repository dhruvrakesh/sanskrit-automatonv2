# sanskrit-automaton

A grow‑as‑you‑go pipeline for **Sanskrit analysis, entity extraction, and explainable translation**, 
inspired by the spirit of critical editions (e.g., **BORI**), translators like **Bibek Debroy** and **Manmatha Nath Dutt**, 
and grounded in **Pāṇini’s grammatical insights** through analyzers such as Sanskrit Heritage and `sanskrit_parser`.

> Goal: ingest Sanskrit texts; normalize → sandhi‑split → morphologically parse; identify **tribes/clans/places**; 
> translate with evidence; and continually improve via human review.

---

## Project layout

```
sanskrit-automaton/
├── README.md
├── requirements.txt
├── pyproject.toml            # optional, for poetry/pip if desired
├── LICENSE
├── configs/
│   ├── sources.yml
│   ├── translit.yml
│   └── mt.yml
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── seeds/seed_tribes_regions.jsonl
├── scripts/
│   ├── normalize_text.py         # danda/diacritics cleanup + transliteration
│   ├── sandhi_split.py           # sandhi splitting using sanskrit_parser
│   ├── morph_parse.py            # morphology; Heritage API (if set) or sanskrit_parser
│   ├── build_gazetteer.py        # scrape+merge proper names (MW/Heritage) → JSONL + GraphML
│   ├── ner_tag.py                # gazetteer-based NER (tribe/loc/etc.)
│   ├── infer_mt.py               # /translate backend with "explain" evidence (stub until model fine-tuned)
│   ├── train_mt.py               # IndicTrans2 fine-tune hooks (instructions + skeleton)
│   └── publish_api.py            # FastAPI: /analyze /entities /translate?explain=true + tiny web UI
├── webui/
│   └── static/ (index.html, app.js, style.css)
├── labelstudio_templates/
│   ├── segmentation_approval.xml
│   ├── sense_choice.xml
│   └── entity_correction.xml
└── tests/
    ├── test_normalize.py
    ├── test_sandhi_split.py
    └── test_morph_parse.py
```

### Upstream inspirations & sources

- **Sanskrit Heritage** (Gérard Huet): morphological analyzer & reader.  
- **sanskrit_parser** (Python): sandhi split + sentence/karaka analysis.  
- **Cologne Sanskrit Lexicon – Monier‑Williams**: https://www.sanskrit-lexicon.uni-koeln.de/  
- **BORI critical edition** references for Mahābhārata; **Debroy** and **Manmatha Nath Dutt** translations for cross‑checking renderings.  
- **Itihāsa parallel corpus** for Sanskrit↔English verse pairs (for fine‑tuning).  
- **IndicTrans2** model family for Indic MT with `san_Deva` support.

> ⚖️ **Licensing & ethics**: respect terms of each corpus/site (Cologne, Heritage, BORI, etc.). 
> The included scrapers are rate‑limited and optional; prefer using local, licensed dumps if available.

---

## Quickstart

1. **Install deps** (Python 3.10+ recommended):
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the API + tiny UI**:
   ```bash
   uvicorn scripts.publish_api:app --reload --port 8000
   # open http://localhost:8000
   ```

3. **CLI examples**:
   ```bash
   echo "धर्मक्षेत्रे कुरुक्षेत्रे..." | python scripts/normalize_text.py --from-script DEVANAGARI --to-script SLP1
   echo "धर्मक्षेत्रे कुरुक्षेत्रे..." | python scripts/sandhi_split.py
   echo "धर्मक्षेत्रे कुरुक्षेत्रे..." | python scripts/morph_parse.py
   ```

4. **Gazetteer build** (optional web fetch; see script header for notes):  
   ```bash
   python scripts/build_gazetteer.py --seed data/seeds/seed_tribes_regions.jsonl --out data/processed/gazetteer.jsonl
   ```

5. **Label Studio** templates are in `labelstudio_templates/` (import them in your LS project).

6. **Training MT** (instructions in `scripts/train_mt.py`): clone IndicTrans2 & prepare Itihāsa pairs, then run fine‑tuning. 
   The API will use your fine‑tuned checkpoint when placed as configured in `configs/mt.yml`.

---

## Paninian grounding & critical‑edition mindset

- Parsers are configured to **prefer grammatical well‑formedness** (Pāṇinian cues) and to expose **explanations** (chosen split, morphology, karaka edges).
- When translations are produced, the UI/API returns **evidence**: parse summary, glossary choices, and “near‑parallel” references if available.
- Where possible, cite **critical editions** (BORI for MBh etc.); the repo is structured to keep edition metadata alongside each text chunk (TEI/XML encouraged).

---

## Minimal warranty

This is a **starter**. Some functionality is stubbed (e.g., MT fine‑tune hooks) until you attach your models and datasets.
