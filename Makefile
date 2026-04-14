.PHONY: help install dev api ui test test-unit test-integration lint clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := PYTHONPATH=. $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: $(VENV)/bin/activate ## Install all dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt 2>/dev/null || true
	$(PIP) install fastapi uvicorn pydantic-settings openai joblib scikit-learn lightgbm
	$(PIP) install pytest pytest-asyncio

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

# ---------------------------------------------------------------------------
# Run services
# ---------------------------------------------------------------------------

api: ## Start the FastAPI server (dev mode with auto-reload)
	$(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

api-prod: ## Start the FastAPI server (production mode)
	ENVIRONMENT=production $(UVICORN) app.main:app --host 0.0.0.0 --port 8000

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test: ## Run all tests (unit + integration)
	$(PYTEST) tests/ -v

test-unit: ## Run unit tests only (no Ollama required)
	$(PYTEST) tests/ -v -m "not integration"

test-integration: ## Run integration tests only (requires Ollama running)
	$(PYTEST) tests/ -v -m "integration"

test-coverage: ## Run tests with coverage report
	$(PYTEST) tests/ -v --tb=short -m "not integration"

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

lint: ## Run linting checks
	$(PYTHON) -m py_compile app/main.py
	$(PYTHON) -m py_compile app/config.py
	$(PYTHON) -m py_compile app/clients/llm.py
	$(PYTHON) -m py_compile app/services/extraction.py
	$(PYTHON) -m py_compile app/services/prediction.py
	$(PYTHON) -m py_compile app/schemas/property_features.py
	$(PYTHON) -m py_compile app/schemas/responses.py
	@echo "All files compile successfully."

check: lint test-unit ## Run lint + unit tests (quick pre-commit check)

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

ollama-status: ## Check if Ollama is running and list available models
	@curl -s http://localhost:11434/api/tags | python3 -m json.tool 2>/dev/null || echo "Ollama is not running."

health: ## Check API health endpoint
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "API is not running."

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache
