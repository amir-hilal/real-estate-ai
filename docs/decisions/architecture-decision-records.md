# Architecture Decision Records

> **Format:** Lightweight ADR — each decision is recorded when made and never deleted.  
> **Rule:** Superseded decisions are marked `Superseded by ADR-XXX`, not removed.  
> **Why this document exists:** Decisions made in moments of clarity must survive moments of confusion.

---

## ADR Template

Use this template for every new entry:

```
---
### ADR-XXX — [Title]

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Superseded by ADR-XXX | Deprecated  
**Decided by:** [Person or team]

#### Context
What situation or constraint led to this decision? What were the competing options?

#### Decision
What was decided? State it clearly and specifically.

#### Consequences
What becomes easier, harder, or different as a result of this decision?
What are the known tradeoffs?
What is explicitly out of scope as a result?
```

---

## ADR-001 — Documentation-First Planning Before Any Implementation

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
It is tempting to begin an ML/LLM project by writing code immediately — load the dataset, train a quick model, write a prompt, and iterate from there. This approach optimizes for immediate visible output.

However, this project has multiple interacting stages (LLM extraction → schema validation → ML prediction → LLM explanation → API → UI). Decisions made early in one stage have downstream consequences in all others. For example: the choice of features in Phase 1 determines the Pydantic schema in Phase 3 and the explanation context in Phase 4. Without planning, these dependencies are discovered by breaking things, not by reasoning about them.

The project also has an explicit learning goal: understanding every decision. Documentation-first planning forces decisions to be made consciously and recorded before implementation makes them feel inevitable.

**Considered options:**
1. Code-first: write code, document later
2. Documentation-first: plan and document, then implement
3. Hybrid: plan only the current phase before starting it

#### Decision
The project will follow a documentation-first approach for all phases. Each phase document must be written, reviewed, and its exit criteria defined before any implementation in that phase begins.

For Phase 1 (EDA), a notebook is the implementation at that stage — but the phase document must define objectives, checklist, and exit criteria before the notebook is opened.

#### Consequences
- Slower initial visible progress (no code for the first days/weeks)
- Significantly lower risk of fundamental redesign mid-implementation
- Every decision has a written rationale before it is encoded in code
- New contributors (or future-you) can understand every choice without reading code
- Planning documents become the acceptance criteria, reducing ambiguity

---

## ADR-002 — Synchronous Request Handling for MVP

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
The full pipeline (Stage 1 LLM + ML inference + Stage 2 LLM) is expected to take 3–8 seconds end-to-end. There are two architectural patterns for handling this:

1. **Synchronous:** The HTTP request waits for the full pipeline to complete and returns the result. Simple to implement and debug.
2. **Asynchronous:** The request returns a job ID immediately; the client polls for results or receives a webhook. Requires a task queue (Celery), message broker (Redis), and additional infrastructure.

#### Decision
MVP will use synchronous request handling. The full pipeline runs within a single HTTP request/response cycle.

Accepted tradeoffs:
- Web server workers are held during LLM calls (I/O bound; acceptable with async FastAPI)
- Perceived latency is 3–8 seconds (acceptable for a demo system)
- If a user closes the browser, the pipeline continues running in the background (no cancellation mechanism)

#### Consequences
- Async infrastructure (Celery, Redis, polling endpoints) is explicitly excluded from MVP
- Latency is accepted as a known constraint, not a bug
- Any server timeout must be set to at least 30 seconds to avoid request cutoff during LLM calls
- If production requirements ever include >10 concurrent users or <3s response time SLAs, this decision must be revisited

---

## ADR-003 — Authentication and Background Jobs Excluded from MVP

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
Production systems of this type eventually need user authentication (who is using the system?), authorization (what are they allowed to do?), and background processing (handling multiple users without blocking). These are real requirements in production, but the question is when to introduce them.

**Authentication requirements in MVP:**
- There is exactly one user: the developer
- No sensitive data is stored
- The system runs locally, not on a shared server
- No access control boundaries exist

**Background job requirements in MVP:**
- Expected concurrency: 1 request at a time
- No batch processing pipeline
- No long-running retraining jobs

#### Decision
Authentication, authorization, and background job processing (Celery, Redis, task queues) are excluded from MVP scope entirely.

