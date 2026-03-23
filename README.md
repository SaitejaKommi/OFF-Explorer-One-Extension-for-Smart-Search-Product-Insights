# OFF Explorer – Unified Intelligent Food Discovery System

> **One browser extension, two powerful modes:** Semantic food search (P3) + Real-time product insights (P4) — integrated, bilingual (EN/FR), and fully offline-capable.

A unified browser extension for Open Food Facts that combines natural language semantic search with real-time product insights. Discover products using intuitive queries and get clear, explainable nutritional insights — all in one seamless experience.

---

## Architecture Overview

```
Browser Extension (Manifest V3)
    │
    ├── Search Mode (Popup)       → POST /search, /refine
    └── Insight Mode (Content)    → POST /product-insights
                │
                ▼
        FastAPI Backend
                │
        ┌───────┴────────────┐
        │                    │
   NLP Layer            Insight Engine
   intent_parser        risk/positive indicators
   taxonomy_mapper      NutriScore/NOVA explanations
   relaxation_engine    food pairings
   context_manager      alternatives ranking
        │
        ▼
     DuckDB ← OFF Parquet datasets
        │
   [Optional] Phi-3-mini via Ollama (local SLM)
```

### Component Interaction

| Layer | Files | Role |
|-------|-------|------|
| **Extension** | `extension/src/content/content.js` | Auto-detect product page, render insight panel |
| **Extension** | `extension/src/popup/popup.js` | Search UI, conversational refinement |
| **Extension** | `extension/src/background/background.js` | Session management, language detection |
| **API** | `backend/routers/search.py` | `POST /search` |
| **API** | `backend/routers/refine.py` | `POST /refine` (conversational) |
| **API** | `backend/routers/insights.py` | `POST /product-insights` |
| **NLP** | `backend/services/intent_parser.py` | Rule-based EN/FR query parsing |
| **NLP** | `backend/services/constraint_extractor.py` | Refinement merging |
| **NLP** | `backend/services/taxonomy_mapper.py` | OFF schema mapping + SQL generation |
| **Data** | `backend/services/duckdb_service.py` | DuckDB query execution over parquet |
| **Ranking** | `backend/services/ranking_engine.py` | Nutrient-weighted product scoring |
| **Relaxation** | `backend/services/relaxation_engine.py` | Stepwise constraint fallback |
| **Insights** | `backend/services/insight_engine.py` | Full rule-based insight generation |
| **Context** | `backend/services/context_manager.py` | Search→Insight continuity |
| **SLM** | `backend/services/ollama_service.py` | Optional Phi-3-mini enhancement |

---

## Repository Structure

```
.
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings + feature flags
│   ├── requirements.txt
│   ├── models/
│   │   └── schemas.py             # Pydantic models
│   ├── routers/
│   │   ├── search.py              # POST /search
│   │   ├── refine.py              # POST /refine
│   │   └── insights.py            # POST /product-insights
│   └── services/
│       ├── intent_parser.py       # EN/FR NL query parser
│       ├── constraint_extractor.py
│       ├── taxonomy_mapper.py     # OFF schema mapper
│       ├── duckdb_service.py      # DuckDB query engine
│       ├── relaxation_engine.py   # Stepwise fallback
│       ├── ranking_engine.py      # Nutrient-weighted ranking
│       ├── insight_engine.py      # Rule-based insights
│       ├── context_manager.py     # Session continuity
│       └── ollama_service.py      # Optional SLM (Phi-3-mini)
├── extension/
│   ├── manifest.json              # MV3 manifest
│   ├── popup.html                 # Search mode UI
│   └── src/
│       ├── api/api-client.js      # Backend API client
│       ├── background/background.js
│       ├── content/content.js     # Insight panel (product pages)
│       ├── popup/popup.js         # Search mode controller
│       └── styles/
│           ├── popup.css
│           └── panel.css
├── data/
│   └── README.md                  # Dataset download instructions
├── tests/
│   ├── conftest.py
│   ├── test_intent_parser.py      # EN + FR + edge cases
│   ├── test_taxonomy_mapper.py
│   ├── test_insight_engine.py
│   ├── test_ranking_engine.py
│   ├── test_relaxation_engine.py
│   └── test_api.py                # FastAPI endpoint tests
├── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for extension development, optional)
- [Ollama](https://ollama.ai) (optional, for SLM enhancement)

### 1. Backend Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Download OFF parquet data (see data/README.md)

# Start the server
uvicorn backend.main:app --reload
# => http://localhost:8000
# => http://localhost:8000/docs  (Swagger UI)
```

