# ITDB Fact‑Sheet Analyzer

A **Streamlit** application that lets you _chat with_ IAEA ITDB fact‑sheet PDFs.
Upload a sheet, extract structured JSON, ask free‑form questions, download CSV,
and visualise key metrics — all powered by **Azure OpenAI**, **LangChain**, and
**FAISS**.

---

##  Features & User Stories

| # | Capability | Key User Stories |
|---|------------|-----------------|
| 1 | **PDF upload & raw‑text preview** | US1.1&nbsp;US1.2 |
| 2 | **Structured‑data extraction (JSON ↔ table)** | US2.1‑2.3 |
| 3 | **Data export (CSV / JSON copy)** | US3.1‑3.2 |
| 4 | **Natural‑language Q&A (RAG)** | US4.1‑4.3 |
| 5 | **Quick visualisations** | US5.1‑5.2 |
| 6 | **Session memory / reset** | US6.1‑6.2 |

---

##  Quick Start

```bash
# 1 · Clone
git clone https://github.com/your‑org/itdb_fact_sheet_analyzer.git
cd itdb_fact_sheet_analyzer

# 2 · Python ≥ 3.9 virtual env
python -m venv .venv
source .venv/bin/activate      # Windows → .venv\Scripts\activate

# 3 · Install dependencies
pip install -r requirements.txt

# 4 · Create .env  (see next section)

# 5 · Run Streamlit
streamlit run app.py
```

Visit **<http://localhost:8501>** in your browser.

---

##  Environment Variables (.env)

```env
# -------- Chat model (GPT‑4o mini) --------
OPENAI_API_KEY=...
OPENAI_API_ENDPOINT=https://<resource>.openai.azure.com/
OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# -------- Embedding model (text‑embedding‑ada‑002) --------
OPENAI_EMBEDDING_API_KEY=...
OPENAI_EMBEDDING_ENDPOINT=https://<resource>.openai.azure.com/
OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# -------- Common --------
OPENAI_API_VERSION=2025-01-01-preview
```

> **Tip:** `az cognitiveservices account keys list -n <resource>` to fetch keys.

---

## 🛠 Development

| Task | Command |
|------|---------|
| Run tests | `pytest tests/` |
| Lint & format | `ruff .` |
| Auto‑reload | Streamlit hot‑reloads on file save |

---

## Deploy Options

| Platform | How |
|----------|-----|
| **Azure App Service** | use `azure‑webapp.yml` GitHub Action |
| **Streamlit Community Cloud** | “New app” → `app.py` |
| **Docker Compose** | `docker compose up --build` |

---

##  Contributing

1. **Fork** & create a feature branch  
2. `pre‑commit install`  
3. Open a PR — CI runs tests & lint automatically.

---

##  License

MIT
