# InterDevResearch

InterDevResearch is a multi-iteration research codebase exploring ontology-driven interfaces and LLM assistance for discovery, curation, and submission of impact-evaluation evidence.

The repository contains three versions of the same core system (`Iteration1` to `Iteration3`) and a separate cross-domain prototype for digital-library book discovery (`cross_domain_evaluation`).

## What Is In This Repo

- ERCT ontology artifacts (`.owl`, WIDOCO docs, JSON-LD, Turtle, N-Triples)
- RDF mapping pipelines (R2RML/RML)
- Flask APIs for SPARQL-backed retrieval and submission workflows
- React/Vite interfaces for trial exploration and curation
- A Vue/Vite cross-domain conversational prototype
- Evaluation instruments and response datasets across iterations

## Repository Layout

- `Iteration1/`
  - `interDev1/`: baseline prototype (React + Flask + GraphDB)
  - `mappings/`: ERCT V3 R2RML mapping + ingestion script
  - `eval/`: iteration 1 study files
- `Iteration2/`
  - `interDev2/`: expanded collection workflow + AI-assisted submission
  - `mappings/`: ERCT V4 R2RML mapping + ingestion script
  - `data/r2rml/`: normalized CSV sources for mapping
  - `eval/`: iteration 2 study files
- `Iteration3/`
  - `interDev3/`: participant-conditioned chat modes, semantic search, event logging
  - `mappings/`: ERCT V5 R2RML mapping + ingestion script
  - `data/r2rml/`: normalized CSV sources for mapping
  - `eval/`: iteration 3 study protocol/questionnaire/data
- `cross_domain_evaluation/`
  - `implementation/`: Vue conversational library explorer
  - `eval/`: cross-domain evaluation dataset
- `data/`
  - `merged_3ie_aer.csv`: merged source CSV used in mapping workflows

## Iteration Summary

| Iteration | Ontology Artifact | Main Additions                                                                                                       |
| --------- | ----------------- | -------------------------------------------------------------------------------------------------------------------- |
| 1         | `ERCT V3.owl`     | Baseline browse/filter/detail and collection workflows                                                               |
| 2         | `ERCT V4.owl`     | Expanded collections, PDF upload, LLM-assisted RDF extraction/submission                                             |
| 3         | `ERCT V5.owl`     | Participant assignment (`none/chat/chat-sources`), cited chat mode, semantic retrieval cache, detailed event logging |

Ontology docs are generated under each iteration's `docs/widoco/` directory.

## Recommended Starting Point

Start with **Iteration 3** unless you explicitly need historical behavior from earlier iterations.

## Quick Start (Iteration 3)

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- GraphDB running with ERCT trial data loaded

### 1) Backend

```bash
cd Iteration3/interDev3/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Additional runtime deps imported by app/routes.py but not pinned in requirements.txt
pip install python-dotenv rdflib pdfminer.six openai anthropic google-generativeai
```

Create `Iteration3/interDev3/backend/app/.env`:

```env
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
CLAUDE_API_KEY=...
GRAPHDB_SPARQL_ENDPOINT=http://localhost:7200/repositories/erct

# Optional tuning
# GRAPHDB_LUCENE_CONNECTOR=
# SPARQL_QUERY_TIMEOUT=45
# SPARQL_QUERY_MAX_RETRIES=3
# SEMANTIC_SEARCH_MIN_SCORE=0.2
# SEMANTIC_SEARCH_TOP_K=60
# SEMANTIC_SEARCH_MAX_TRIALS=300
```

Run the API:

```bash
python app.py
```

Backend listens on `http://127.0.0.1:5000`.

### 2) Frontend

```bash
cd Iteration3/interDev3/interface/interface
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:5000` by default.

## Rebuilding RDF From CSV (Iteration 3 Mapping)

Use this when you want to regenerate mapped RDF from tabular inputs.

```bash
pip install morph-kgc rdflib requests
python3 Iteration3/mappings/ingest_erct_v5_r2rml.py \
  --input-csv data/merged_3ie_aer.csv \
  --mapping Iteration3/mappings/erct_v5_r2rml.ttl \
  --sources-dir Iteration3/data/r2rml \
  --output Iteration3/interDev3/mapped_data_r2rml.ttl \
  --start-year 2015 \
  --end-year 2024
```

Notes:

- `--prepare-only` generates normalized CSV source tables without materializing RDF.

## Running Other Iterations

### Iteration 1

- Backend: `Iteration1/interDev1/backend/`
- Frontend: `Iteration1/interDev1/interface/interface/`
- Uses older baseline behavior and integration assumptions.

### Iteration 2

- Backend: `Iteration2/interDev2/backend/`
- Frontend: `Iteration2/interDev2/interface/interface/`
- Includes AI-assisted ingestion/submission extensions.

## Cross-Domain Prototype

Location: `cross_domain_evaluation/implementation/`

- Frontend (Vue + Vite):

```bash
cd cross_domain_evaluation/implementation
npm install
npm run dev
```

- Local JSON storage backend (port `2600`):

```bash
cd cross_domain_evaluation/implementation/backend_temp_for_books_storage
npm install
node server.js
```

- Optional local Gutendex/LLM backend:
  - Code: `cross_domain_evaluation/implementation/gutget/app.py`
  - Defaults to Flask port `5000`
  - Requires environment variables such as `OPENAI_API_KEY` and `REQUIRED_API_KEY`
  - To use it from local frontend dev, update `/api` proxy target in `cross_domain_evaluation/implementation/vite.config.ts`

## Caveats

- This is a research snapshot, not a production repo
