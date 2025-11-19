# Google Cloud Platform (GCP) Migration Guide
## RAG Application - Comprehensive Migration Strategy

**Document Version:** 1.0
**Last Updated:** 2025-11-19
**Project:** PDF RAG Application with Hybrid Search & AI Chat

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Overview](#2-current-architecture-overview)
3. [GCP Services Mapping](#3-gcp-services-mapping)
4. [Target GCP Architecture](#4-target-gcp-architecture)
5. [Migration Strategy](#5-migration-strategy)
6. [Infrastructure as Code](#6-infrastructure-as-code)
7. [Deployment Plan](#7-deployment-plan)
8. [Cost Estimation](#8-cost-estimation)
9. [Security & Compliance](#9-security--compliance)
10. [Monitoring & Observability](#10-monitoring--observability)
11. [Disaster Recovery & Backup](#11-disaster-recovery--backup)
12. [Performance Optimization](#12-performance-optimization)
13. [Migration Phases](#13-migration-phases)
14. [Testing Strategy](#14-testing-strategy)
15. [Rollback Plan](#15-rollback-plan)
16. [Post-Migration Tasks](#16-post-migration-tasks)
17. [Appendix](#17-appendix)

---

## 1. Executive Summary

### 1.1 Overview

This document provides a comprehensive strategy for migrating the RAG (Retrieval-Augmented Generation) application from a Docker Compose-based local deployment to Google Cloud Platform (GCP). The application consists of six microservices that provide PDF document processing, hybrid search, and AI-powered chat capabilities.

### 1.2 Business Drivers

- **Scalability**: Auto-scaling capabilities for variable workloads
- **Reliability**: 99.9%+ uptime with managed services
- **Performance**: Global CDN, regional data centers, optimized networking
- **Operational Efficiency**: Managed services reduce maintenance overhead
- **Cost Optimization**: Pay-per-use model with cost controls
- **Security**: Enterprise-grade security, compliance certifications
- **Developer Productivity**: CI/CD automation, managed infrastructure

### 1.3 Migration Approach

**Strategy**: Lift-and-Shift with Modernization (Hybrid Approach)

- **Phase 1**: Containerized services to Cloud Run (minimal changes)
- **Phase 2**: Managed database migration (Cloud SQL, Firestore)
- **Phase 3**: Serverless file processing (Cloud Functions, Cloud Storage)
- **Phase 4**: Optimization and cost reduction

### 1.4 Timeline Estimate

- **Planning & Setup**: 1-2 weeks
- **Infrastructure Provisioning**: 1 week
- **Service Migration**: 2-3 weeks
- **Testing & Validation**: 1-2 weeks
- **Production Cutover**: 1 week
- **Post-Migration Optimization**: Ongoing

**Total**: 6-9 weeks

### 1.5 Success Criteria

- Zero data loss during migration
- &lt;1 hour downtime during cutover
- Application performance matches or exceeds current
- Cost within projected budget (±10%)
- All security requirements met
- Automated CI/CD pipeline operational

---

## 2. Current Architecture Overview

### 2.1 Service Inventory

| Service | Technology | Purpose | Resources |
|---------|-----------|---------|-----------|
| **Backend API** | FastAPI (Python 3.11) | Core API, PDF processing, orchestration | 2-3GB Docker image |
| **LLM Service** | FastAPI (Python 3.11) | Gemini API integration, chat generation | 600MB Docker image |
| **Frontend** | React 18 + Nginx | User interface | 100MB Docker image |
| **PostgreSQL** | PostgreSQL 15 Alpine | Document metadata storage | Named volume |
| **ChromaDB** | ChromaDB latest | Vector embeddings storage | Named volume |
| **File Watcher** | Python watchdog | Automated PDF processing | 400MB Docker image |

### 2.2 Current Resource Usage

```
Total Memory: ~4-6GB
Total Storage: ~10-20GB (depends on documents)
Network: Internal Docker bridge network
Ports: 3000 (frontend), 8000 (backend), 8001 (chromadb), 8002 (llm), 5432 (postgres)
```

### 2.3 Data Flow

```
User → Frontend (React/Nginx)
  ↓
Backend API (FastAPI)
  ↓
├─→ PostgreSQL (metadata)
├─→ ChromaDB (embeddings)
└─→ LLM Service → Gemini API

File Upload/Watch → Backend → PDF Processing → Embedding → ChromaDB
```

### 2.4 Current Limitations

- **Scalability**: Single-instance deployment, no auto-scaling
- **Availability**: Single point of failure, no redundancy
- **Backup**: Manual backup required, no automated disaster recovery
- **Monitoring**: Basic logs, no centralized monitoring
- **Security**: Development credentials, no secrets management
- **Performance**: Limited by single machine resources
- **Geographic Distribution**: Single location deployment

---

## 3. GCP Services Mapping

### 3.1 Service-to-Service Mapping

| Current Component | GCP Service | Rationale |
|-------------------|-------------|-----------|
| **Frontend (React/Nginx)** | Cloud Run + Cloud CDN | Serverless container hosting, global CDN |
| **Backend API (FastAPI)** | Cloud Run | Serverless container hosting, auto-scaling |
| **LLM Service (FastAPI)** | Cloud Run | Serverless container hosting, GPU options |
| **PostgreSQL** | Cloud SQL (PostgreSQL) | Managed database, automated backups, HA |
| **ChromaDB** | Vertex AI Vector Search OR Cloud Run (self-hosted) | Managed vector search OR containerized ChromaDB |
| **File Watcher** | Cloud Storage + Cloud Functions (2nd gen) | Event-driven serverless file processing |
| **Docker Registry** | Artifact Registry | Container image storage |
| **File Storage** | Cloud Storage | Object storage for PDFs |
| **Secrets** | Secret Manager | Secure credential storage |
| **Networking** | VPC, Cloud NAT, Load Balancer | Private networking, internet egress |
| **CI/CD** | Cloud Build | Automated build and deployment |
| **Monitoring** | Cloud Logging + Cloud Monitoring | Centralized logging and metrics |

### 3.2 Alternative Architectures

#### Option A: Fully Managed (Recommended)
```
Frontend: Cloud Run + Cloud CDN + Cloud Storage (static hosting)
Backend: Cloud Run
LLM: Cloud Run
Database: Cloud SQL (PostgreSQL)
Vector DB: Vertex AI Vector Search
File Processing: Cloud Storage + Cloud Functions
```

**Pros**: Minimal operational overhead, auto-scaling, managed backups
**Cons**: Vendor lock-in, potential cost at high scale
**Best For**: Production deployments prioritizing reliability

#### Option B: Hybrid Managed
```
Frontend: Cloud Storage (static) + Cloud CDN + Load Balancer
Backend: GKE (Kubernetes) or Cloud Run
LLM: Cloud Run
Database: Cloud SQL (PostgreSQL)
Vector DB: ChromaDB on Cloud Run (persistent disk)
File Processing: Cloud Storage + Cloud Functions
```

**Pros**: More control, easier to migrate elsewhere
**Cons**: Higher operational overhead, more complex
**Best For**: Teams with Kubernetes expertise

#### Option C: Cost-Optimized
```
Frontend: Cloud Storage (static hosting)
Backend: Cloud Run (min instances = 0)
LLM: Cloud Run (min instances = 0)
Database: Cloud SQL (shared-core instance)
Vector DB: ChromaDB on Compute Engine (E2-medium)
File Processing: Cloud Storage + Cloud Functions
```

**Pros**: Lower cost for development/staging
**Cons**: Cold starts, lower performance
**Best For**: Development, staging, low-traffic production

**Recommendation**: Start with Option A for production, use Option C for dev/staging

---

## 4. Target GCP Architecture

### 4.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         INTERNET                                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Cloud CDN (Global)  │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  Cloud Load Balancer │
                  │  (HTTPS, SSL/TLS)    │
                  └──────────┬───────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Cloud Storage │  │   Cloud Run    │  │   Cloud Run    │
│  (Static Site) │  │   (Frontend)   │  │   (Backend)    │
│  [Optional]    │  │                │  │                │
└────────────────┘  └────────────────┘  └───────┬────────┘
                                                 │
                    ┌────────────────────────────┼────────────────┐
                    │                            │                │
                    ▼                            ▼                ▼
          ┌──────────────────┐        ┌──────────────────┐  ┌──────────────┐
          │   Cloud Run      │        │   Cloud SQL      │  │  Vertex AI   │
          │   (LLM Service)  │        │   (PostgreSQL)   │  │  Vector      │
          │                  │        │                  │  │  Search      │
          └─────────┬────────┘        └──────────────────┘  └──────┬───────┘
                    │                                               │
                    ▼                                               │
          ┌──────────────────┐                                      │
          │  Gemini API      │                                      │
          │  (External)      │                                      │
          └──────────────────┘                                      │
                                                                    │
┌─────────────────────────────────────────────────────────────────┼┘
│                    FILE PROCESSING PIPELINE                      │
│                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐             │
│  │  Cloud Storage   │ ───────▶│  Cloud Function  │             │
│  │  (PDF Bucket)    │ event   │  (Process PDF)   │             │
│  │                  │         └────────┬─────────┘             │
│  └──────────────────┘                  │                       │
│                                         ▼                       │
│                              ┌──────────────────┐               │
│                              │  Pub/Sub Topic   │               │
│                              │  (processing)    │               │
│                              └────────┬─────────┘               │
│                                       │                         │
│                                       ▼                         │
│                              Backend API (Cloud Run)            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SUPPORTING SERVICES                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Secret     │  │  Artifact    │  │  Cloud       │          │
│  │   Manager    │  │  Registry    │  │  Logging     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Cloud       │  │  Cloud       │  │  IAM         │          │
│  │  Monitoring  │  │  Build       │  │  Service     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Network Architecture

```
VPC: rag-application-vpc
├── Subnet: rag-backend-subnet (10.0.1.0/24) - us-central1
├── Subnet: rag-data-subnet (10.0.2.0/24) - us-central1
└── Serverless VPC Connector: rag-connector (for Cloud Run → VPC)

Cloud SQL: Private IP (10.0.2.10)
Cloud Run: Serverless VPC Access via connector
Cloud NAT: For outbound internet from Cloud Run (Gemini API calls)
```

### 4.3 Component Details

#### Frontend Service (Cloud Run)
```yaml
Service: rag-frontend
Region: us-central1
Container: gcr.io/PROJECT_ID/rag-frontend:latest
Port: 80
CPU: 1 vCPU
Memory: 512 MiB
Min Instances: 1 (production) / 0 (staging)
Max Instances: 10
Concurrency: 80
Timeout: 300s
Ingress: All traffic
Authentication: Allow unauthenticated (public facing)
Environment Variables:
  - REACT_APP_API_URL: https://api.rag-app.example.com/api/v1
```

#### Backend Service (Cloud Run)
```yaml
Service: rag-backend
Region: us-central1
Container: gcr.io/PROJECT_ID/rag-backend:latest
Port: 8000
CPU: 2 vCPU
Memory: 4 GiB
Min Instances: 1 (production) / 0 (staging)
Max Instances: 20
Concurrency: 80
Timeout: 900s (15 minutes for large PDF processing)
VPC Connector: rag-connector
Ingress: Internal and Cloud Load Balancing
Authentication: Require authentication (internal service)
Environment Variables:
  - POSTGRES_USER: from Secret Manager
  - POSTGRES_PASSWORD: from Secret Manager
  - POSTGRES_HOST: Cloud SQL connection name
  - CHROMA_HOST: rag-chromadb Cloud Run URL
  - LLM_SERVICE_URL: https://llm.rag-internal.a.run.app
  - WATCH_DIR: gs://rag-app-documents/watch
```

#### LLM Service (Cloud Run)
```yaml
Service: rag-llm
Region: us-central1
Container: gcr.io/PROJECT_ID/rag-llm:latest
Port: 8001
CPU: 2 vCPU
Memory: 2 GiB
Min Instances: 0 (on-demand)
Max Instances: 10
Concurrency: 10 (LLM requests are expensive)
Timeout: 300s
Ingress: Internal only
Authentication: Require authentication
Environment Variables:
  - LLM_PROVIDER: gemini
  - LLM_API_KEY: from Secret Manager
  - LLM_MODEL: gemini-2.0-flash
  - LLM_MAX_TOKENS: 4096
  - LLM_TEMPERATURE: 0.7
```

#### Vector Database (Two Options)

**Option 1: Vertex AI Vector Search (Recommended)**
```yaml
Index: rag-embeddings-index
Dimensions: 384
Distance: COSINE_DISTANCE
Shard Size: SMALL (< 1M vectors)
Region: us-central1
Deployed Endpoint: rag-embeddings-endpoint
Machine Type: e2-standard-2
Min Replicas: 1
Max Replicas: 5
```

**Option 2: ChromaDB on Cloud Run**
```yaml
Service: rag-chromadb
Region: us-central1
Container: chromadb/chroma:latest
Port: 8000
CPU: 2 vCPU
Memory: 4 GiB
Min Instances: 1 (stateful service)
Max Instances: 1 (no horizontal scaling)
Persistent Disk: 100 GB SSD
Timeout: 300s
Ingress: Internal only
```

#### Database (Cloud SQL)
```yaml
Instance: rag-postgres-instance
Database Version: PostgreSQL 15
Region: us-central1
Zone: us-central1-a (primary), us-central1-b (HA replica)
Tier: db-custom-2-7680 (2 vCPU, 7.5 GB RAM)
Storage: 100 GB SSD
Auto-resize: Enabled (max 500 GB)
Backups: Automated daily at 3:00 AM UTC
High Availability: Enabled (regional HA)
Private IP: Enabled (VPC peering)
Public IP: Disabled
Encryption: Google-managed keys
Flags:
  - max_connections: 200
  - shared_buffers: 2GB
```

#### File Storage (Cloud Storage)
```yaml
Bucket: rag-app-documents
Location: us-central1
Storage Class: Standard
Lifecycle Rules:
  - Delete files older than 90 days (optional)
Versioning: Enabled
Access Control: Uniform (IAM)
Public Access: Prevented
Notifications:
  - Event: OBJECT_FINALIZE
  - Filter: *.pdf
  - Destination: Pub/Sub topic (rag-pdf-uploads)
```

#### File Processing (Cloud Functions)
```yaml
Function: process-pdf-upload
Runtime: Python 3.11
Region: us-central1
Trigger: Cloud Storage (OBJECT_FINALIZE on *.pdf)
Entry Point: process_pdf_file
Memory: 2 GiB
Timeout: 540s (9 minutes)
Min Instances: 0
Max Instances: 10
VPC Connector: rag-connector
Environment Variables:
  - BACKEND_API_URL: https://backend.rag-internal.a.run.app
  - BACKEND_PROCESS_ENDPOINT: /api/v1/documents/process-file
Service Account: pdf-processor@PROJECT_ID.iam.gserviceaccount.com
```

---

## 5. Migration Strategy

### 5.1 Migration Principles

1. **Zero Data Loss**: All data must be migrated completely and verified
2. **Minimal Downtime**: Target &lt;1 hour production downtime
3. **Incremental Migration**: Migrate services incrementally, validate each step
4. **Rollback Capability**: Maintain ability to rollback at each phase
5. **Parallel Testing**: Test in GCP while maintaining current system
6. **Documentation**: Document every step for repeatability

### 5.2 Pre-Migration Checklist

#### Technical Prerequisites
- [ ] GCP Project created and configured
- [ ] Billing account linked and budget alerts configured
- [ ] gcloud CLI installed and authenticated
- [ ] Terraform installed (v1.5+)
- [ ] Docker installed for local testing
- [ ] Access to current system for data export

#### Access & Permissions
- [ ] Project Owner or Editor role assigned
- [ ] Service accounts created with least-privilege permissions
- [ ] API access enabled (Cloud Run, Cloud SQL, etc.)
- [ ] Secret Manager access configured
- [ ] Artifact Registry permissions granted

#### Planning
- [ ] Migration timeline approved
- [ ] Stakeholder communication plan
- [ ] Rollback plan documented
- [ ] Success criteria defined
- [ ] Cost budget approved

### 5.3 Data Migration Plan

#### Database Migration (PostgreSQL)

**Approach**: Database Migration Service (DMS) OR pg_dump/pg_restore

**Steps**:
1. **Pre-Migration**
   ```bash
   # Create Cloud SQL instance
   gcloud sql instances create rag-postgres-instance \
     --database-version=POSTGRES_15 \
     --tier=db-custom-2-7680 \
     --region=us-central1 \
     --network=projects/PROJECT_ID/global/networks/rag-application-vpc \
     --no-assign-ip \
     --enable-bin-log \
     --backup-start-time=03:00

   # Create database
   gcloud sql databases create ragdb --instance=rag-postgres-instance

   # Create user
   gcloud sql users create raguser \
     --instance=rag-postgres-instance \
     --password=SECURE_PASSWORD
   ```

2. **Data Export** (from current system)
   ```bash
   # Full database dump
   docker exec rag_postgres pg_dump -U raguser -d ragdb -F c -f /tmp/ragdb_backup.dump

   # Copy dump file out
   docker cp rag_postgres:/tmp/ragdb_backup.dump ./ragdb_backup.dump
   ```

3. **Data Import** (to Cloud SQL)
   ```bash
   # Upload to Cloud Storage
   gsutil cp ragdb_backup.dump gs://rag-migration-temp/

   # Import to Cloud SQL
   gcloud sql import sql rag-postgres-instance \
     gs://rag-migration-temp/ragdb_backup.dump \
     --database=ragdb
   ```

4. **Validation**
   ```bash
   # Connect to Cloud SQL
   gcloud sql connect rag-postgres-instance --user=raguser --database=ragdb

   # Verify row counts
   SELECT COUNT(*) FROM documents;

   # Verify data integrity
   SELECT * FROM documents ORDER BY uploaded_at DESC LIMIT 10;
   ```

#### Vector Database Migration (ChromaDB)

**Approach A: Direct ChromaDB Migration**

1. **Export ChromaDB Data**
   ```python
   # Export script (run in current environment)
   import chromadb
   import pickle

   client = chromadb.HttpClient(host='localhost', port=8001)
   collection = client.get_collection("documents")

   # Get all embeddings
   results = collection.get(include=['embeddings', 'metadatas', 'documents'])

   # Save to file
   with open('chromadb_export.pkl', 'wb') as f:
       pickle.dump(results, f)
   ```

2. **Import to Cloud Run ChromaDB**
   ```python
   # Import script (run in GCP environment)
   import chromadb
   import pickle

   client = chromadb.HttpClient(host='CHROMADB_CLOUD_RUN_URL', port=443)
   collection = client.get_or_create_collection("documents", metadata={"hnsw:space": "cosine"})

   # Load exported data
   with open('chromadb_export.pkl', 'rb') as f:
       data = pickle.load(f)

   # Batch insert
   collection.add(
       embeddings=data['embeddings'],
       metadatas=data['metadatas'],
       documents=data['documents'],
       ids=data['ids']
   )
   ```

**Approach B: Vertex AI Vector Search Migration**

1. **Export Embeddings to JSONL**
   ```python
   import chromadb
   import json

   client = chromadb.HttpClient(host='localhost', port=8001)
   collection = client.get_collection("documents")
   results = collection.get(include=['embeddings', 'metadatas', 'documents'])

   # Convert to Vertex AI format
   with open('embeddings.jsonl', 'w') as f:
       for i in range(len(results['ids'])):
           record = {
               'id': results['ids'][i],
               'embedding': results['embeddings'][i],
               'restricts': [
                   {'namespace': k, 'allow': [v]}
                   for k, v in results['metadatas'][i].items()
               ]
           }
           f.write(json.dumps(record) + '\n')
   ```

2. **Upload to Cloud Storage**
   ```bash
   gsutil cp embeddings.jsonl gs://rag-embeddings-data/
   ```

3. **Create Vertex AI Index**
   ```bash
   # Create index
   gcloud ai indexes create \
     --display-name=rag-embeddings-index \
     --metadata-file=index_metadata.json \
     --region=us-central1

   # index_metadata.json:
   {
     "contentsDeltaUri": "gs://rag-embeddings-data/",
     "config": {
       "dimensions": 384,
       "approximateNeighborsCount": 150,
       "distanceMeasureType": "COSINE_DISTANCE",
       "algorithm": "TREE_AH"
     }
   }
   ```

4. **Deploy Index**
   ```bash
   gcloud ai index-endpoints create \
     --display-name=rag-embeddings-endpoint \
     --region=us-central1

   gcloud ai index-endpoints deploy-index INDEX_ENDPOINT_ID \
     --deployed-index-id=rag_embeddings_v1 \
     --index=INDEX_ID \
     --display-name=rag-embeddings-deployed \
     --machine-type=e2-standard-2 \
     --min-replica-count=1 \
     --max-replica-count=5
   ```

#### File Storage Migration

```bash
# Sync local files to Cloud Storage
gsutil -m rsync -r ./data/watch gs://rag-app-documents/watch/
gsutil -m rsync -r ./data/uploads gs://rag-app-documents/uploads/

# Set bucket lifecycle
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://rag-app-documents
```

### 5.4 Service Migration Sequence

**Order**: Dependencies first, applications last

1. **Secrets & Configuration** (Week 1)
   - Create secrets in Secret Manager
   - Configure IAM roles and service accounts
   - Set up VPC and networking

2. **Data Layer** (Week 1-2)
   - Provision Cloud SQL
   - Migrate PostgreSQL data
   - Set up Cloud Storage buckets
   - Migrate vector database

3. **Backend Services** (Week 2-3)
   - Build and push Docker images to Artifact Registry
   - Deploy LLM Service to Cloud Run
   - Deploy Backend API to Cloud Run
   - Test backend APIs

4. **File Processing** (Week 3)
   - Deploy Cloud Function for PDF processing
   - Set up Cloud Storage triggers
   - Test end-to-end file processing

5. **Frontend** (Week 3-4)
   - Deploy Frontend to Cloud Run
   - Configure Load Balancer and Cloud CDN
   - Set up custom domain and SSL

6. **Integration Testing** (Week 4-5)
   - End-to-end testing
   - Performance testing
   - Load testing
   - Security testing

7. **Production Cutover** (Week 5-6)
   - Final data sync
   - DNS cutover
   - Monitor and validate

---

## 6. Infrastructure as Code

### 6.1 Terraform Structure

```
terraform/
├── main.tf                 # Main configuration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── terraform.tfvars        # Variable values (gitignored)
├── versions.tf             # Provider versions
├── modules/
│   ├── networking/         # VPC, subnets, NAT
│   ├── cloudsql/           # Cloud SQL instance
│   ├── cloudrun/           # Cloud Run services
│   ├── storage/            # Cloud Storage buckets
│   ├── functions/          # Cloud Functions
│   ├── iam/                # Service accounts, IAM
│   ├── monitoring/         # Logging, monitoring
│   └── secrets/            # Secret Manager
├── environments/
│   ├── dev/
│   │   ├── backend.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   ├── backend.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── backend.tf
│       └── terraform.tfvars
└── scripts/
    ├── init.sh             # Initialize Terraform
    ├── plan.sh             # Plan changes
    ├── apply.sh            # Apply changes
    └── destroy.sh          # Destroy infrastructure
```

### 6.2 Sample Terraform Code

#### main.tf
```hcl
terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "rag-app-terraform-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC Network
module "networking" {
  source = "./modules/networking"

  project_id   = var.project_id
  region       = var.region
  network_name = "rag-application-vpc"
}

# Cloud SQL
module "cloudsql" {
  source = "./modules/cloudsql"

  project_id      = var.project_id
  region          = var.region
  instance_name   = "rag-postgres-instance"
  database_name   = "ragdb"
  database_user   = "raguser"
  database_password_secret = google_secret_manager_secret_version.db_password.id
  network_id      = module.networking.network_id
  tier            = var.cloudsql_tier
}

# Cloud Storage
module "storage" {
  source = "./modules/storage"

  project_id   = var.project_id
  region       = var.region
  bucket_name  = "rag-app-documents"
}

# Cloud Run Services
module "backend" {
  source = "./modules/cloudrun"

  project_id     = var.project_id
  region         = var.region
  service_name   = "rag-backend"
  image          = "${var.artifact_registry_url}/rag-backend:${var.image_tag}"
  vpc_connector  = module.networking.vpc_connector_id
  env_vars = {
    POSTGRES_HOST = module.cloudsql.connection_name
    CHROMA_HOST   = module.chromadb.service_url
    LLM_SERVICE_URL = module.llm_service.service_url
  }
  secrets = {
    POSTGRES_PASSWORD = google_secret_manager_secret_version.db_password.id
  }
  cpu_limit     = "2000m"
  memory_limit  = "4Gi"
  min_instances = var.backend_min_instances
  max_instances = var.backend_max_instances
}

module "llm_service" {
  source = "./modules/cloudrun"

  project_id     = var.project_id
  region         = var.region
  service_name   = "rag-llm"
  image          = "${var.artifact_registry_url}/rag-llm:${var.image_tag}"
  env_vars = {
    LLM_PROVIDER = "gemini"
    LLM_MODEL    = "gemini-2.0-flash"
  }
  secrets = {
    LLM_API_KEY = google_secret_manager_secret_version.gemini_api_key.id
  }
  cpu_limit     = "2000m"
  memory_limit  = "2Gi"
  min_instances = 0
  max_instances = 10
  ingress       = "internal"
}

module "frontend" {
  source = "./modules/cloudrun"

  project_id     = var.project_id
  region         = var.region
  service_name   = "rag-frontend"
  image          = "${var.artifact_registry_url}/rag-frontend:${var.image_tag}"
  env_vars = {
    REACT_APP_API_URL = module.backend.service_url
  }
  cpu_limit     = "1000m"
  memory_limit  = "512Mi"
  min_instances = var.frontend_min_instances
  max_instances = 10
  ingress       = "all"
  allow_unauthenticated = true
}

# Cloud Functions
module "pdf_processor" {
  source = "./modules/functions"

  project_id      = var.project_id
  region          = var.region
  function_name   = "process-pdf-upload"
  runtime         = "python311"
  entry_point     = "process_pdf_file"
  source_dir      = "../file_watcher_service"
  trigger_bucket  = module.storage.bucket_name
  trigger_event   = "google.storage.object.finalize"
  vpc_connector   = module.networking.vpc_connector_id
  env_vars = {
    BACKEND_API_URL = module.backend.service_url
  }
  memory          = 2048
  timeout         = 540
}

# Monitoring
module "monitoring" {
  source = "./modules/monitoring"

  project_id     = var.project_id
  notification_channels = var.notification_emails
}
```

#### modules/cloudrun/main.tf
```hcl
resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = var.image

        ports {
          container_port = var.container_port
        }

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }

        dynamic "env" {
          for_each = var.env_vars
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_from {
              secret_key_ref {
                name = env.value
                key  = "latest"
              }
            }
          }
        }
      }

      service_account_name = google_service_account.service.email

      dynamic "vpc_access" {
        for_each = var.vpc_connector != null ? [1] : []
        content {
          connector = var.vpc_connector
        }
      }
    }

    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/vpc-access-egress" = var.vpc_connector != null ? "private-ranges-only" : "all"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_service_account" "service" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name}"
}

resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.allow_unauthenticated ? 1 : 0

  service  = google_cloud_run_service.service.name
  location = google_cloud_run_service.service.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

### 6.3 Deployment Scripts

#### scripts/deploy.sh
```bash
#!/bin/bash
set -e

# Configuration
PROJECT_ID="your-project-id"
REGION="us-central1"
ARTIFACT_REGISTRY="us-central1-docker.pkg.dev/$PROJECT_ID/rag-app"
ENV=${1:-"dev"}  # dev, staging, production

echo "Deploying to environment: $ENV"

# Build and push images
echo "Building Docker images..."
docker build -t $ARTIFACT_REGISTRY/rag-backend:latest ./backend
docker build -t $ARTIFACT_REGISTRY/rag-llm:latest ./llm_service
docker build -t $ARTIFACT_REGISTRY/rag-frontend:latest ./frontend

echo "Pushing images to Artifact Registry..."
docker push $ARTIFACT_REGISTRY/rag-backend:latest
docker push $ARTIFACT_REGISTRY/rag-llm:latest
docker push $ARTIFACT_REGISTRY/rag-frontend:latest

# Apply Terraform
echo "Applying Terraform configuration..."
cd terraform/environments/$ENV
terraform init
terraform plan -out=tfplan
terraform apply tfplan

echo "Deployment complete!"
```

---

## 7. Deployment Plan

### 7.1 CI/CD Pipeline (Cloud Build)

#### cloudbuild.yaml
```yaml
steps:
  # Build backend
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-backend'
    args:
      - 'build'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-backend:$COMMIT_SHA'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-backend:latest'
      - './backend'

  # Build LLM service
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-llm'
    args:
      - 'build'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-llm:$COMMIT_SHA'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-llm:latest'
      - './llm_service'

  # Build frontend
  - name: 'gcr.io/cloud-builders/docker'
    id: 'build-frontend'
    args:
      - 'build'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-frontend:$COMMIT_SHA'
      - '-t'
      - '${_ARTIFACT_REGISTRY}/rag-frontend:latest'
      - '--build-arg'
      - 'REACT_APP_API_URL=${_BACKEND_URL}'
      - './frontend'

  # Push images
  - name: 'gcr.io/cloud-builders/docker'
    id: 'push-images'
    args:
      - 'push'
      - '--all-tags'
      - '${_ARTIFACT_REGISTRY}/rag-backend'
    waitFor: ['build-backend']

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_ARTIFACT_REGISTRY}/rag-llm'
    waitFor: ['build-llm']

  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - '--all-tags'
      - '${_ARTIFACT_REGISTRY}/rag-frontend'
    waitFor: ['build-frontend']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-backend'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'rag-backend'
      - '--image=${_ARTIFACT_REGISTRY}/rag-backend:$COMMIT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--vpc-connector=${_VPC_CONNECTOR}'
      - '--set-env-vars=POSTGRES_HOST=${_POSTGRES_HOST}'
      - '--update-secrets=POSTGRES_PASSWORD=postgres-password:latest'
    waitFor: ['push-images']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-llm'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'rag-llm'
      - '--image=${_ARTIFACT_REGISTRY}/rag-llm:$COMMIT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--update-secrets=LLM_API_KEY=gemini-api-key:latest'
    waitFor: ['push-images']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    id: 'deploy-frontend'
    entrypoint: 'gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'rag-frontend'
      - '--image=${_ARTIFACT_REGISTRY}/rag-frontend:$COMMIT_SHA'
      - '--region=${_REGION}'
      - '--platform=managed'
      - '--allow-unauthenticated'
    waitFor: ['push-images']

substitutions:
  _ARTIFACT_REGISTRY: 'us-central1-docker.pkg.dev/${PROJECT_ID}/rag-app'
  _REGION: 'us-central1'
  _VPC_CONNECTOR: 'rag-connector'
  _POSTGRES_HOST: '/cloudsql/PROJECT_ID:us-central1:rag-postgres-instance'
  _BACKEND_URL: 'https://api.rag-app.example.com/api/v1'

options:
  machineType: 'E2_HIGHCPU_8'
  logging: CLOUD_LOGGING_ONLY

timeout: 1800s  # 30 minutes
```

### 7.2 Environment Configuration

#### Development
```yaml
Environment: dev
Region: us-central1
Cloud SQL Tier: db-f1-micro (shared-core)
Backend Min Instances: 0
Frontend Min Instances: 0
Budget Alert: $50/month
Domain: dev.rag-app.example.com
```

#### Staging
```yaml
Environment: staging
Region: us-central1
Cloud SQL Tier: db-custom-1-3840
Backend Min Instances: 0
Frontend Min Instances: 0
Budget Alert: $200/month
Domain: staging.rag-app.example.com
```

#### Production
```yaml
Environment: production
Region: us-central1 (primary), us-east1 (DR)
Cloud SQL Tier: db-custom-2-7680 (HA enabled)
Backend Min Instances: 1
Frontend Min Instances: 1
Budget Alert: $1000/month
Domain: app.rag-app.example.com
```

---

## 8. Cost Estimation

### 8.1 Monthly Cost Breakdown (Production)

| Service | Configuration | Monthly Cost (USD) |
|---------|--------------|-------------------|
| **Cloud Run - Backend** | 2 vCPU, 4GB, 1M requests, 30% utilization | $80-120 |
| **Cloud Run - Frontend** | 1 vCPU, 512MB, 2M requests, 20% utilization | $40-60 |
| **Cloud Run - LLM** | 2 vCPU, 2GB, 500K requests, on-demand | $50-80 |
| **Cloud SQL** | db-custom-2-7680, HA, 100GB SSD | $250-300 |
| **Vertex AI Vector Search** | 1M vectors, 500K queries | $150-200 |
| **Cloud Storage** | 500GB Standard, 100K operations | $10-15 |
| **Cloud Functions** | 100K invocations, 2GB memory | $5-10 |
| **Cloud NAT** | 1 gateway, 100GB egress | $45-50 |
| **Load Balancer** | HTTPS, 2M requests | $20-25 |
| **Cloud CDN** | 500GB egress | $40-50 |
| **Cloud Logging** | 50GB ingestion, 30-day retention | $25-30 |
| **Cloud Monitoring** | Standard metrics | $10-15 |
| **Secret Manager** | 10 secrets, 10K accesses | $1-2 |
| **Artifact Registry** | 50GB storage | $2-3 |
| **Gemini API** | 10M tokens/month | $50-100 |
| **Networking** | VPC, egress | $30-40 |
| **TOTAL** |  | **$808-1,100/month** |

### 8.2 Cost Optimization Strategies

#### Immediate Optimizations
1. **Min Instances = 0** for dev/staging (eliminates idle costs)
2. **Cloud SQL Shared Core** for non-production ($10/month vs $250)
3. **Committed Use Discounts** (CUD) for Cloud Run (30% savings)
4. **Sustained Use Discounts** automatically applied
5. **Cloud Storage Lifecycle** to Nearline/Coldline for old files
6. **Log Retention** reduced to 7 days for non-critical logs

#### Advanced Optimizations
1. **Vertex AI Alternative**: Use ChromaDB on Compute Engine (E2-medium = $25/month)
2. **Request Batching**: Combine embedding requests
3. **CDN Caching**: Increase cache hit ratio to 80%+
4. **Regional Deployment**: Single region vs multi-region
5. **Reserved IPs**: Avoid ephemeral IP charges
6. **Cloud Scheduler**: Shut down dev/staging overnight

#### Cost Comparison

| Approach | Monthly Cost | Notes |
|----------|-------------|-------|
| **Full Managed (Production)** | $800-1,100 | Recommended for production |
| **Hybrid (ChromaDB on GCE)** | $650-900 | Save $150 on Vertex AI |
| **Cost-Optimized (Dev)** | $50-100 | Shared SQL, min instances = 0 |
| **Current (Docker Compose)** | $0 (local) | No cloud costs, limited scale |

### 8.3 Budget Alerts

```bash
# Create budget alert
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="RAG App Production Budget" \
  --budget-amount=1000 \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=75 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100
```

---

## 9. Security & Compliance

### 9.1 Security Architecture

#### Network Security
```
Internet → Cloud Armor (DDoS, WAF)
       → Load Balancer (SSL/TLS termination)
       → Cloud Run (application)
       → VPC (private network)
       → Cloud SQL (private IP only)
```

#### Identity & Access Management

**Service Accounts** (Principle of Least Privilege):

```yaml
# Backend Service Account
backend-sa@PROJECT_ID.iam.gserviceaccount.com:
  - roles/cloudsql.client           # Connect to Cloud SQL
  - roles/storage.objectViewer      # Read PDFs from bucket
  - roles/secretmanager.secretAccessor  # Access secrets
  - roles/aiplatform.user           # Query Vertex AI
  - roles/run.invoker               # Call LLM service

# LLM Service Account
llm-sa@PROJECT_ID.iam.gserviceaccount.com:
  - roles/secretmanager.secretAccessor  # Access Gemini API key

# Cloud Function Service Account
pdf-processor-sa@PROJECT_ID.iam.gserviceaccount.com:
  - roles/storage.objectViewer      # Read uploaded PDFs
  - roles/run.invoker               # Call backend API
  - roles/cloudsql.client           # Update database

# Frontend Service Account
frontend-sa@PROJECT_ID.iam.gserviceaccount.com:
  - (no special permissions - public service)
```

#### Secrets Management

```bash
# Create secrets
gcloud secrets create postgres-password \
  --replication-policy="automatic" \
  --data-file=- <<EOF
SECURE_RANDOM_PASSWORD_HERE
EOF

gcloud secrets create gemini-api-key \
  --replication-policy="automatic" \
  --data-file=- <<EOF
YOUR_GEMINI_API_KEY
EOF

# Grant access
gcloud secrets add-iam-policy-binding postgres-password \
  --member="serviceAccount:backend-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Data Encryption

- **At Rest**:
  - Cloud SQL: Google-managed encryption keys (GMEK) or CMEK
  - Cloud Storage: Default encryption
  - Persistent Disks: Encrypted by default

- **In Transit**:
  - HTTPS/TLS 1.3 for all external connections
  - Private IP for internal service communication
  - VPC peering for Cloud SQL connections

#### Application Security

**CORS Configuration**:
```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.rag-app.example.com",
        "https://staging.rag-app.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

**Rate Limiting** (Cloud Armor):
```yaml
security_policy:
  name: rag-app-security-policy
  rules:
    - priority: 1000
      match:
        versioned_expr: SRC_IPS_V1
        config:
          src_ip_ranges: ["*"]
      rate_limit_options:
        rate_limit_threshold:
          count: 100
          interval_sec: 60
        conform_action: allow
        exceed_action: deny-403
```

**Authentication** (Future Enhancement):
```yaml
# Add Cloud Identity-Aware Proxy (IAP) for user authentication
# Or integrate Firebase Authentication / Auth0
```

### 9.2 Compliance Considerations

| Requirement | GCP Service/Feature | Status |
|-------------|-------------------|--------|
| **Data Residency** | Regional resources (us-central1) | ✓ Implemented |
| **Encryption at Rest** | GMEK/CMEK | ✓ Default |
| **Encryption in Transit** | TLS 1.3 | ✓ Enforced |
| **Access Logging** | Cloud Audit Logs | ✓ Enabled |
| **Data Backup** | Cloud SQL automated backups | ✓ Daily |
| **Disaster Recovery** | Regional HA, cross-region backups | ○ Optional |
| **PII Protection** | DLP API for content scanning | ○ Future |
| **GDPR Compliance** | Data deletion API, audit logs | ○ Partial |
| **HIPAA Compliance** | BAA with Google, CMEK | ○ If needed |

### 9.3 Security Checklist

- [ ] Service accounts follow least-privilege principle
- [ ] All secrets stored in Secret Manager (no hardcoded credentials)
- [ ] Cloud SQL private IP only (no public IP)
- [ ] VPC firewall rules configured
- [ ] Cloud Armor enabled for DDoS protection
- [ ] SSL/TLS certificates configured
- [ ] CORS properly restricted
- [ ] Rate limiting implemented
- [ ] Audit logging enabled
- [ ] Security scanning enabled (Container Analysis)
- [ ] Vulnerability scanning scheduled
- [ ] IAM policies reviewed quarterly
- [ ] Data classification documented
- [ ] Incident response plan created

---

## 10. Monitoring & Observability

### 10.1 Monitoring Strategy

#### Key Metrics to Track

**Application Metrics**:
```yaml
Backend API:
  - Request rate (requests/sec)
  - Request latency (p50, p95, p99)
  - Error rate (4xx, 5xx)
  - CPU utilization (%)
  - Memory utilization (%)
  - Active instances count
  - Cold start frequency

LLM Service:
  - Request rate
  - Generation latency
  - Token usage
  - Error rate (API failures)

Database:
  - Connection count
  - Query latency
  - CPU utilization
  - Memory utilization
  - Disk I/O
  - Replication lag (HA)

Vector DB:
  - Query latency
  - Index size
  - Query throughput

Storage:
  - Object count
  - Total size
  - Request rate
  - Bandwidth usage
```

#### Cloud Monitoring Dashboards

```yaml
Dashboard: RAG Application Overview
Widgets:
  - Service Health (uptime, error rate)
  - Request Volume (chart)
  - Latency Distribution (heatmap)
  - Cost Breakdown (pie chart)
  - Active Users (gauge)
  - Database Connections (line chart)

Dashboard: Performance
Widgets:
  - API Latency (p50, p95, p99)
  - PDF Processing Time
  - Embedding Generation Time
  - Search Query Latency
  - LLM Response Time

Dashboard: Infrastructure
Widgets:
  - Cloud Run Instances
  - Cloud SQL CPU/Memory
  - Storage Usage
  - Network Throughput
```

#### Sample Monitoring Query (MQL)

```sql
-- Cloud Run request latency
fetch cloud_run_revision
| metric 'run.googleapis.com/request_latencies'
| group_by 1m, [percentile(value.request_latencies, 99)]
| every 1m

-- Cloud SQL CPU utilization
fetch cloudsql_database
| metric 'cloudsql.googleapis.com/database/cpu/utilization'
| group_by 1m, [mean(value.utilization)]
| every 1m
| condition gt(val(), 0.8)  # Alert if > 80%
```

### 10.2 Logging Strategy

#### Log Types

```yaml
Application Logs:
  - Backend API request/response logs
  - PDF processing logs
  - Embedding generation logs
  - Search query logs
  - LLM interaction logs
  - Error stack traces

Audit Logs:
  - IAM changes
  - Resource modifications
  - Data access (Cloud SQL queries)
  - Secret access

System Logs:
  - Cloud Run container logs
  - Cloud SQL system logs
  - Cloud Functions execution logs
```

#### Structured Logging

```python
# backend/app/core/logging.py
import logging
from pythonjsonlogger import jsonlogger

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()

    # GCP-compatible JSON format
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s',
        rename_fields={
            'levelname': 'severity',
            'asctime': 'timestamp'
        }
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

# Usage
logger = setup_logging()
logger.info("Processing PDF", extra={
    "document_id": doc_id,
    "filename": filename,
    "file_size": size,
    "user_id": user_id
})
```

#### Log-based Metrics

```bash
# Create log-based metric for error rate
gcloud logging metrics create backend_errors \
  --description="Backend 5xx errors" \
  --log-filter='resource.type="cloud_run_revision"
    resource.labels.service_name="rag-backend"
    severity>=ERROR'

# Create alert on metric
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Backend Error Rate Alert" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s
```

### 10.3 Alerting

#### Alert Policies

```yaml
Critical Alerts (PagerDuty/SMS):
  - Service down (uptime check fails)
  - Error rate > 5%
  - Database connection failures
  - Disk usage > 90%
  - Budget exceeds 100%

Warning Alerts (Email):
  - Latency p99 > 5s
  - CPU utilization > 80%
  - Memory utilization > 85%
  - Budget exceeds 75%
  - SSL certificate expiring in 30 days

Info Alerts (Slack):
  - Deployment completed
  - Backup completed
  - Unusual traffic spike
```

#### Sample Alert Policy (Terraform)

```hcl
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate - Backend API"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"rag-backend\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "1800s"
  }
}
```

### 10.4 Uptime Checks

```bash
# Create uptime check for frontend
gcloud monitoring uptime create web-uptime-check \
  --resource-type=uptime-url \
  --display-name="Frontend Uptime Check" \
  --http-check-path="/" \
  --monitored-resource=FRONTEND_URL \
  --check-interval=60s \
  --timeout=10s

# Create uptime check for backend API
gcloud monitoring uptime create api-uptime-check \
  --resource-type=uptime-url \
  --display-name="Backend API Uptime Check" \
  --http-check-path="/api/v1/health" \
  --monitored-resource=BACKEND_URL \
  --check-interval=60s
```

### 10.5 Tracing (Cloud Trace)

```python
# Enable distributed tracing
from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Initialize tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add span exporter
span_exporter = CloudTraceSpanExporter()
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(span_exporter)
)

# Instrument code
@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile):
    with tracer.start_as_current_span("upload_document"):
        with tracer.start_as_current_span("save_file"):
            # Save file
            pass

        with tracer.start_as_current_span("process_pdf"):
            # Process PDF
            pass

        with tracer.start_as_current_span("generate_embeddings"):
            # Generate embeddings
            pass
```

---

## 11. Disaster Recovery & Backup

### 11.1 Backup Strategy

#### Cloud SQL Backups

```yaml
Automated Backups:
  Frequency: Daily at 3:00 AM UTC
  Retention: 7 days (production), 3 days (staging)
  Type: Full snapshot
  Location: us-central1 (primary), us-east1 (cross-region)

Point-in-Time Recovery (PITR):
  Enabled: Yes
  Log retention: 7 days
  Recovery point: Any point in last 7 days

On-Demand Backups:
  Frequency: Before major deployments
  Retention: 30 days
  Type: Manual snapshot
```

```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=rag-postgres-instance \
  --description="Pre-deployment backup"

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=rag-postgres-instance \
  --backup-location=us-central1
```

#### Vector Database Backups

**Vertex AI Vector Search**:
- Automatic backups (managed by Google)
- Export index to Cloud Storage for DR

**ChromaDB** (if using Cloud Run):
```bash
# Create snapshot of persistent disk
gcloud compute disks snapshot chromadb-disk \
  --snapshot-names=chromadb-backup-$(date +%Y%m%d) \
  --zone=us-central1-a

# Schedule daily snapshots
gcloud compute resource-policies create snapshot-schedule chromadb-daily \
  --region=us-central1 \
  --max-retention-days=7 \
  --on-source-disk-delete=keep-auto-snapshots \
  --daily-schedule \
  --start-time=02:00
```

#### Cloud Storage Backups

```yaml
Versioning: Enabled
Object Lifecycle:
  - Delete versions older than 30 days
  - Move to Nearline after 90 days (optional)

Cross-Region Replication:
  Source: us-central1
  Destination: us-east1
  Filter: *.pdf
```

```bash
# Enable versioning
gsutil versioning set on gs://rag-app-documents

# Set lifecycle policy
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "numNewerVersions": 5,
          "isLive": false
        }
      }
    ]
  }
}
EOF
gsutil lifecycle set lifecycle.json gs://rag-app-documents
```

### 11.2 Disaster Recovery Plan

#### Recovery Time Objective (RTO) & Recovery Point Objective (RPO)

```yaml
Production:
  RTO: 4 hours
  RPO: 1 hour

Staging:
  RTO: 24 hours
  RPO: 24 hours

Development:
  RTO: N/A
  RPO: N/A
```

#### DR Scenarios

**Scenario 1: Single Service Failure**
```
Impact: One Cloud Run service down
Detection: Uptime check alert
Recovery:
  1. Cloud Run auto-restarts container (automatic)
  2. If persistent failure, rollback to previous revision
  3. Investigate logs, fix issue
RTO: 5-10 minutes
```

**Scenario 2: Regional Outage**
```
Impact: Entire us-central1 region unavailable
Detection: Multiple service alerts
Recovery:
  1. Failover to us-east1 (if multi-region setup)
  2. Or redeploy to alternate region
  3. Update DNS to point to new region
RTO: 2-4 hours (without multi-region), 10 minutes (with multi-region)
```

**Scenario 3: Data Corruption**
```
Impact: Database data corrupted
Detection: Application errors, data validation
Recovery:
  1. Identify corruption time
  2. Restore Cloud SQL from PITR
  3. Restore vector DB from snapshot
  4. Verify data integrity
RTO: 2-3 hours
```

**Scenario 4: Security Breach**
```
Impact: Unauthorized access detected
Detection: Audit logs, anomaly detection
Recovery:
  1. Isolate affected resources
  2. Rotate all credentials
  3. Review audit logs
  4. Restore from clean backup if needed
  5. Update security policies
RTO: 4-8 hours
```

#### DR Runbook

```markdown
# Disaster Recovery Runbook

## Prerequisites
- Access to GCP Console
- gcloud CLI authenticated
- Terraform state access
- Backup verification completed

## Step-by-Step Recovery

### 1. Assess Impact (15 minutes)
- Check Cloud Monitoring dashboards
- Review error logs
- Identify affected services
- Determine root cause

### 2. Communicate (5 minutes)
- Notify stakeholders
- Update status page
- Create incident ticket

### 3. Initiate Recovery (varies)
- Follow scenario-specific recovery steps
- Execute rollback if needed
- Restore from backups if needed

### 4. Verify Recovery (30 minutes)
- Run health checks
- Verify data integrity
- Test critical user flows
- Monitor metrics

### 5. Post-Mortem (after recovery)
- Document incident timeline
- Identify root cause
- Create action items
- Update runbooks
```

### 11.3 High Availability Configuration

#### Cloud SQL High Availability

```bash
# Enable HA for Cloud SQL
gcloud sql instances patch rag-postgres-instance \
  --availability-type=REGIONAL \
  --backup-start-time=03:00 \
  --enable-bin-log
```

**Configuration**:
- Primary instance: us-central1-a
- Standby replica: us-central1-b
- Automatic failover: Enabled
- Failover time: < 2 minutes

#### Multi-Region Deployment (Optional)

```yaml
Primary Region: us-central1
  - All services deployed
  - Active-active traffic

Secondary Region: us-east1 (DR)
  - Cloud SQL read replica
  - Cold standby Cloud Run services
  - Cross-region bucket replication

Traffic Distribution:
  - Global Load Balancer
  - 100% to primary (normal)
  - Automatic failover to secondary
```

---

## 12. Performance Optimization

### 12.1 Current Performance Baseline

```yaml
Metrics (Docker Compose):
  PDF Processing: 5-10 seconds (10MB file)
  Embedding Generation: 2-3 seconds (50 chunks)
  Search Latency: 50-100ms
  LLM Response: 2-5 seconds
  Page Load: 1-2 seconds
```

### 12.2 Target GCP Performance

```yaml
Metrics (GCP Optimized):
  PDF Processing: 3-7 seconds (parallel processing)
  Embedding Generation: 1-2 seconds (GPU/batch optimization)
  Search Latency: 20-50ms (Vertex AI Vector Search)
  LLM Response: 1-3 seconds (regional endpoint)
  Page Load: 500ms-1s (CDN, caching)
```

### 12.3 Optimization Strategies

#### Backend API Optimization

```python
# Enable response caching
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

@app.get("/api/v1/documents/{document_id}")
@cache(expire=300)  # Cache for 5 minutes
async def get_document(document_id: str):
    # ...
    pass

# Database connection pooling
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Batch embedding generation
async def generate_embeddings_batch(chunks: list[str]):
    # Process in batches of 64 instead of 32
    batch_size = 64
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embeddings = embedding_service.encode(batch)
        yield embeddings
```

#### Frontend Optimization

```javascript
// Code splitting
const SearchResults = React.lazy(() => import('./components/SearchResults'));
const ChatInterface = React.lazy(() => import('./components/ChatInterface'));

// Service worker for offline support
// public/service-worker.js
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});

// Compress API responses
import compression from 'compression';
app.use(compression());
```

#### Cloud Run Optimization

```yaml
# Increase CPU during request processing
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: rag-backend
  annotations:
    run.googleapis.com/cpu-throttling: "false"  # Don't throttle CPU when idle
    run.googleapis.com/startup-cpu-boost: "true"  # Boost CPU during startup
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "20"
        autoscaling.knative.dev/target: "70"  # Target 70% CPU utilization
```

#### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at DESC);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_filename ON documents(filename);

-- Optimize queries with EXPLAIN
EXPLAIN ANALYZE SELECT * FROM documents WHERE status = 'completed' ORDER BY uploaded_at DESC LIMIT 10;

-- Vacuuming and analyzing
VACUUM ANALYZE documents;
```

#### CDN & Caching

```yaml
Cloud CDN Configuration:
  Cache Mode: CACHE_ALL_STATIC
  Cache TTL:
    - Static assets: 1 year
    - API responses (cacheable): 5 minutes
    - HTML: 1 hour
  Compression: Enabled (gzip, brotli)

Cache-Control Headers:
  Static Assets: public, max-age=31536000, immutable
  API Responses: public, max-age=300, must-revalidate
  HTML: public, max-age=3600
```

#### Embedding Model Optimization

**Option 1: Use smaller model**
```python
# Current: all-MiniLM-L6-v2 (384 dimensions, 22M parameters)
# Alternative: all-MiniLM-L12-v2 (384 dimensions, better quality)
# Alternative: paraphrase-MiniLM-L3-v2 (384 dimensions, faster)
```

**Option 2: Quantization**
```python
from sentence_transformers import SentenceTransformer
import torch

model = SentenceTransformer('all-MiniLM-L6-v2')
model.half()  # Convert to FP16 (faster, 50% memory)
```

**Option 3: GPU acceleration** (Cloud Run GPU)
```yaml
Service: rag-backend-gpu
CPU: 4 vCPU
Memory: 16 GiB
GPU: 1x NVIDIA T4
Cost: ~$0.50/hour (expensive, use for high-throughput only)
```

### 12.4 Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class RAGUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def search(self):
        self.client.post("/api/v1/search", json={
            "query": "machine learning",
            "top_k": 5,
            "search_mode": "hybrid"
        })

    @task(1)
    def upload(self):
        with open("sample.pdf", "rb") as f:
            self.client.post("/api/v1/documents/upload", files={"file": f})

    @task(2)
    def chat(self):
        self.client.post("/api/v1/chat", json={
            "message": "What is RAG?",
            "use_search_tool": True
        })
```

```bash
# Run load test
locust -f locustfile.py --host=https://api.rag-app.example.com --users=100 --spawn-rate=10
```

---

## 13. Migration Phases

### Phase 1: Foundation (Week 1)

**Objectives**: Set up GCP project, networking, and core infrastructure

**Tasks**:
- [ ] Create GCP project and enable billing
- [ ] Set up Terraform backend (Cloud Storage for state)
- [ ] Create VPC network and subnets
- [ ] Set up Serverless VPC Connector
- [ ] Configure Cloud NAT
- [ ] Set up Artifact Registry
- [ ] Create Secret Manager secrets
- [ ] Set up service accounts and IAM roles
- [ ] Configure Cloud Build triggers

**Deliverables**:
- GCP project fully configured
- Terraform infrastructure code committed
- Service accounts created with appropriate permissions

**Validation**:
- `gcloud projects describe PROJECT_ID` succeeds
- Terraform `plan` runs without errors
- Service accounts listed in IAM

---

### Phase 2: Data Layer (Week 2)

**Objectives**: Provision and migrate databases and storage

**Tasks**:
- [ ] Provision Cloud SQL instance
- [ ] Configure Cloud SQL backups and HA
- [ ] Export PostgreSQL data from current system
- [ ] Import data to Cloud SQL
- [ ] Validate data integrity (row counts, checksums)
- [ ] Create Cloud Storage buckets
- [ ] Migrate PDF files to Cloud Storage
- [ ] Set up bucket lifecycle policies
- [ ] Provision Vertex AI Vector Search (or ChromaDB)
- [ ] Migrate embeddings to vector database
- [ ] Test vector search queries

**Deliverables**:
- Cloud SQL instance with migrated data
- Cloud Storage buckets with all files
- Vector database with embeddings

**Validation**:
- Database query results match current system
- All PDF files accessible in Cloud Storage
- Vector search returns expected results

---

### Phase 3: Backend Services (Week 3)

**Objectives**: Deploy backend API and LLM service

**Tasks**:
- [ ] Update backend code for GCP (connection strings, etc.)
- [ ] Build and push Docker images to Artifact Registry
- [ ] Deploy LLM service to Cloud Run
- [ ] Test LLM service endpoints
- [ ] Deploy Backend API to Cloud Run
- [ ] Configure environment variables and secrets
- [ ] Test API endpoints (CRUD operations)
- [ ] Set up Cloud Run VPC connector
- [ ] Configure Cloud Run autoscaling
- [ ] Implement health checks

**Deliverables**:
- LLM service running on Cloud Run
- Backend API running on Cloud Run
- All API endpoints functional

**Validation**:
- Health check returns 200 OK
- Document upload succeeds
- Search queries return results
- Chat functionality works

---

### Phase 4: File Processing (Week 3)

**Objectives**: Set up serverless file processing

**Tasks**:
- [ ] Migrate file watcher code to Cloud Function
- [ ] Configure Cloud Storage trigger (OBJECT_FINALIZE)
- [ ] Deploy Cloud Function
- [ ] Test file upload → processing flow
- [ ] Set up Pub/Sub topic for processing events (optional)
- [ ] Configure Cloud Function timeout and memory
- [ ] Implement retry logic for failures

**Deliverables**:
- Cloud Function deployed and triggered by uploads
- End-to-end PDF processing workflow functional

**Validation**:
- Upload PDF to Cloud Storage
- Verify Cloud Function triggered
- Verify document processed and searchable

---

### Phase 5: Frontend (Week 4)

**Objectives**: Deploy frontend and configure load balancing

**Tasks**:
- [ ] Update frontend API URLs for GCP backend
- [ ] Build and push frontend Docker image
- [ ] Deploy frontend to Cloud Run
- [ ] Configure Cloud Load Balancer
- [ ] Set up SSL certificate (managed or custom)
- [ ] Configure Cloud CDN
- [ ] Set up custom domain (DNS)
- [ ] Test frontend functionality

**Deliverables**:
- Frontend accessible via HTTPS
- Load balancer routing traffic correctly
- CDN serving static assets

**Validation**:
- Frontend loads without errors
- All features functional (upload, search, chat)
- SSL certificate valid
- CDN cache hit ratio > 50%

---

### Phase 6: Monitoring & Observability (Week 4-5)

**Objectives**: Set up comprehensive monitoring and alerting

**Tasks**:
- [ ] Create Cloud Monitoring dashboards
- [ ] Configure uptime checks
- [ ] Set up log-based metrics
- [ ] Create alert policies
- [ ] Configure notification channels (email, Slack)
- [ ] Enable Cloud Trace for distributed tracing
- [ ] Set up Error Reporting
- [ ] Configure budget alerts

**Deliverables**:
- Monitoring dashboards for all services
- Alert policies for critical metrics
- Logging pipeline operational

**Validation**:
- Dashboards show real-time metrics
- Test alerts trigger correctly
- Logs searchable in Cloud Logging

---

### Phase 7: Integration Testing (Week 5)

**Objectives**: Comprehensive end-to-end testing

**Tasks**:
- [ ] Functional testing (all features)
- [ ] Performance testing (load tests)
- [ ] Security testing (penetration testing)
- [ ] Disaster recovery testing (backup restore)
- [ ] Failover testing (if HA configured)
- [ ] User acceptance testing (UAT)
- [ ] Documentation review

**Deliverables**:
- Test reports for all test types
- Bug fixes for issues found
- Updated documentation

**Validation**:
- All tests pass
- Performance meets or exceeds baseline
- No critical security vulnerabilities

---

### Phase 8: Production Cutover (Week 6)

**Objectives**: Switch production traffic to GCP

**Tasks**:
- [ ] Final data sync (incremental)
- [ ] DNS cutover preparation
- [ ] Communicate maintenance window to users
- [ ] Final backup of current system
- [ ] Update DNS records to point to GCP
- [ ] Monitor traffic and errors
- [ ] Verify all functionality
- [ ] Keep current system running (warm standby)
- [ ] Decommission old system after 1 week

**Deliverables**:
- Production traffic on GCP
- Current system in standby mode

**Validation**:
- No increase in error rates
- User traffic flows to GCP
- All features functional

---

### Phase 9: Optimization (Ongoing)

**Objectives**: Optimize cost, performance, and reliability

**Tasks**:
- [ ] Review Cloud Monitoring metrics
- [ ] Optimize resource allocation (CPU, memory)
- [ ] Implement caching strategies
- [ ] Fine-tune autoscaling parameters
- [ ] Review and optimize costs
- [ ] Implement advanced security features
- [ ] Performance tuning based on real usage
- [ ] Documentation updates

**Deliverables**:
- Optimized infrastructure
- Cost reduction of 10-20%
- Improved performance metrics

---

## 14. Testing Strategy

### 14.1 Pre-Migration Testing

#### Unit Testing
```python
# tests/test_pdf_processor.py
import pytest
from app.services.pdf_processor import PDFProcessor

def test_pdf_extraction():
    processor = PDFProcessor()
    result = processor.extract_text("test.pdf")
    assert result is not None
    assert len(result) > 0

def test_chunking():
    processor = PDFProcessor()
    text = "Sample text " * 100
    chunks = processor.chunk_text(text, chunk_size=100)
    assert len(chunks) > 0
    assert all(len(chunk) <= 100 for chunk in chunks)
```

#### Integration Testing
```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_upload_document():
    async with AsyncClient(app=app, base_url="http://test") as client:
        with open("test.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", f, "application/pdf")}
            )
    assert response.status_code == 200
    assert "document_id" in response.json()
```

### 14.2 Migration Testing

#### Data Validation
```python
# scripts/validate_migration.py
import asyncpg
from chromadb import HttpClient

async def validate_postgres_migration():
    # Connect to current and new database
    current = await asyncpg.connect(CURRENT_DB_URL)
    new = await asyncpg.connect(CLOUD_SQL_URL)

    # Compare row counts
    current_count = await current.fetchval("SELECT COUNT(*) FROM documents")
    new_count = await new.fetchval("SELECT COUNT(*) FROM documents")

    assert current_count == new_count, f"Row count mismatch: {current_count} vs {new_count}"

    # Compare sample data
    current_sample = await current.fetch("SELECT * FROM documents LIMIT 100")
    new_sample = await new.fetch("SELECT * FROM documents LIMIT 100")

    # ... validate data integrity

def validate_vector_db_migration():
    current_client = HttpClient(host="localhost", port=8001)
    new_client = HttpClient(host=VERTEX_AI_ENDPOINT)

    current_collection = current_client.get_collection("documents")

    # Compare counts
    current_count = current_collection.count()
    # Query new system
    # ... validate embeddings match
```

#### Smoke Testing
```bash
# scripts/smoke_test.sh
#!/bin/bash

BASE_URL="https://api.rag-app.example.com"

# Test health endpoint
echo "Testing health endpoint..."
curl -f $BASE_URL/health || exit 1

# Test document upload
echo "Testing document upload..."
curl -f -X POST $BASE_URL/api/v1/documents/upload \
  -F "file=@test.pdf" || exit 1

# Test search
echo "Testing search..."
curl -f -X POST $BASE_URL/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}' || exit 1

# Test chat
echo "Testing chat..."
curl -f -X POST $BASE_URL/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}' || exit 1

