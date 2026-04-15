# AWS Deployment Guide — FastAPI Docker Container

> **Purpose:** Step-by-step guide to deploy the real-estate-ai API to AWS.  
> **Audience:** Developer who has tested the system locally with `docker compose up`.  
> **Prerequisite:** AWS account, AWS CLI installed and configured (`aws configure`), Docker installed locally.

---

## Architecture Overview

```
┌─────────────┐       HTTPS         ┌──────────────────────────┐       HTTPS        ┌─────────────┐
│   Browser   │  ───────────────►   │  FastAPI on AWS          │  ──────────────►   │  Groq API   │
│  (Vercel)   │  ◄───────────────   │  (ECS Fargate or EC2)    │  ◄──────────────   │  (LLM)      │
└─────────────┘       SSE           └──────────────────────────┘                    └─────────────┘
```

- **Frontend:** Deployed on Vercel
- **API:** Docker container on AWS — this guide covers two options:
  - **Option A: ECS Fargate** (recommended) — serverless containers, no server management
  - **Option B: EC2** — cheapest, full control, more manual setup
- **LLM:** Groq hosted API (no Ollama in production — requires `ENVIRONMENT=production`)

---

## Environment Variables for Production

These must be set in your AWS deployment (ECS task definition or EC2 `.env`):

```env
ENVIRONMENT=production

# Groq LLM (production provider)
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT=120

# Prompt versioning
EXTRACTION_PROMPT_VERSION=v1
EXPLANATION_PROMPT_VERSION=v1
CHAT_PROMPT_VERSION=v2

# Model artifacts (paths inside the container — no change needed)
MODEL_PATH=ml/artifacts/model.joblib
TRAINING_STATS_PATH=ml/artifacts/training_stats.json

# Server
HOST=0.0.0.0
PORT=8000

# CORS — set to your Vercel domain
CORS_ORIGIN=https://your-app.vercel.app
```

**Security notes:**
- Never commit `GROQ_API_KEY` to source control
- In ECS, use the task definition's `environment` or `secrets` (for AWS Secrets Manager integration)
- On EC2, use a `.env` file with restricted permissions (`chmod 600 .env`)

---

## Option A: ECS Fargate (Recommended)

### Step 1 — Push Docker Image to ECR

Create an ECR repository:
```bash
aws ecr create-repository --repository-name real-estate-ai --region us-east-1
```

Authenticate Docker with ECR:
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

Build and push:
```bash
# Build for linux/amd64 (required for Fargate)
docker build --platform linux/amd64 -t real-estate-ai .

# Tag for ECR
docker tag real-estate-ai:latest \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest

# Push
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest
```

Replace `<ACCOUNT_ID>` with your 12-digit AWS account ID. Find it with: `aws sts get-caller-identity --query Account --output text`

### Step 2 — Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name real-estate-ai --region us-east-1
```

### Step 3 — Create Task Definition

Save as `ecs-task-definition.json`:

```json
{
  "family": "real-estate-ai",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        { "name": "ENVIRONMENT", "value": "production" },
        { "name": "GROQ_API_KEY", "value": "gsk_your_key_here" },
        { "name": "GROQ_BASE_URL", "value": "https://api.groq.com/openai/v1" },
        { "name": "GROQ_MODEL", "value": "llama-3.3-70b-versatile" },
        { "name": "GROQ_TIMEOUT", "value": "120" },
        { "name": "EXTRACTION_PROMPT_VERSION", "value": "v1" },
        { "name": "EXPLANATION_PROMPT_VERSION", "value": "v1" },
        { "name": "CHAT_PROMPT_VERSION", "value": "v2" },
        { "name": "MODEL_PATH", "value": "ml/artifacts/model.joblib" },
        { "name": "TRAINING_STATS_PATH", "value": "ml/artifacts/training_stats.json" },
        { "name": "HOST", "value": "0.0.0.0" },
        { "name": "PORT", "value": "8000" },
        { "name": "CORS_ORIGIN", "value": "https://your-app.vercel.app" }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 15
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/real-estate-ai",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "api"
        }
      }
    }
  ]
}
```

Create the CloudWatch log group:
```bash
aws logs create-log-group --log-group-name /ecs/real-estate-ai --region us-east-1
```

Register the task definition:
```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

