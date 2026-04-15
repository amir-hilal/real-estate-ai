# Future Considerations: Post-MVP Architecture

> **Purpose:** Separate what was built in MVP from what belongs in future phases.  
> **Status:** Sections 2–4 are **Planned — Next Phase**. Sections 1, 5–9 remain Post-MVP.  
> **Why this file exists:** To prevent scope creep by giving future ideas a home outside the active plan.

---

## The Core Principle

> Add complexity only when a specific, named problem demands it.

Items in this document were deliberately excluded from MVP. With MVP complete and cloud deployment decided (ADR-011), three items now have concrete justification and are promoted to **Planned — Next Phase**: GCS storage, Keycloak auth, and agent/customer role separation.

The remaining items stay Post-MVP until a specific, recurring, named problem demands them.

---

## 1. Async / Background Task Processing

### Status: **Post-MVP — Not Planned**

### What it means
Instead of running the full pipeline synchronously inside a single HTTP request, work would be dispatched to a background worker (Celery + Redis). The client receives a job ID and polls for the result.

### Why it is not needed
The system uses SSE streaming for all user-facing interactions (`POST /chat`). Each chat turn is a single LLM call (2–5s) that streams tokens back immediately — there is no long-running job to background. The prediction trigger on the final turn adds ML inference (instant) + explanation streaming (5–10s of streamed tokens), but the user sees content within 2–3s.

Celery/Redis would add two new services with no benefit:
- Chat turns are short-lived HTTP connections, not backgroundable jobs
- FastAPI's async event loop already handles concurrent I/O-bound LLM calls
- SSE requires an open HTTP connection — incompatible with fire-and-forget task dispatch
- The complexity cost (broker configuration, task retry logic, polling endpoints, worker containers) is not justified by any current or near-term problem

### Signal to revisit
- Sustained >20 concurrent users causing request queuing (measure first)
- Long-running batch jobs (e.g., model retraining) needed alongside live serving
- Non-interactive bulk operations (e.g., CSV batch analysis) requested

---

## 2. Object Storage (Google Cloud Storage)

### Status: **Planned — Next Phase**

### What it means
Instead of storing the serialized model artifact and training statistics file inside the Docker image, they are stored in a Google Cloud Storage (GCS) bucket. The application downloads them at startup.

### Why it was not in MVP
For one model serving one user locally, the filesystem was perfectly adequate. GCS adds IAM, bucket policies, and SDK configuration.

### Why it is needed now
With Cloud Run deployment (ADR-011), the model artifact is COPY'd into the Docker image at build time. This means:
- Every model update requires a full Docker image rebuild and redeploy
- Multiple Cloud Run instances each carry a ~50MB model file in their image
- No model versioning — rollback requires redeploying a previous image tag

GCS solves these problems:
- **Model versioning** — upload new `model.joblib` to GCS with a version key; roll back by pointing to a previous version
- **Decoupled deployment** — update the model without rebuilding the Docker image
- **Shared storage** — multiple Cloud Run instances pull the same artifact
- **Future: retraining pipeline** — new model artifacts land in GCS automatically

