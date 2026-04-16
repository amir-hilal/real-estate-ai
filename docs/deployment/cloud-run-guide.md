# Google Cloud Run Deployment Guide — FastAPI Docker Container

> **Purpose:** Step-by-step guide to deploy the real-estate-ai API to Google Cloud Run.  
> **Audience:** Developer who has tested the system locally with `docker compose up`.  
> **Prerequisite:** Google Cloud account, `gcloud` CLI installed, Docker installed locally.  
> **Note:** The previous AWS guide is preserved at `docs/deployment/aws-guide.md` for reference. See ADR-011.

---

## Architecture Overview

```
┌─────────────┐       HTTPS         ┌──────────────────────────────┐       HTTPS        ┌─────────────┐
│   Browser   │  ───────────────►   │  FastAPI on Cloud Run        │  ──────────────►   │  Groq API   │
│  (Vercel)   │  ◄───────────────   │  (serverless container)      │  ◄──────────────   │  (LLM)      │
└─────────────┘       SSE           └──────────────────────────────┘                    └─────────────┘
```

- **Frontend:** Deployed on Vercel 
- **API:** Google Cloud Run — runs your Docker container, auto-scales, free tier
- **LLM:** Groq hosted API (`ENVIRONMENT=production`)

### Why Cloud Run?

- **Free tier:** 2M requests/month, 360K GB-seconds, 180K vCPU-seconds — effectively $0 for a demo
- **HTTPS out of the box** — no ALB, no certificates, no domain registration needed
- **Runs your Dockerfile as-is** — no changes to the application
- **Auto-scales to zero** — no cost when nobody is using it
- **SSE streaming works natively** — your `/chat` endpoint works without configuration

---

## Environment Variables for Production

These are set via `--set-env-vars` during deployment or in the Cloud Run console:

```env
ENVIRONMENT=production

# Groq LLM (production provider)
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT=120

# Prompt versioning
EXTRACTION_PROMPT_VERSION=v1
PROMPT_VERSION=latest

# Model artifacts (paths inside the container — no change needed)
MODEL_PATH=ml/artifacts/model.joblib
TRAINING_STATS_PATH=ml/artifacts/training_stats.json

# Server
HOST=0.0.0.0
# PORT is NOT set here — Cloud Run injects PORT=8080 automatically.
# The Dockerfile CMD reads $PORT, so this works without configuration.

# CORS — set to your Vercel domain (no trailing slash)
CORS_ORIGIN=https://your-app.vercel.app
```

**Important:** Do NOT set `PORT` in `--set-env-vars` — Cloud Run reserves it and will reject the deployment. Cloud Run injects `PORT=8080` automatically, and the Dockerfile CMD (`uvicorn ... --port $PORT`) picks it up.

**Security:** For `GROQ_API_KEY`, you can use `--set-secrets` with Google Secret Manager instead of `--set-env-vars` for better security. For a demo project, env vars are acceptable.

---

## Step 1 — Install and Configure gcloud CLI

**On WSL (Ubuntu/Debian):** Use snap — the apt repo method can hang in WSL:

```bash
sudo snap install google-cloud-cli --classic
gcloud version  # verify installation
```

**On native Linux (non-WSL):** Use the apt method:

```bash
# See: https://cloud.google.com/sdk/docs/install
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install -y google-cloud-cli
```

Then login and set up the project:

```bash
gcloud auth login

# Create a project (or use an existing one)
gcloud projects create real-estate-ai-demo --name="Real Estate AI"
gcloud config set project real-estate-ai-demo

# Enable required APIs (requires billing — see note below)
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

> **Billing required:** Google requires a billing account to enable APIs, even for free-tier usage. Link one at https://console.cloud.google.com/billing/linkedaccount?project=real-estate-ai-demo

---

## Step 2 — Create an Artifact Registry Repository

Cloud Run pulls images from Artifact Registry (Google's container registry):

```bash
gcloud artifacts repositories create real-estate-ai \
  --repository-format=docker \
  --location=us-central1 \
  --description="Real Estate AI Docker images"
