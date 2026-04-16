# AI Real Estate Agent

> Describe a property in plain English — get a price estimate with a grounded explanation.

---

## Live Deployment

| Resource | URL |
|----------|-----|
| Frontend | https://real-estate-ui-green.vercel.app/ |
| API | https://real-estate-ai-64849588355.us-central1.run.app |
| API Docs (Swagger) | https://real-estate-ai-64849588355.us-central1.run.app/docs |

**Repositories:**
- Backend (this repo): https://github.com/amir-hilal/real-estate-ai
- Frontend: https://github.com/amir-hilal/real-estate-ui

---

## Deployment

### Backend — Google Cloud Run

The FastAPI backend is containerized with Docker and deployed to [Google Cloud Run](https://cloud.google.com/run) (us-central1). Cloud Run runs the container on demand, scales to zero when idle, and handles HTTPS termination automatically.

The Docker image is built from the `Dockerfile` in the repository root and the ML model artifact (`model.joblib`) is copied into the image at build time. Environment variables (Groq API key, CORS origin, etc.) are set as Cloud Run secrets/environment variables at deploy time.

### Frontend — Vercel

The React frontend is deployed to [Vercel](https://vercel.com/) via the [real-estate-ui](https://github.com/amir-hilal/real-estate-ui) repository. Vercel builds and deploys automatically on every push to the main branch. The `VITE_API_URL` environment variable is set in the Vercel project settings to point to the Cloud Run API URL.

---

## Getting Started — Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- [Ollama](https://ollama.com/) (for local LLM inference in development) **or** a [Groq](https://console.groq.com/) API key (for production mode)

---

### 1. Clone Both Repositories

```bash
git clone https://github.com/amir-hilal/real-estate-ai.git
git clone https://github.com/amir-hilal/real-estate-ui.git
```

---

### 2. Backend Setup

```bash
cd real-estate-ai

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
make install
# or: pip install -r requirements.txt
```

**Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and set the following:

```env
# Choose "development" (Ollama) or "production" (Groq)
ENVIRONMENT=development

# Development — Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=phi4-mini

# Production — Groq (hosted)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Frontend origin for CORS
CORS_ORIGIN=http://localhost:5173
```

**Pull the Ollama model (development mode only):**

```bash
ollama pull phi4-mini
```

**Start the API server:**

```bash
# Development (with auto-reload)
make serve

# Production mode (uses Groq)
make serve-prod
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

---

### 3. Frontend Setup

```bash
cd real-estate-ui
npm install
```

Create a `.env` file in the frontend root:

```env
VITE_API_URL=http://localhost:8000
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

### 4. Docker (Alternative to Manual Setup)

To run the backend with Docker:

```bash
cd real-estate-ai
cp .env.example .env   # fill in your values
docker-compose up --build
```

The API will be available at `http://localhost:8000`.

---

## Learning Goals

This project is explicitly designed for deep understanding. The goals are:

- Understand how an LLM can extract structured, validated data from free text through conversation
- Understand how to train, evaluate, and prevent leakage in an ML regression pipeline
- Understand how a second LLM call can produce grounded, data-informed explanations
- Understand how to serve ML and LLM components together through a REST API
- Understand how to containerize a multi-component AI system
- Build the discipline to document and plan before writing code
- Understand every tradeoff made — not just the outcome

---

## Project Scope

**In scope for MVP:**

- Conversational LLM interface that extracts property features turn-by-turn from natural language
- Feature validation and schema enforcement using Pydantic
- ML model trained on the Ames Housing dataset (scikit-learn regression pipeline)
- Price prediction from validated features once all required fields are collected
- LLM-generated prediction explanation grounded in training data statistics
- FastAPI backend with SSE streaming for the chat endpoint
- Docker-based containerization
- React frontend consuming the streaming chat API

**Not in scope for MVP (see `docs/context/future-considerations.md` for details):**

- Authentication or role-based access control
- Async/background task processing (Celery, Redis)
- Object storage (S3, MinIO)
- Multi-user or multi-agent architectures
- Real-time property search or external data integrations
- A/B testing of prompts or models
- Fine-tuning of the LLM
- Production SLA or scalability guarantees

---

## High-Level Architecture

The system is built around a **conversational pipeline**. The user interacts with an LLM-powered chat interface that progressively extracts the property features needed for prediction.

```
User Message + Conversation History + Accumulated Features
        │
        ▼
┌──────────────────────────────────────────┐
│  POST /chat  (FastAPI — SSE streaming)   │
│                                          │
│  1. Build system prompt with known /     │
│     missing feature context              │
│                                          │
│  2. LLM turn (non-streaming):            │
│     classify intent + extract features   │
│                                          │
│  3. Merge new features with accumulated  │
│     features from client state           │
│                                          │
│  4a. Required fields still missing?      │
│      → stream reply asking for them      │
│      → emit: token…, done                │
│                                          │
│  4b. All required fields present?        │
│      → run ML prediction (scikit-learn)  │
│      → stream explanation tokens (LLM)   │
│      → emit: features, prediction,       │
│              token…, done                │
└──────────────────────────────────────────┘
        │
        ▼
  SSE Event Stream to Client
  ┌──────────────────────────────┐
  │  { type: "features", ... }   │  ← extracted property data
  │  { type: "token", ... }      │  ← streaming LLM text
  │  { type: "prediction", ... } │  ← price + confidence
  │  { type: "done" }            │
  │  { type: "error", ... }      │
  └──────────────────────────────┘
```

**LLM providers:**
- `ENVIRONMENT=development` → [Ollama](https://ollama.com/) (local, no API key required)
- `ENVIRONMENT=production` → [Groq](https://console.groq.com/) (hosted, fast inference)

**Additional endpoints:**

| Endpoint | Purpose |
|----------|---------|
| `POST /chat` | Main conversational pipeline (SSE streaming) |
| `POST /extract` | Stage 1 only — extract features from a single text input |
| `POST /predict` | Stage 2+3 only — predict price from a validated feature set |
| `GET /insights` | Return training data summary statistics |
| `GET /versions` | List available prompt versions |
| `GET /health` | Liveness check — confirms model and stats are loaded |

---

## Repository Structure

```
real-estate-ai/
├── app/                               ← FastAPI application
│   ├── main.py                        ← App factory + lifespan (model loaded here)
│   ├── config.py                      ← Pydantic BaseSettings (env var config)
│   ├── constants.py                   ← Shared constants
│   ├── routes/                        ← Thin route handlers (no business logic)
│   │   ├── chat.py                    ← POST /chat — SSE streaming chat
│   │   ├── extract.py                 ← POST /extract — feature extraction only
│   │   ├── predict.py                 ← POST /predict — prediction + explanation
│   │   ├── insights.py                ← GET /insights — training stats
│   │   └── versions.py                ← GET /versions — prompt version list
│   ├── services/                      ← Pipeline stage implementations
│   │   ├── chat.py                    ← Conversational turn orchestration
│   │   ├── extraction.py              ← Stage 1: LLM feature extraction
│   │   ├── prediction.py              ← Stage 2: ML model inference
│   │   ├── explanation.py             ← Stage 3: LLM explanation generation
│   │   └── insights.py                ← Training stats loader
│   ├── schemas/                       ← Pydantic models
│   │   ├── property_features.py       ← PropertyFeatures schema (validated input)
│   │   ├── responses.py               ← API response models
│   │   └── chat.py                    ← ChatRequest / ChatMessage schemas
│   └── clients/
│       └── llm.py                     ← OpenAI-compatible LLM client wrapper
├── prompts/                           ← Versioned LLM prompt files
│   ├── v1/
│   │   ├── chat.md
│   │   ├── extraction.md
│   │   └── explanation.md
│   ├── v2/
│   │   ├── chat.md
│   │   └── explanation.md
│   └── v3/
│       ├── chat.md
│       └── explanation.md
├── ml/                                ← ML experimentation and artifacts
│   ├── eda.ipynb                      ← Exploratory data analysis
│   ├── model_training.ipynb           ← Model training and evaluation
│   ├── data/
│   │   └── ames.csv                   ← Ames Housing dataset
│   └── artifacts/
│       ├── model.joblib               ← Serialized scikit-learn pipeline
│       └── training_stats.json        ← Summary statistics for explanation context
├── tests/
│   ├── conftest.py
│   ├── test_routes.py
│   ├── test_extraction.py
│   ├── test_extraction_integration.py
│   ├── test_explanation.py
│   ├── test_explanation_integration.py
│   └── test_api_integration.py
├── docs/                              ← All project documentation
│   ├── overall_flow.md
│   ├── prompt-versions.md
│   ├── roadmap.md
│   ├── context/
│   │   ├── project-brief.md
│   │   ├── requirements.md
│   │   ├── assumptions-and-open-questions.md
│   │   └── future-considerations.md
│   ├── decisions/
│   │   └── architecture-decision-records.md
│   ├── phases/
│   │   └── phase-0X-*.md              ← Per-phase plans and checklists
│   ├── deployment/
│   │   ├── aws-guide.md
│   │   └── cloud-run-guide.md
│   └── status/
│       ├── current-status.md
│       └── progress-log.md
├── ui/                                ← Frontend placeholder (see real-estate-ui repo)
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt
└── .env.example
```