### Why GCS over S3
The project runs on Google Cloud (Cloud Run — ADR-011). Using GCS keeps everything in the same ecosystem:
- Cloud Run's default service account has GCS access with no extra configuration
- No cross-cloud IAM or networking needed
- `google-cloud-storage` Python SDK is lightweight (~5MB vs. boto3's ~70MB)
- GCS free tier: 5GB storage, 5K Class A operations/month, 50K Class B operations/month

### Implementation plan
1. Create a GCS bucket (e.g., `real-estate-ai-artifacts`)
2. Upload `model.joblib` and `training_stats.json` to GCS
3. Add `google-cloud-storage` to `requirements.txt`
4. Modify `app/main.py` lifespan to download from GCS if `MODEL_SOURCE=gcs` env var is set (local filesystem remains the default for development)
5. Add `GCS_BUCKET`, `GCS_MODEL_KEY`, `GCS_STATS_KEY` to `app/config.py`
6. Remove `COPY ml/artifacts/` from Dockerfile (only when GCS is the production default)
7. IAM: Cloud Run service account gets `storage.objectViewer` role on the bucket (default service account may already have this)
8. Add ADR documenting the decision

---

## 3. Authentication and Authorization (RBAC)

### Status: **Planned — Next Phase**

### What it means
- User login and session management (JWT tokens, OAuth2 / OpenID Connect)
- Role-based access control: two roles with different capabilities
- Token validation middleware in FastAPI protecting all endpoints except `/health`

### The stack
- **Keycloak** as the identity provider (self-hosted or managed)
  - Handles user registration, login, password reset, OAuth2 flows
  - Issues JWT tokens with role claims (`realm_roles: ["user", "agent"]`)
- **FastAPI middleware** validates the JWT on every request
- **Role extraction** from the token determines prompt version and response content

### Why it was not in MVP
There was one user: the developer running the system locally. Authentication added complexity that protected nothing.

### Why it is needed now
With cloud deployment and role-specific features (Section 4), the system needs:
- **Identity** — know who is making requests
- **Authorization** — agents see different content than regular users
- **Security** — the public API must not be open to anonymous traffic
- **Rate limiting foundation** — per-user limits require knowing the user

### Implementation plan
1. Add Keycloak container to `docker-compose.yml` (dev) or use a managed instance (prod)
2. Configure a `real-estate-ai` realm with two roles: `user` and `agent`
3. Add `python-jose` or `PyJWT` to `requirements.txt` for token validation
4. Create `app/middleware/auth.py` — decode JWT, extract `user_id` and `roles`, attach to request state
5. Add `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID` to `app/config.py`
6. Protect all endpoints except `GET /health` — return 401 for missing/invalid tokens
7. Pass `role` to the chat and prediction services so they can select the appropriate prompt version
8. Frontend: add login flow (Keycloak JS adapter or redirect-based OAuth2)
9. Add ADR documenting the decision

---

## 4. Agent vs. Customer Role Separation

### Status: **Planned — Next Phase** (depends on Section 3: Keycloak)

### What it means
Two distinct personas use the system differently:

**Regular User (`user` role):**
- Describes a property, gets a price prediction and explanation
- Same experience as the current MVP chat flow
- No additional content beyond prediction + explanation

**Real Estate Agent (`agent` role):**
- Same prediction pipeline, but the **explanation prompt** is swapped to an agent-specific version
- The agent version includes additional sections that the regular user does not see:
  - **Investment insight** — how the agent could profit from properties at this price point (undervalued indicators, renovation ROI potential, rental yield estimate based on price-to-neighborhood-median ratio)
  - **Selling guide** — practical advice on positioning this property to a specific buyer profile (first-time buyer, investor, family) based on the extracted features (lot size, bedrooms, neighborhood tier)
  - **Comparable context** — more detailed statistical comparisons (not just median, but percentile rank within the neighborhood)
- No extra questions are asked — the same features drive both versions
- The role is determined from the JWT token, not from user input

### Prompt versioning strategy

The current prompt structure already supports this:

```
prompts/
├── chat_v2.md                    ← shared (intent classification + extraction)
├── extraction_v1.md              ← shared (standalone extraction)
├── explanation_v1.md             ← current: regular user explanation
├── explanation_agent_v1.md       ← NEW: agent-specific explanation
└── explanation_agent_v1.md       ← includes investment + selling sections
```

- `chat_v2.md` and `extraction_v1.md` are **role-agnostic** — extraction is the same for everyone
- `explanation_v1.md` stays unchanged for regular users
- `explanation_agent_v1.md` extends the base explanation with agent-only sections
- The service layer selects the prompt based on `role` from the request context:
  ```python
  prompt_file = "explanation_agent_v1.md" if role == "agent" else "explanation_v1.md"
  ```

### Implementation plan
1. Create `prompts/explanation_agent_v1.md` — same grounding rules as `explanation_v1.md` + investment insight + selling guide sections
2. Modify `app/services/explanation.py` to accept a `role` parameter and load the corresponding prompt
3. Modify `app/services/chat.py` to pass the role through to the explanation stage
4. Modify route handlers to extract role from the JWT (set by auth middleware)
5. Frontend: display agent-specific sections with distinct styling (e.g., a "Professional Insights" card)
6. Add integration tests for both prompt versions
7. Update `docs/prompt-versions.md` with the agent prompt entry

### Why no extra questions for agents
The features needed for prediction are identical regardless of role. The difference is entirely in **output** — what the LLM writes in the explanation. The agent prompt simply has additional instructions that say: *"In addition to the standard explanation, provide investment and selling guidance based on the features and prediction."* The same `training_stats.json` context grounds both versions.

---

## 5. Messaging Architecture (Event-Driven Design)

### What it means
Instead of direct function calls between components, stages publish and subscribe to events via a message bus (Redis Pub/Sub, Kafka, RabbitMQ). Example: Stage 1 completion emits a `FeaturesExtracted` event; the ML model consumes it; completion emits a `PredictionComplete` event; Stage 2 consumes that.

### Why it is not in MVP
This introduces:
- Message schema design and evolution
- Producer/consumer coordination and failure handling
- A fundamentally different debugging mental model

For a three-stage sequential pipeline with one user, this solves no real problem. It would be a architecture demonstration, not a solution to an actual constraint.

### Signal to add it
- The pipeline needs to fan out to multiple consumers (e.g., logging service, audit trail, notification service)
- Stages need to be independently scalable
- Reliability guarantees (at-least-once delivery, exactly-once) are required

---

## 6. Fine-Tuning the LLM

### What it means
Instead of relying on a general-purpose LLM with in-context prompting, fine-tune a model (or a smaller open-source model) specifically on real estate property descriptions → structured feature extraction pairs.

### Why it is not in MVP
- Requires a labeled training dataset of property descriptions paired with ground-truth feature extractions
- Requires significant compute and fine-tuning infrastructure
- General-purpose LLMs with well-designed prompts already perform well on structured extraction tasks
- The prompting approach is easier to iterate, version, and debug

### Signal to add it
- Prompt-based extraction has a documented error rate >10% on real production traffic
- A labeled dataset of property descriptions has been collected
- Cost of LLM API calls is prohibitive and a smaller fine-tuned model would reduce it

---

## 7. Continuous Learning / Online Retraining

### What it means
The ML model is periodically retrained on new data (e.g., new property sales added to the training set). A pipeline automatically retrains, evaluates, and promotes the new model if it beats the current one.

### Why it is not in MVP
- There is no new data source — the Ames dataset is static
- Model lifecycle management requires experiment tracking (MLflow), model registry, and deployment automation
- This is an MLOps concern, not an ML modeling concern

### Signal to add it
- A live data pipeline feeds new labeled examples to the system
- Model performance degrades measurably over time (concept drift)
- Business stakeholders require freshness guarantees

---

## 8. Experiment Tracking (MLflow, Weights & Biases)

### What it means
Systematically log model training runs: hyperparameters, dataset version, metrics, artifacts. Compare runs visually. Register the best model.

### Why it is not in MVP
For one model trained once on one dataset, a documented Jupyter notebook is a perfectly adequate experiment log. MLflow adds operational overhead without adding clarity at this stage.

### Signal to add it
- More than 3 meaningful model variants are being compared
- Team members need to reproduce or compare each other's runs
- Hyperparameter tuning is being automated

---

## 9. API Gateway and Multi-Service Architecture

### What it means
Each pipeline component (extraction service, prediction service, explanation service) is a separate deployed microservice. An API gateway routes requests and aggregates responses.

### Why it is not in MVP
- Three services where one will do
- Network hops between services add latency and failure surfaces
- Each service requires its own Docker image, health check, deployment config, and inter-service auth

### Signal to add it
- Individual stages have dramatically different scaling requirements (e.g., ML inference is CPU-bound, LLM calls are I/O-bound)
- Teams own different services independently
- Independent deployability of stages is required

---

## Summary Table

| Feature | Status | Trigger / Rationale |
|---------|--------|---------------------|
| Async background tasks (Celery + Redis) | Post-MVP | Not needed — SSE streaming is real-time, FastAPI async handles concurrency |
| Object storage (GCS) | **Planned — Next Phase** | Model versioning, decouple deployment from artifact, shared storage across Cloud Run instances |
| Auth & RBAC (Keycloak) | **Planned — Next Phase** | Public API security, role-based prompt selection, rate limiting foundation |
| Role separation (agent/customer) | **Planned — Next Phase** | Agent-specific explanation prompts (investment insight + selling guide) |
| Messaging / event bus | Post-MVP | Fan-out, independent scaling, reliability SLAs |
| LLM fine-tuning | Post-MVP | >10% prompt extraction error rate, labeled data |
| Continuous retraining | Post-MVP | Live data pipeline, measurable concept drift |
| Experiment tracking (MLflow) | Post-MVP | >3 model variants, team collaboration |
| Microservice architecture | Post-MVP | Independent scaling, separate team ownership |

---

---

## 10. Cloud Deployment (Google Cloud Run + Vercel)

### Status: Decided (ADR-011, supersedes ADR-010)

This item has been promoted from future consideration to an active decision:

- **API:** Google Cloud Run — Docker container with `ENVIRONMENT=production` (Groq LLM), auto-scales to zero, free tier
- **Frontend:** Vercel — static React app with `VITE_API_URL` pointing to the Cloud Run service URL
- **Guide:** `docs/deployment/cloud-run-guide.md`
- **Previous:** AWS guide preserved at `docs/deployment/aws-guide.md` for reference (ADR-010, superseded)

This is no longer a future consideration — it is the deployment architecture.

---

*The best system for learning and MVP delivery is the simplest one that works. Complexity should be earned, not assumed.*