```

Configure Docker to authenticate with Artifact Registry:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

---

## Step 3 — Build and Push the Docker Image

```bash
# Build for linux/amd64
docker build --platform linux/amd64 -t real-estate-ai .

# Tag for Artifact Registry
docker tag real-estate-ai:latest \
  us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest

# Push
docker push us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest
```

Replace `real-estate-ai-demo` with your actual project ID if different.

**Alternative — build in the cloud** (no local Docker needed):

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest
```

This builds the image using Cloud Build (free tier: 120 build-minutes/day).

---

## Step 4 — Deploy to Cloud Run

```bash
gcloud run deploy real-estate-ai \
  --image us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "\
ENVIRONMENT=production,\
GROQ_API_KEY=gsk_your_key_here,\
GROQ_BASE_URL=https://api.groq.com/openai/v1,\
GROQ_MODEL=llama-3.3-70b-versatile,\
GROQ_TIMEOUT=120,\
EXTRACTION_PROMPT_VERSION=v1,\
PROMPT_VERSION=latest,\
MODEL_PATH=ml/artifacts/model.joblib,\
TRAINING_STATS_PATH=ml/artifacts/training_stats.json,\
HOST=0.0.0.0,\
CORS_ORIGIN=https://your-app.vercel.app"
```

> **Do NOT include `PORT`** in `--set-env-vars` — Cloud Run reserves it and will reject the deployment. The `--port 8080` flag tells Cloud Run which port to route to, and Cloud Run injects `PORT=8080` into the container environment automatically.

**Key flags:**
- `--allow-unauthenticated` — public API (no auth in MVP)
- `--port 8080` — Cloud Run injects `PORT=8080` automatically; the Dockerfile CMD reads `$PORT`
- `--memory 1Gi` — enough for the ML model (~50MB) + Python runtime
- `--timeout 300` — 5 minutes max per request (SSE streams need time)

Cloud Run will output the service URL:

```
Service URL: https://real-estate-ai-xxxxx-uc.a.run.app
```

---

## Step 5 — Verify

```bash
# Health check
curl https://real-estate-ai-xxxxx-uc.a.run.app/health
# → {"status":"ok","model_loaded":true,"stats_loaded":true}

# Test SSE streaming
curl -N -X POST https://real-estate-ai-xxxxx-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello","history":[],"accumulated_features":{}}'
```

---

## Step 6 — Connect the Vercel Frontend

1. In your React frontend project, set the environment variable in Vercel:
   ```
   VITE_API_URL=https://real-estate-ai-xxxxx-uc.a.run.app
   ```

2. Update `CORS_ORIGIN` in the Cloud Run service to match your Vercel URL:
   ```bash
   gcloud run services update real-estate-ai \
     --region us-central1 \
     --set-env-vars CORS_ORIGIN=https://your-app.vercel.app
   ```

3. Redeploy both if you changed environment variables.

---

## Updating the Deployment

```bash
# Rebuild and push new image
docker build --platform linux/amd64 -t real-estate-ai .
docker tag real-estate-ai:latest \
  us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest
docker push us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest

# Deploy the new image
gcloud run deploy real-estate-ai \
  --image us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest \
  --region us-central1
```

Or use the cloud build shortcut:
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest
gcloud run deploy real-estate-ai \
  --image us-central1-docker.pkg.dev/real-estate-ai-demo/real-estate-ai/api:latest \
  --region us-central1
