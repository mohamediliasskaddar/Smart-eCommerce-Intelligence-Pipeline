#!/bin/bash

# Project root
PROJECT="smart-ecommerce-intelligence"

# Create root directory
mkdir -p "$PROJECT"

# -----------------------
# Agents Module
# -----------------------
mkdir -p "$PROJECT/agents"
touch "$PROJECT/agents/__init__.py"
touch "$PROJECT/agents/base_agent.py"
touch "$PROJECT/agents/shopify_agent.py"
touch "$PROJECT/agents/woocommerce_agent.py"
touch "$PROJECT/agents/agent_coordinator.py"
touch "$PROJECT/agents/schemas.py"

# -----------------------
# Pipeline Module
# -----------------------
mkdir -p "$PROJECT/pipeline/steps"
mkdir -p "$PROJECT/pipeline/models"
touch "$PROJECT/pipeline/__init__.py"
touch "$PROJECT/pipeline/pipeline_definition.py"
touch "$PROJECT/pipeline/steps/ingest.py"
touch "$PROJECT/pipeline/steps/preprocess.py"
touch "$PROJECT/pipeline/steps/train.py"
touch "$PROJECT/pipeline/steps/evaluate.py"
touch "$PROJECT/pipeline/steps/topk_selector.py"
touch "$PROJECT/pipeline/models/xgboost_model.py"
touch "$PROJECT/pipeline/models/clustering.py"

# -----------------------
# Dashboard Module
# -----------------------
mkdir -p "$PROJECT/dashboard/pages"
touch "$PROJECT/dashboard/app.py"
touch "$PROJECT/dashboard/pages/01_overview.py"
touch "$PROJECT/dashboard/pages/02_topk_products.py"
touch "$PROJECT/dashboard/pages/03_predictions.py"
touch "$PROJECT/dashboard/pages/04_llm_insights.py"
touch "$PROJECT/dashboard/charts.py"
touch "$PROJECT/dashboard/data_loader.py"
touch "$PROJECT/dashboard/style.css"

# -----------------------
# LLM Module
# -----------------------
mkdir -p "$PROJECT/llm/prompts"
touch "$PROJECT/llm/__init__.py"
touch "$PROJECT/llm/enrichment.py"
touch "$PROJECT/llm/synthesis.py"
touch "$PROJECT/llm/mcp_agents.py"
touch "$PROJECT/llm/langchain_client.py"
touch "$PROJECT/llm/prompts/enrich_product.txt"
touch "$PROJECT/llm/prompts/top_k_summary.txt"
touch "$PROJECT/llm/prompts/strategy_report.txt"

# -----------------------
# Data directories
# -----------------------
mkdir -p "$PROJECT/data/raw"
mkdir -p "$PROJECT/data/processed"
mkdir -p "$PROJECT/data/output"

# -----------------------
# Tests
# -----------------------
mkdir -p "$PROJECT/tests"
touch "$PROJECT/tests/test_agents.py"
touch "$PROJECT/tests/test_pipeline.py"
touch "$PROJECT/tests/test_llm.py"

# -----------------------
# Infra
# -----------------------
mkdir -p "$PROJECT/infra/k8s"
touch "$PROJECT/infra/Dockerfile.agents"
touch "$PROJECT/infra/Dockerfile.pipeline"
touch "$PROJECT/infra/Dockerfile.dashboard"
touch "$PROJECT/infra/k8s/deployment.yaml"
touch "$PROJECT/infra/k8s/kubeflow-pipeline.yaml"

# -----------------------
# GitHub workflows
# -----------------------
mkdir -p "$PROJECT/.github/workflows"
touch "$PROJECT/.github/workflows/ci.yml"
touch "$PROJECT/.github/workflows/deploy.yml"

# -----------------------
# Root files
# -----------------------
touch "$PROJECT/config.yaml"
touch "$PROJECT/requirements.txt"
touch "$PROJECT/docker-compose.yml"
touch "$PROJECT/.env"
touch "$PROJECT/Makefile"
touch "$PROJECT/README.md"

echo "Project structure for '$PROJECT' created successfully!"