### 2. Docker (recommended)

```bash
# Basic (no SLM)
docker-compose up backend

# With Phi-3-mini SLM
SLM_ENABLED=true docker-compose --profile slm up
# Then pull the model:
docker exec -it <ollama_container> ollama pull phi3:mini
```

### 3. Extension Setup

1. Open `chrome://extensions` (or `edge://extensions`)
2. Enable **Developer Mode**
3. Click **Load unpacked** → select the `extension/` directory
4. The extension icon appears in the toolbar

---

## Features

### Search Mode (P3)

Natural language product search with explainable results:

```
Query: "low sugar vegan snacks under 200 calories"
=> Parsed: category=snacks, dietary=[vegan], sugars<5g, energy<200kcal
=> Results ranked by nutrient score
=> Explanation: "sugars: 3.2/5.0 ✓, vegan ✓, calories: 180/200 ✓"
```

**Conversational refinement:**
```
"now only gluten-free"       => adds en:gluten-free filter
"which has more protein?"    => re-ranks by protein content
```

**Constraint relaxation** (when 0 results):
1. Drop dietary tags (least specific first)
2. Relax numeric thresholds +/-20%
3. Drop category filters

### Insight Mode (P4)

Auto-activates on Open Food Facts product pages:

- Rule-based health summary
- Risk indicators (high sugar, high salt, ultra-processed)
- Positive indicators (high fiber, high protein, low sodium)
- NutriScore + NOVA explanations
- Weighted alternatives (sugars x0.30 + fat x0.20 + salt x0.15 + protein x0.20 + fiber x0.15)
- Food pairings (rule-based + optional SLM)
- Daily-use recommendations

### Bilingual Support

Auto-detects language from URL:
- `ca.openfoodfacts.org` → English
- `fr.openfoodfacts.org` → French

French query example:
```
"collations véganes à faible teneur en sucre moins de 200 calories"
```

---

## Configuration

Create a `.env` file in the project root:

```env
# Data
PARQUET_GLOB=data/*.parquet

# SLM (optional)
SLM_ENABLED=false
SLM_MODEL=phi3:mini
OLLAMA_BASE_URL=http://localhost:11434

# Server
DEBUG=false
PORT=8000
```

---

## Running Tests

```bash
# Install test dependencies
pip install -r backend/requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_intent_parser.py -v
pytest tests/test_insight_engine.py -v
pytest tests/test_api.py -v
```

---

## Security & Privacy

- No external API calls in production – all processing is local
- No user data stored – sessions are ephemeral (in-memory, 1-hour TTL)
- SQL injection prevention – all DuckDB field names are validated against a whitelist; barcodes are sanitised to digits only
- SLM is opt-in – disabled by default; uses local Ollama only

---

## Sample Query Flow

```
User types: "low sugar vegan snacks under 200 calories"
    |
    v
IntentParser.parse()
    => categories: [en:snacks]
    => dietary_tags: [en:vegan]
    => constraints: [sugars_100g < 5.0, energy_kcal_100g < 200]
    |
    v
TaxonomyMapper.validate() + build_conditions()
    => SQL WHERE clauses
    |
    v
DuckDBService.execute_search()
    => Raw rows from parquet
    |
    v (if 0 results)
RelaxationEngine.apply_with_fallback()
    => Drop dietary tag => relax threshold => drop category
    |
    v
RankingEngine.rank()
    => Scored ProductResult list
    |
    v
ContextManager.update_intent()   <- stores for Search->Insight continuity
    |
    v
User clicks product => content.js detects barcode
    |
    v
POST /product-insights { barcode, session_id }
    |
    v
InsightEngine.generate()
    => health_summary, risk_indicators, positive_indicators
    => nutriscore_explanation, nova_explanation
    => alternatives (ranked), food_pairings, recommendations
    => context_highlights (from search intent)
    |
    v [optional]
OllamaService.enhance_*()
    => enriched summary, SLM pairings, SLM recommendations
    |
    v
Panel rendered in sidebar on OFF product page
```

---

## Contributing

This project is part of Google Summer of Code for Open Food Facts Canada.
See the [Open Food Facts wiki](https://wiki.openfoodfacts.org/Google_Summer_of_Code) for contribution guidelines.