Auth will be revisited when:
- The system is deployed to a shared or public environment, OR
- User-specific data needs to be protected or separated

Background processing will be revisited when:
- Sustained concurrent usage at >5 requests/minute is observed, OR
- Batch retraining jobs are needed alongside live serving

#### Consequences
- MVP API is fully open — no API keys, no JWT tokens, no user sessions
- Any call to the API succeeds regardless of caller identity
- This is explicitly a security debt, documented and accepted for MVP
- All future-architecture notes on auth and async are in `docs/context/future-considerations.md`

---

## ADR-004 — Form-Based UI Before Chat-First UI

**Date:** 2026-04-14  
**Status:** Superseded by ADR-008  
**Decided by:** Project lead

#### Context
The primary input mechanism for this system is a natural-language property description. This could be implemented as:

1. **Chat UI:** A conversational interface where the user types, the system responds, asks follow-up questions, and iteratively builds the feature set through dialogue
2. **Form-based UI:** A text area for the description, with a structured fallback form for missing fields

A chat interface feels more natural for LLM-driven products and aligns with consumer familiarity with tools like ChatGPT. However, it introduces significant engineering complexity that is not justified at MVP stage.

**Reasons a chat interface is premature for MVP:**
- Requires managing conversation state (history, turn tracking, context window)
- The missing-field collection flow becomes an LLM-driven conversation instead of a simple form — requiring additional prompt engineering for the collection phase itself
- Results (a numeric prediction + 3 paragraphs) are awkward to display inline in a chat thread
- A form-based UI can be built significantly faster, allowing focus on the ML/LLM pipeline which is the learning priority
- The pipeline does not yet have a proven extraction error rate — it is unknown whether conversational clarification is even necessary

#### Decision
MVP UI will be form-based: a text area for the description, and a structured form for any missing required fields. Chat interface is a post-MVP consideration.

#### Consequences
- UI implementation time is significantly reduced
- Missing-field collection is handled through standard HTML form controls, not through conversational back-and-forth
- The decision can be revisited after Phase 3 testing reveals how often required fields are actually missing
- If the missing-field rate is very high (>50% of requests), a chat interface may become justified

---

## ADR-005 — Ames Housing Dataset as Training Data

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
A property price prediction model requires labeled training data: properties with known sale prices. Options considered:

1. **Ames Housing dataset:** ~2,900 rows, 79 features, residential sales in Ames, Iowa (2006–2010). Well-documented, widely used in ML education, free to use.
2. **Zillow / real MLS data:** Real production data; not freely available; licensing restrictions; would require web scraping or API access
3. **Synthetic data:** Generated artificially; does not reflect real market dynamics; useless for a realistic prediction task

**Reasons for Ames:**
- Free, publicly available, well-documented
- Rich enough (79 features) to require real feature selection and engineering decisions
- Standard enough that public benchmarks exist (useful for sanity-checking metrics)
- Realistic enough to demonstrate a working prediction system

**Limitations acknowledged:**
- Small dataset by modern standards (~2,900 rows)
- Data is from 2006–2010 in one city — predictions are not generalizable to current real estate
- Some features (e.g., `OverallQual`, assessor-specific ratings) are not naturally describable by a user
- Missing values in the dataset are semantically meaningful (not random) — requires careful imputation

#### Decision
Ames Housing dataset is the chosen training dataset for MVP.

#### Consequences
- The `PropertyFeatures` schema will be based on Ames column definitions
- Predictions will always be anchored to 2006–2010 Ames, Iowa pricing — this must be disclosed in the UI
- ML metrics should be compared against public Ames benchmarks for sanity checking
- If the project later requires a more modern or geographically diverse dataset, the schema and model must both be rebuilt

---

*New ADR entries must be added before any decision is implemented in code. A decision implemented without a record is undocumented technical debt.*

---

## ADR-006 — LightGBM as Final ML Model

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
Phase 2 required selecting a regression model for Ames Housing price prediction. The model must work with 12 features (4 required + 8 optional), handle mixed numeric/categorical inputs via a scikit-learn Pipeline, and beat the DummyRegressor baseline (MAE = $59,568) by at least 30%.