echo "All smoke tests passed!"
```

### 14.3 Performance Testing

```python
# Load testing with Locust
from locust import HttpUser, task, between

class RAGLoadTest(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Upload test document
        with open("test.pdf", "rb") as f:
            self.client.post("/api/v1/documents/upload", files={"file": f})

    @task(5)
    def search_documents(self):
        self.client.post("/api/v1/search", json={
            "query": "machine learning",
            "top_k": 10
        })

    @task(3)
    def chat(self):
        self.client.post("/api/v1/chat", json={
            "message": "What is RAG?",
            "use_search_tool": True
        })

    @task(1)
    def list_documents(self):
        self.client.get("/api/v1/documents")
```

```bash
# Run load test
locust -f load_test.py \
  --host=https://api.rag-app.example.com \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m \
  --html=load_test_report.html
```

### 14.4 Security Testing

```yaml
Security Checklist:
  - [ ] OWASP Top 10 vulnerabilities checked
  - [ ] SQL injection testing
  - [ ] XSS (Cross-Site Scripting) testing
  - [ ] CSRF (Cross-Site Request Forgery) testing
  - [ ] Authentication bypass testing
  - [ ] Authorization testing
  - [ ] Secrets not exposed in logs
  - [ ] SSL/TLS configuration validated
  - [ ] CORS properly configured
  - [ ] Rate limiting effective
  - [ ] Container image scanning (no critical CVEs)
  - [ ] Dependency vulnerability scanning
```

```bash
# Container image scanning
gcloud container images scan $ARTIFACT_REGISTRY/rag-backend:latest

# Dependency vulnerability check
pip install safety
safety check -r requirements.txt
```

---

## 15. Rollback Plan

### 15.1 Rollback Scenarios

#### Scenario 1: Critical Bug in New Deployment

**Detection**: High error rate, user reports, monitoring alerts

**Rollback Procedure**:
1. **Immediate** (1-2 minutes):
   ```bash
   # Rollback Cloud Run services to previous revision
   gcloud run services update-traffic rag-backend \
     --to-revisions=PREVIOUS_REVISION=100

   gcloud run services update-traffic rag-frontend \
     --to-revisions=PREVIOUS_REVISION=100
   ```

2. **DNS Cutover** (5-10 minutes):
   ```bash
   # Point DNS back to old system
   gcloud dns record-sets transaction start --zone=rag-app-zone
   gcloud dns record-sets transaction remove \
     --name=app.rag-app.example.com \
     --ttl=300 \
     --type=A \
     "NEW_IP_ADDRESS" \
     --zone=rag-app-zone
   gcloud dns record-sets transaction add \
     --name=app.rag-app.example.com \
     --ttl=300 \
     --type=A \
     "OLD_IP_ADDRESS" \
     --zone=rag-app-zone
   gcloud dns record-sets transaction execute --zone=rag-app-zone
   ```

3. **Data Rollback** (if needed):
   ```bash
   # Restore Cloud SQL from backup
   gcloud sql backups restore BACKUP_ID \
     --backup-instance=rag-postgres-instance
   ```

#### Scenario 2: Data Migration Issue

**Detection**: Data validation failures, missing documents

**Rollback Procedure**:
1. **Immediate**: Switch traffic back to old system (DNS)
2. **Investigate**: Identify data discrepancies
3. **Re-migrate**: Fix migration scripts, re-run migration
4. **Validate**: Comprehensive data validation
5. **Retry cutover**: When data is validated

#### Scenario 3: Performance Degradation

**Detection**: High latency, timeouts, slow responses

**Rollback Procedure**:
1. **Scale up** resources first (may resolve without rollback):
   ```bash
   gcloud run services update rag-backend \
     --cpu=4 \
     --memory=8Gi \
     --min-instances=5
   ```

2. If scaling doesn't help, **rollback** to old system
3. **Investigate** performance bottlenecks
4. **Optimize** before retry

### 15.2 Rollback Decision Matrix

| Severity | Condition | Action | Timeline |
|----------|-----------|--------|----------|
| **Critical** | Service completely down, data loss | Immediate rollback to old system | < 15 min |
| **High** | Error rate > 10%, major feature broken | Rollback Cloud Run revisions | < 30 min |
| **Medium** | Error rate 5-10%, minor issues | Investigate, fix forward if possible | 1-2 hours |
| **Low** | Performance degradation, non-critical bugs | Fix forward, no rollback | N/A |

### 15.3 Rollback Checklist

**Pre-Rollback**:
- [ ] Confirm rollback is necessary (error rate, severity)
- [ ] Notify stakeholders (incident declared)
- [ ] Document current state (logs, metrics screenshots)
- [ ] Identify rollback target (previous revision, old system)

**During Rollback**:
- [ ] Execute rollback procedure (see scenarios above)
- [ ] Monitor error rates and traffic
- [ ] Verify old system operational
- [ ] Update status page

**Post-Rollback**:
- [ ] Verify full functionality restored
- [ ] Collect logs and data for investigation
- [ ] Schedule post-mortem
- [ ] Create bug tickets for issues found
- [ ] Plan retry with fixes

---

## 16. Post-Migration Tasks

### 16.1 Immediate Tasks (Week 1 after cutover)

- [ ] Monitor all services 24/7 for first 3 days
- [ ] Address any performance issues
- [ ] Fine-tune autoscaling parameters
- [ ] Review and optimize costs
- [ ] Conduct user feedback survey
- [ ] Update documentation with any changes
- [ ] Archive old system (keep for 1-2 weeks)

### 16.2 Short-Term Tasks (Month 1)

- [ ] Comprehensive post-migration review
- [ ] Optimize resource allocation based on usage
- [ ] Implement advanced caching strategies
- [ ] Set up advanced monitoring (SLOs, error budgets)
- [ ] Security hardening (implement WAF rules)
- [ ] Performance optimization
- [ ] Decommission old infrastructure
- [ ] Cost optimization (Reserved instances, CUD)

### 16.3 Long-Term Tasks (Month 2-3)

- [ ] Implement multi-region deployment (if needed)
- [ ] Set up CI/CD for automated deployments
- [ ] Implement blue-green deployment strategy
- [ ] Advanced security features (DLP, VPC Service Controls)
- [ ] Implement cost allocation and chargeback
- [ ] Optimize for sustainability (carbon footprint)
- [ ] Implement advanced analytics and reporting
- [ ] Plan for future scaling and features

### 16.4 Documentation Updates

- [ ] Update architecture diagrams
- [ ] Update deployment documentation
- [ ] Update troubleshooting guides
- [ ] Update DR procedures
- [ ] Update team runbooks
- [ ] Create knowledge base articles

---

## 17. Appendix

### A. Useful Commands

#### gcloud CLI Commands
```bash
# Authentication
gcloud auth login
gcloud auth application-default login

# Project management
gcloud config set project PROJECT_ID
gcloud projects list

# Cloud Run
gcloud run services list
gcloud run services describe rag-backend --region=us-central1
gcloud run services logs read rag-backend --region=us-central1

# Cloud SQL
gcloud sql instances list
gcloud sql connect rag-postgres-instance --user=raguser
gcloud sql operations list --instance=rag-postgres-instance

# Cloud Storage
gsutil ls gs://rag-app-documents
gsutil du -sh gs://rag-app-documents
gsutil cp local-file.pdf gs://rag-app-documents/

# Logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=rag-backend" --limit=50

# Monitoring
gcloud monitoring dashboards list
gcloud monitoring policies list
```

#### Terraform Commands
```bash
# Initialize
cd terraform/environments/production
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Destroy (careful!)
terraform destroy

# Import existing resource
terraform import google_cloud_run_service.backend projects/PROJECT_ID/locations/us-central1/services/rag-backend
```

### B. Reference Links

**GCP Documentation**:
- Cloud Run: https://cloud.google.com/run/docs
- Cloud SQL: https://cloud.google.com/sql/docs
- Cloud Storage: https://cloud.google.com/storage/docs
- Vertex AI: https://cloud.google.com/vertex-ai/docs
- Cloud Functions: https://cloud.google.com/functions/docs

**Terraform**:
- Google Provider: https://registry.terraform.io/providers/hashicorp/google/latest/docs
- Cloud Run Module: https://registry.terraform.io/modules/terraform-google-modules/cloud-run/google/latest

**Best Practices**:
- Cloud Run Best Practices: https://cloud.google.com/run/docs/best-practices
- Cloud SQL Best Practices: https://cloud.google.com/sql/docs/postgres/best-practices
- Cost Optimization: https://cloud.google.com/cost-management/docs/best-practices

### C. Troubleshooting Guide

#### Common Issues

**Issue 1: Cloud Run Cold Starts**
```yaml
Problem: First request takes 10+ seconds
Solution:
  - Set min-instances=1 for critical services
  - Enable CPU allocation during request processing only
  - Optimize container image size
  - Use startup CPU boost
```

**Issue 2: Cloud SQL Connection Errors**
```yaml
Problem: "connection refused" errors
Solution:
  - Verify VPC connector configured
  - Check service account has cloudsql.client role
  - Use Cloud SQL Proxy for local testing
  - Check connection string format: /cloudsql/PROJECT:REGION:INSTANCE
```

**Issue 3: High Costs**
```yaml
Problem: Unexpected high billing
Solution:
  - Check min-instances (set to 0 for non-production)
  - Review Cloud SQL tier (downgrade if over-provisioned)
  - Enable Cloud CDN caching
  - Review egress costs (Cloud NAT, internet)
  - Use cost breakdown in Billing reports
```

**Issue 4: Vector Search Performance**
```yaml
Problem: Slow search queries
Solution:
  - Increase Vertex AI endpoint replicas
  - Optimize query parameters (top_k)
  - Use approximate search instead of exact
  - Batch queries when possible
  - Consider caching frequent queries
```

### D. Contact Information

```yaml
Project Owner: [Your Name]
Email: your-email@example.com

GCP Support:
  - Tier: Premium Support (if applicable)
  - Case Portal: https://cloud.google.com/support

Emergency Contacts:
  - On-Call Engineer: [Phone]
  - Team Lead: [Phone]
  - GCP Account Manager: [Email]

Escalation Path:
  1. On-Call Engineer
  2. Team Lead
  3. GCP Support
  4. GCP Account Manager
```

---

## Conclusion

This comprehensive migration guide provides a structured approach to migrating your RAG application to Google Cloud Platform. The migration will result in:

- **Improved Scalability**: Auto-scaling from 0 to 100+ instances
- **Enhanced Reliability**: 99.9%+ uptime with managed services
- **Better Performance**: Regional CDN, optimized networking
- **Reduced Operational Overhead**: Managed databases, serverless compute
- **Enterprise Security**: IAM, encryption, audit logging
- **Cost Efficiency**: Pay-per-use model with optimization opportunities

**Next Steps**:
1. Review this document with your team
2. Set up a GCP project and enable billing
3. Start with Phase 1 (Foundation)
4. Follow the migration phases sequentially
5. Reach out for support as needed

**Success Metrics** (90 days post-migration):
- Zero unplanned downtime
- 99.9% uptime
- Cost within budget (±10%)
- Improved performance vs. baseline
- Team proficient in GCP operations

Good luck with your migration!

---

**Document History**:
- v1.0 (2025-11-19): Initial comprehensive migration guide created
