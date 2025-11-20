#!/bin/bash
# ================================================
# RAG Application - GCP Deployment Script
# Deploys all services to Cloud Run
# ================================================

set -e  # Exit on error

PROJECT_ID="anb-gpt-prj"
REGION="me-central2"

echo "=========================================="
echo "RAG Application - GCP Deployment"
echo "=========================================="
echo ""

# Set project
gcloud config set project $PROJECT_ID

# Deploy Backend
echo "[1/3] Deploying Backend API..."
echo "----------------------------------------"
cd backend
gcloud builds submit --region=$REGION --config cloudbuild.yaml .
cd ..
echo "✅ Backend deployed!"
echo ""

# Deploy LLM Service
echo "[2/3] Deploying LLM Service..."
echo "----------------------------------------"
cd llm_service
gcloud builds submit --region=$REGION --config cloudbuild.yaml .
cd ..
echo "✅ LLM Service deployed!"
echo ""

# Deploy Frontend
echo "[3/3] Deploying Frontend..."
echo "----------------------------------------"
cd frontend
gcloud builds submit --region=$REGION --config cloudbuild.yaml .
cd ..
echo "✅ Frontend deployed!"
echo ""

# Get service URLs
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Service URLs:"
echo "----------------------------------------"
BACKEND_URL=$(gcloud run services describe rag-backend --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not found")
LLM_URL=$(gcloud run services describe rag-llm --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not found")
FRONTEND_URL=$(gcloud run services describe rag-frontend --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not found")

echo "Backend:  $BACKEND_URL"
echo "LLM:      $LLM_URL"
echo "Frontend: $FRONTEND_URL"
echo ""
echo "Open your app: $FRONTEND_URL"
echo "=========================================="
