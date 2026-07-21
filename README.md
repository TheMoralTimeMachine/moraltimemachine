# Moral Time Machine

BSc thesis project by Emir Berat Kir and Timur Cenk Kaya.

## Running locally

1.  Copy environment variables

    cp .env.example .env

2.  Add API keys to `.env`

        ANTHROPIC_API_KEY=...
        OPENAI_API_KEY=...

    To run against the included study database, also set
    `MTM_DB_PATH=db.sqlite3`.

3.  Build the retrieval index (embeds `rag/chunks.json` into a local Chroma index)

    uv sync --extra backend
    uv run python -m rag.indexer

4.  Start the app

        docker compose up --build

    Or without Docker: `make dev` (backend on :8080, frontend on :5173).

The grounding corpus ships as `rag/chunks.json`. The source papers it was
chunked from are published, copyrighted works and are not redistributed here;
they are cited in the thesis.

## Evaluation instruments and data

- Questionnaire items: `frontend/src/lib/questionnaire.ts`
- Figure/data analysis script: `paper/figures/make_results_figures.py`
- Anonymized study database: `db.sqlite3`

To reproduce the figures and statistics reported in the thesis (no API keys needed):

    uv sync --extra figures
    uv run python paper/figures/make_results_figures.py

This reads `db.sqlite3` and writes `likert-distribution.pdf` and
`participants-overview.pdf` to `paper/figures/`, printing the summary
statistics used in the results section.

## Privacy note

The public database contains only anonymized/pseudonymized study data.
Prolific IDs, names, email addresses, and direct identifiers are not included.