**Note about `ecsTaskExecutionRole`:** If this role doesn't exist, create it in IAM with the `AmazonECSTaskExecutionRolePolicy` managed policy. This allows ECS to pull images from ECR and write logs to CloudWatch.

### Step 4 — Create a Service with a Public IP

You need a VPC with public subnets. Use the default VPC or create one.

Find your default VPC subnets and security group:
```bash
# Get default VPC ID
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" --output text)

# Get subnet IDs
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].SubnetId" --output text | tr '\t' ',')

# Create a security group allowing port 8000
SG_ID=$(aws ec2 create-security-group \
  --group-name real-estate-ai-sg \
  --description "Allow HTTP 8000" \
  --vpc-id "$VPC_ID" \
  --query "GroupId" --output text)

aws ec2 authorize-security-group-ingress \
  --group-id "$SG_ID" \
  --protocol tcp --port 8000 --cidr 0.0.0.0/0
```

Create the ECS service:
```bash
aws ecs create-service \
  --cluster real-estate-ai \
  --service-name api \
  --task-definition real-estate-ai \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}"
```

### Step 5 — Get the Public IP

Wait ~1 minute for the task to start, then:
```bash
# Get the task ARN
TASK_ARN=$(aws ecs list-tasks --cluster real-estate-ai --service-name api \
  --query "taskArns[0]" --output text)

# Get the ENI ID
ENI_ID=$(aws ecs describe-tasks --cluster real-estate-ai --tasks "$TASK_ARN" \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text)

# Get the public IP
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids "$ENI_ID" \
  --query "NetworkInterfaces[0].Association.PublicIp" --output text)

echo "API is running at: http://$PUBLIC_IP:8000"
```

Verify:
```bash
curl http://$PUBLIC_IP:8000/health
# → {"status":"ok","model_loaded":true,"stats_loaded":true}
```

### Step 6 — (Optional) Add HTTPS with an Application Load Balancer

For production with HTTPS, add an ALB in front of ECS:

1. Create an ALB in the same VPC/subnets
2. Create a target group (type = `ip`, port 8000, health check path `/health`)
3. Add an HTTPS listener (port 443) with an ACM certificate for your domain
4. Update the ECS service to use the target group
5. Point your domain (e.g., `api.yourdomain.com`) to the ALB via Route 53 or your DNS provider

**Important for SSE:** Configure the ALB idle timeout to at least 120 seconds (default is 60s). SSE connections stay open for the full explanation stream:
```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn <ALB_ARN> \
  --attributes Key=idle_timeout.timeout_seconds,Value=120
```

---

## Option B: EC2 (Cheapest)

### Step 1 — Launch an EC2 Instance

```bash
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.small \
  --key-name your-key-pair \
  --security-group-ids sg-your-group \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=real-estate-ai}]' \
  --region us-east-1
```

- **Instance type:** `t3.small` (2 vCPU, 2 GB RAM) is sufficient. `t3.micro` works but is tight on memory.
- **AMI:** Amazon Linux 2023 or Ubuntu 22.04 LTS
- **Security group:** Allow inbound TCP 8000 (and 22 for SSH)

### Step 2 — Install Docker on the Instance

SSH into the instance:
```bash
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
```

Install Docker:
```bash
# Amazon Linux 2023
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Log out and back in for group change to take effect
exit
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
```

### Step 3 — Deploy the Container

**Option 3a — Pull from ECR** (if you pushed in Option A Step 1):
```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

docker pull <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest

docker run -d \
  --name real-estate-ai \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest
```