**Alternatives considered:**
1. **Ridge Regression** — fast, interpretable, but linear only; cannot capture the non-linear neighborhood and quality interactions visible in EDA
2. **Random Forest** — non-linear, robust; generally slightly worse than gradient-boosted trees on structured tabular data
3. **XGBoost** — strong candidate; similar performance profile to LightGBM but slower training on small datasets
4. **LightGBM** — gradient-boosted trees optimized for speed; native categorical support (not used here due to Pipeline constraints, but available for future work)

#### Decision
LightGBM (`LGBMRegressor`) is the final model. Parameters: `n_estimators=500, learning_rate=0.05, num_leaves=31, random_state=42`.

Test-set results: MAE = $17,936 (69.9% improvement over baseline), RMSE = $29,238, R² = 0.8885. All Phase 2 targets exceeded.

#### Consequences
- `lightgbm` is a required dependency (must be pinned in `requirements.txt`)
- Model is serialized as part of an `sklearn.Pipeline` via `joblib` — LightGBM version must be consistent between training and inference environments
- Train/test MAE gap is 72% ($5,029 vs $17,936) — acceptable overfitting for MVP; regularization can be explored post-MVP if needed
- `OverallQual` dominates feature importance (gain ~875) — the model is heavily dependent on this single feature

---

## ADR-007 — Ollama (Development) + Groq (Production) as LLM Providers

**Date:** 2026-04-14  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
The pipeline requires two LLM calls per request: Stage 1 (feature extraction) and Stage 3 (explanation generation). A provider must be chosen for development and production use.

**Alternatives considered:**
1. **OpenAI (GPT-4o)** — highest quality; expensive per-call; requires API key for all environments including development
2. **Anthropic (Claude)** — comparable quality; same cost and key-dependency issues as OpenAI
3. **Ollama (local)** — free, no API key, runs locally, good for development iteration; limited model quality for small models; latency depends on hardware
4. **Groq** — hosted inference with very fast response times; free tier available; supports Llama 3.3 70B and other open models; OpenAI-compatible API

**Key insight:** Both Ollama and Groq expose OpenAI-compatible REST APIs. The `openai` Python SDK works with both by changing only `base_url` and `api_key`. This means the same client code serves both environments with zero code branching.

#### Decision
- **Development:** Ollama with `phi4-mini` (local, free, no API key required)
- **Production:** Groq with `llama-3.3-70b-versatile` (hosted, fast inference, OpenAI-compatible)
- Environment selection via `ENVIRONMENT` variable (`development` | `production`)
- Client code uses the `openai` Python SDK with environment-dependent `base_url`

#### Consequences
- No OpenAI or Anthropic dependency or cost — significant simplification
- Development can proceed without any API key (Ollama is local and free)
- B-02 blocker (LLM API key) is resolved for development; Groq key needed only for production deployment
- Prompt quality may differ between `phi4-mini` (3.8B params) and `llama-3.3-70b` — prompts must be tested on both
- The `openai` Python package is still a dependency (used as a universal client), but OpenAI's API is not called
- If Groq's free tier is insufficient for production, switching to another OpenAI-compatible provider (Together AI, Fireworks, etc.) requires only changing env vars

---

## ADR-008 — Conversational Chat UI Supersedes Form-Based UI

**Date:** 2026-04-15  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
ADR-004 chose a form-based UI on the grounds that the pipeline was not yet proven and that a chat interface would require significant additional engineering before the core system was validated. By Phase 6, those conditions have changed:

1. **Pipeline proven.** Phases 1–5 are complete. Extraction, prediction, and explanation all work end-to-end in Docker.
2. **Missing fields are common.** Testing confirmed that most natural-language descriptions leave at least one required field (`OverallQual` or `GrLivArea`) null. The form-based fallback is needed in almost every interaction — making it the primary UX, not a fallback.
3. **A form cannot handle arbitrary input.** A user greeting ("Hello"), a question ("What makes a property more valuable?"), or an irrelevant message causes the form-based UI to return an error card. This is a poor experience that a chat model handles naturally.
4. **Streaming is the right fix for perceived latency.** The 10-20 second LLM explanation wait cannot be fixed by spinners — it requires streaming. Streaming belongs in a conversational UI, not a single-page form.

