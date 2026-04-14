# Future Considerations: Post-MVP Architecture

> **Purpose:** Clearly separate what is in scope for MVP from what belongs in a future version.  
> **Rule:** Nothing in this document is allowed to influence Phase 0–7 implementation.  
> **Why this file exists:** To prevent scope creep by giving future ideas a home outside the active plan.

---

## The Core Principle

> Add complexity only when a specific, named problem demands it.

Every item in this document was deliberately excluded from MVP. The reason is not that these ideas are bad — it is that they solve problems we do not yet have. Adding them before those problems exist produces systems that are harder to understand, harder to debug, and harder to change.

The signal to revisit any item below is: *"We have a specific, recurring, named problem that this solution would fix."* Not: *"This would be cool"* or *"Production systems usually have this."*

---

## 1. Async / Background Task Processing

### What it means
Instead of running the full pipeline (LLM extraction → ML prediction → LLM explanation) synchronously inside a single HTTP request, the work would be dispatched to a background worker. The client receives a job ID immediately and polls for the result.

### The typical stack
- **Celery** as the distributed task queue
- **Redis** as the message broker (queues tasks) and result backend (stores results)
- A worker process separate from the API server
- A polling or webhook mechanism for the frontend

### Why it is not in MVP
The full pipeline takes approximately 3–8 seconds. This is acceptable for a demonstration system and for learning. Async infrastructure adds:
- Two new services to configure and debug (Celery + Redis)
- Complex failure handling (task retries, timeouts, dead letter queues)
- New concepts (message brokers, worker concurrency) that distract from the core ML/LLM learning goals

### Signal to add it
- A user submits a request and the UI becomes unresponsive for >10 seconds routinely
- Multiple concurrent users exist and requests are queuing
- Long-running batch jobs (e.g., re-training) are needed alongside real-time serving

---

## 2. Object Storage (S3, MinIO)

### What it means
Instead of storing the serialized model artifact and training statistics file on the local filesystem (or inside the Docker image), they would be stored in an object storage bucket (AWS S3, Google Cloud Storage, or self-hosted MinIO). The application would download them at startup or reference them by URL.

### Why it is not in MVP
For one model serving one user locally:
- The filesystem is perfectly adequate
- S3 adds IAM, bucket policies, network dependencies, and SDK configuration
- None of those problems exist yet

### Signal to add it
- The model artifact needs to be versioned and shared across multiple server instances
- Model retraining produces new artifacts that need to be promoted through an environment pipeline
- The system is deployed to the cloud and cannot rely on local disk

---

## 3. Authentication and Authorization (RBAC)

### What it means
- User login and session management (JWT tokens, OAuth2 flows)
- Role-based access control: different permissions for different roles
- The suggestion below about agent vs. customer separation implies distinct roles

### The likely future stack
- **Keycloak** as the identity provider (handles OAuth2, OpenID Connect, user management)
- Token validation middleware in FastAPI
- Role claims embedded in JWT tokens

### Why it is not in MVP
There is one user: the developer running the system locally. Authentication:
- Adds an entire auth service to stand up
- Requires token flows, session handling, and protected route middleware
- Protects nothing until multiple users or sensitive data exist

### Signal to add it
- The system is deployed beyond a local machine
- Multiple users with different permissions need access
- User-submitted property data is considered sensitive and must be protected

---

## 4. Agent vs. Customer Role Separation

### What it means
In a real estate context, there are at least two personas:
- **Agent:** A licensed real estate professional who uses the system to assist clients
- **Customer/Buyer:** A consumer exploring property values independently

These roles have different access levels, different UI needs, and potentially different business logic (e.g., agents see model confidence, customers see only the explanation).

### Why it is not in MVP
There is one persona in MVP: a developer or tester sending a property description. Role separation requires:
- Auth (see above)
- UI personalization
- Business logic branching by role
- None of which is validated as necessary yet

### Signal to add it
- Real users with real professional contexts are using the system
- Role-specific features are requested by name
- Auth infrastructure is already in place

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

| Feature | Status | Trigger to Add |
|---------|--------|----------------|
| Async background tasks (Celery + Redis) | Post-MVP | >10s latency, concurrent users, batch jobs |
| Object storage (S3/MinIO) | Post-MVP | Multi-instance deployment, model versioning |
| Auth & RBAC (Keycloak) | Post-MVP | Real external users, sensitive data |
| Role separation (agent/customer) | Post-MVP | Auth in place, role-specific features requested |
| Messaging / event bus | Post-MVP | Fan-out, independent scaling, reliability SLAs |
| LLM fine-tuning | Post-MVP | >10% prompt extraction error rate, labeled data |
| Continuous retraining | Post-MVP | Live data pipeline, measurable concept drift |
| Experiment tracking (MLflow) | Post-MVP | >3 model variants, team collaboration |
| Microservice architecture | Post-MVP | Independent scaling, separate team ownership |

---

*The best system for learning and MVP delivery is the simplest one that works. Complexity should be earned, not assumed.*