**Option 3b — Build on the instance** (no ECR needed):
```bash
# Clone the repo
git clone https://github.com/your-username/real-estate-ai.git
cd real-estate-ai

# Create .env with production values
cat > .env << 'EOF'
ENVIRONMENT=production
GROQ_API_KEY=gsk_your_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT=120
EXTRACTION_PROMPT_VERSION=v1
EXPLANATION_PROMPT_VERSION=v1
CHAT_PROMPT_VERSION=v2
MODEL_PATH=ml/artifacts/model.joblib
TRAINING_STATS_PATH=ml/artifacts/training_stats.json
HOST=0.0.0.0
PORT=8000
CORS_ORIGIN=https://your-app.vercel.app
EOF
chmod 600 .env

# Build and run
docker build -t real-estate-ai .
docker run -d \
  --name real-estate-ai \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  real-estate-ai:latest
```

### Step 4 — Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok","model_loaded":true,"stats_loaded":true}
```

From outside: `http://<EC2_PUBLIC_IP>:8000/health`

### Step 5 — (Optional) Add HTTPS with Caddy

Install Caddy as a reverse proxy for automatic HTTPS:
```bash
sudo yum install -y caddy   # Amazon Linux
# OR: sudo apt install -y caddy  # Ubuntu

# Configure Caddy
sudo tee /etc/caddy/Caddyfile << 'EOF'
api.yourdomain.com {
    reverse_proxy localhost:8000
}
EOF

sudo systemctl start caddy
sudo systemctl enable caddy
```

Point your domain's DNS A record to the EC2 public IP. Caddy will automatically obtain and renew a Let's Encrypt certificate.

---

## Connecting the Vercel Frontend

Once the API is deployed and accessible (e.g., `https://api.yourdomain.com` or `http://<PUBLIC_IP>:8000`):

1. In your React frontend project, set the `VITE_API_URL` environment variable in Vercel:
   ```
   VITE_API_URL=https://api.yourdomain.com
   ```
   (Or `http://<PUBLIC_IP>:8000` if not using HTTPS — not recommended for production)

2. Update `CORS_ORIGIN` in the API's environment to match your Vercel URL:
   ```
   CORS_ORIGIN=https://your-app.vercel.app
   ```

3. Redeploy both if you changed environment variables.

---

## Updating the Deployment

### ECS Fargate

```bash
# Rebuild and push new image
docker build --platform linux/amd64 -t real-estate-ai .
docker tag real-estate-ai:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/real-estate-ai:latest

# Force new deployment (pulls latest image)
aws ecs update-service --cluster real-estate-ai --service api --force-new-deployment
```

### EC2

```bash
ssh -i your-key.pem ec2-user@<PUBLIC_IP>
cd real-estate-ai
git pull
docker build -t real-estate-ai .
docker stop real-estate-ai && docker rm real-estate-ai
docker run -d \
  --name real-estate-ai \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env \
  real-estate-ai:latest
```

---

## Cost Estimates (Approximate)

| Component | Option | Monthly Cost |
|-----------|--------|-------------|
| ECS Fargate | 0.5 vCPU / 1 GB, always-on | ~$15–20 |
| EC2 | t3.small, always-on | ~$15 |
| EC2 | t3.micro (free tier eligible) | $0 (first 12 months) |
| ECR | <1 GB image storage | ~$0.10 |
| Groq API | Free tier (rate limited) | $0 |
| Vercel | Free tier (frontend) | $0 |

**Cheapest MVP option:** EC2 `t3.micro` (free tier) + Vercel free tier + Groq free tier = **$0/month** for the first year.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Container starts but `/health` returns 503 | Model file not found. Check `MODEL_PATH` env var matches the path inside the container (`ml/artifacts/model.joblib`). |
| LLM calls fail with 401 | `GROQ_API_KEY` is invalid or missing. Verify the key in the Groq dashboard. |
| CORS errors in browser | `CORS_ORIGIN` doesn't match the frontend URL exactly (include `https://`, no trailing slash). |
| SSE stream cuts off mid-response | ALB idle timeout too low (default 60s). Increase to 120s. If using EC2 directly, no ALB timeout applies. |
| Container OOM killed on Fargate | Increase task memory from 1024 to 2048 in the task definition. |
| `docker build` fails on ARM Mac (M1/M2) | Add `--platform linux/amd64` to the build command. |