**Options considered:**
1. **Keep form-based UI, add graceful error handling for non-property input** — patching symptoms; does not solve the missing-field conversation loop
2. **Add a pre-check LLM call before the form** — doubles LLM calls; still doesn't produce a natural experience
3. **Full conversational chat UI with `POST /chat` SSE endpoint** — handles all input types, streams explanation, accumulates features naturally across turns

#### Decision
Replace the form-based UI with a conversational chat interface. The `POST /chat` endpoint accepts any user message plus conversation history and accumulated features, routes intent via an LLM call, and streams the result. The existing `POST /predict` endpoint is unchanged.

#### Consequences
- The partial form-based UI (exit criteria 1, 3, 5, 6, 7 verified) is replaced entirely — no prior work carries forward to the new exit criteria
- A new prompt file is required (`prompts/chat_v1.md`) covering combined intent classification + extraction
- Frontend state management is more complex: `messages[]`, `accumulatedFeatures{}`, and streaming buffer all tracked in React state
- The `/predict` endpoint and all its tests remain untouched — `/chat` is additive
- Phase 6b (streaming explanation) is merged into Phase 6 — it is no longer a separate phase but an integral part of the chat endpoint

---

## ADR-009 — Standalone React Frontend Replaces Embedded HTML

**Date:** 2026-04-15  
**Status:** Accepted  
**Decided by:** Project lead

#### Context
ADR-008 chose a conversational chat UI with token-by-token streaming of the explanation. The initial implementation embedded the frontend as a single `app/static/index.html` file using React 18 + Babel Standalone (in-browser JSX transpilation) + Tailwind Play CDN, served directly by the FastAPI backend via `GET /`.

This approach failed to deliver token-by-token streaming despite multiple fix attempts:

1. **`flushSync` did not work.** React 18's automatic batching groups all `setState` calls within a microtask. Even with `flushSync`, the browser did not paint between token updates because the JS call stack did not unwind between iterations of the SSE event processing loop.
2. **`requestAnimationFrame` yields were added.** An `await yieldToBrowser()` (double-rAF) pattern was inserted between token events. This approach is architecturally correct, but Babel Standalone's in-browser transpilation changes how async generators interact with React's scheduler, preventing reliable frame-by-frame rendering.
3. **Backend confirmed working.** A vanilla JS debug page (`debug-stream.html`) with direct DOM writes (`element.textContent = ...`) showed perfect token-by-token rendering. Every `event: token` SSE event arrived individually with correct timing. The problem is exclusively in the React CDN frontend layer.

The root cause: Babel Standalone transpiles JSX at runtime in the browser, producing code that does not match the assumptions of React 18's concurrent features and batching behavior. A proper build step (Vite/webpack) produces optimized output where these patterns work as documented.

**Options considered:**
1. **Keep Babel Standalone, work around batching** — Multiple workarounds attempted (`flushSync`, `requestAnimationFrame` yields, `setTimeout(0)`). None produced reliable per-token rendering. The in-browser transpiler is fundamentally incompatible with the required rendering behavior.
2. **Switch to vanilla JS (no React)** — The debug page proved this works. However, managing a chat thread with state (messages, accumulated features, streaming text, prediction cards) without a framework produces brittle, hard-to-maintain code.
3. **Standalone React app with Vite build** — Proper build step produces standard React 18 output. Streaming patterns work as documented. TypeScript adds type safety. The app runs independently and communicates with the backend via `POST /chat`.

#### Decision
Extract the frontend to a standalone React application built with Vite + React 18 + TypeScript + plain CSS. The app lives in a separate directory outside the FastAPI project. The FastAPI backend becomes a pure API server — `app/routes/ui.py`, `app/static/`, and all HTML-serving code are removed. CORS middleware is added to the backend to allow cross-origin requests from the frontend dev server.

#### Consequences
- Token-by-token streaming will work reliably with a proper React 18 build
- The frontend and backend are decoupled — they can be developed, tested, and deployed independently
- CORS middleware must be added to the FastAPI backend (new `cors_origin` setting)
- The Docker setup changes: either the frontend is built and served by a static file server (nginx), or the backend proxies it — this is a deployment decision for Phase 7
- `GET /` no longer serves the UI from the FastAPI backend — the API root returns the health endpoint or OpenAPI docs
- The frontend is a separate codebase with its own `package.json`, `tsconfig.json`, and `vite.config.ts`
- No npm or Node.js dependencies are added to the Python backend project