```

---

## PORT Configuration

Cloud Run injects `PORT=8080` as a reserved environment variable — you **cannot** set it via `--set-env-vars` (the deployment will fail with `reserved env names` error).

This works automatically because:
1. Cloud Run injects `PORT=8080` into the container
2. The Dockerfile CMD runs `uvicorn app.main:app --host $HOST --port $PORT`
3. Uvicorn reads the injected value and listens on 8080

For **local development**, the Dockerfile defaults to `PORT=8000` (set in the `ENV` directive), and `app/config.py` defaults to port 8000. No changes needed.

---

## Google Workspace / Organization Policy

If your Google account belongs to a Google Workspace organization (e.g., a custom domain like `@yourcompany.com`), the `--allow-unauthenticated` flag may fail with:

```
FAILED_PRECONDITION: One or more users named in the policy do not belong to a permitted customer
```

This is caused by the `iam.allowedPolicyMemberDomains` organization policy blocking `allUsers` access. To fix it:

```bash
# 1. Find your organization ID
gcloud organizations list

# 2. Enable the org policy API (if not already)
gcloud services enable orgpolicy.googleapis.com

# 3. Override the policy at the project level to allow public access
cat <<EOF > /tmp/policy.yaml
name: projects/real-estate-ai-demo/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
EOF

gcloud org-policies set-policy /tmp/policy.yaml

# 4. Now set the IAM binding for public access
gcloud beta run services add-iam-policy-binding \
  --region=us-central1 \
  --member=allUsers \
  --role=roles/run.invoker \
  real-estate-ai
```

This override applies only to the `real-estate-ai-demo` project — it does not affect other projects in the organization.

---

## Cold Starts

When the container scales to zero (no traffic for ~15 minutes), the next request triggers a cold start:
1. Cloud Run pulls the image (~5s)
2. Container starts, model loads (~5-10s)
3. First request processes (~3-5s for LLM call)

**Total cold start: ~15-20 seconds.** Subsequent requests are fast (model is already loaded).

To minimize cold starts:
- Keep the Docker image small (already multi-stage build)
- Set `--min-instances 1` to keep one container warm (exits free tier — adds ~$5-10/month)
- For a demo/portfolio project, cold starts are acceptable

---

## Cost Estimate

| Component | Free Tier | Monthly Cost |
|-----------|-----------|-------------|
| Cloud Run | 2M requests, 360K GB-s | $0 |
| Artifact Registry | 500MB storage | $0 |
| Cloud Build | 120 min/day | $0 |
| Groq API | Free tier (rate limited) | $0 |
| Vercel | Free tier (frontend) | $0 |

**Total: $0/month** within free tier limits.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container starts but `/health` returns 503 | Model file not found. Check `MODEL_PATH` env var matches the path inside the container (`ml/artifacts/model.joblib`). |
| Container crashes on startup | Check logs: `gcloud run services logs read real-estate-ai --region us-central1`. Usually a missing env var or model file. |
| LLM calls fail with 401 | `GROQ_API_KEY` is invalid or missing. Verify the key in the Groq dashboard. |
| CORS errors in browser | `CORS_ORIGIN` doesn't match the frontend URL exactly (include `https://`, no trailing slash). |
| SSE stream cuts off mid-response | Increase `--timeout` (default 300s should be sufficient). Check Cloud Run logs for timeout errors. |
| Cold start too slow | The ML model loads at startup. Ensure the Docker image is as small as possible. Consider `--min-instances 1` if cold starts are unacceptable. |
| `docker build` fails on ARM Mac (M1/M2) | Add `--platform linux/amd64` to the build command. |
| Port mismatch | Cloud Run expects port 8080 by default. Do NOT set `PORT` in env vars (it's reserved). Use `--port 8080` flag — the Dockerfile CMD reads the injected `$PORT` automatically. |
| `reserved env names: PORT` error on deploy | Remove `PORT` from `--set-env-vars`. Cloud Run injects it automatically. |
| `allUsers` IAM binding fails (org policy) | Your Google Workspace org blocks public access. See the "Google Workspace / Organization Policy" section above. |
| `gcloud` apt install hangs on WSL | Use `sudo snap install google-cloud-cli --classic` instead. |
