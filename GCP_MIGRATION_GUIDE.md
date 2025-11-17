# GCP Migration Guide - File Watcher Service

This document explains how to migrate the File Watcher Service from the current Docker-based implementation to Google Cloud Platform (GCP) services.

## Current Architecture vs GCP Architecture

### Current (Docker/Local)
```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Local Folder   │────►│ File Watcher │────►│   Backend   │
│  (/data/watch)  │     │  (Watchdog)  │     │   (FastAPI) │
└─────────────────┘     └──────────────┘     └─────────────┘
         │                       │                    │
    File System             HTTP POST            Process PDF
      Events                                    Store Vectors
```

### GCP Architecture
```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  Cloud Storage  │────►│   Pub/Sub    │────►│Cloud Function│────►│  Cloud Run  │
│     Bucket      │     │    Topic     │     │  (Trigger)   │     │  (Backend)  │
└─────────────────┘     └──────────────┘     └──────────────┘     └─────────────┘
         │                       │                    │                    │
    Object Finalize         Message            Process Event        Process PDF
      Notification         Routing              Forward to           Store in
                                                 Backend              Vertex AI
```

## Migration Steps

### 1. Set Up GCP Resources

```bash
# Set your project
export PROJECT_ID=your-project-id
export REGION=us-central1

gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudfunctions.googleapis.com \
  pubsub.googleapis.com \
  storage.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com
```

### 2. Create Cloud Storage Bucket

```bash
# Create bucket for PDF uploads
gsutil mb -l $REGION gs://${PROJECT_ID}-pdf-uploads

# Set lifecycle policy (optional - auto-delete old processed files)
cat > lifecycle.json << 'EOF'
{
  "rule": [{
    "action": {"type": "Delete"},
    "condition": {"age": 90}
  }]
}
EOF

gsutil lifecycle set lifecycle.json gs://${PROJECT_ID}-pdf-uploads
```

### 3. Create Pub/Sub Topic

```bash
# Create topic for storage notifications
gcloud pubsub topics create pdf-upload-notifications

# Create subscription (for monitoring/debugging)
gcloud pubsub subscriptions create pdf-upload-sub \
  --topic=pdf-upload-notifications \
  --ack-deadline=600
```

### 4. Configure Cloud Storage Notifications

```bash
# Send OBJECT_FINALIZE events to Pub/Sub
gsutil notification create \
  -t projects/${PROJECT_ID}/topics/pdf-upload-notifications \
  -f json \
  -e OBJECT_FINALIZE \
  gs://${PROJECT_ID}-pdf-uploads
```

### 5. Deploy Backend to Cloud Run

```bash
# Build and push backend image
cd backend

# Create Artifact Registry repository
gcloud artifacts repositories create rag-images \
  --repository-format=docker \
  --location=$REGION

# Build with Cloud Build
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-images/backend:latest

# Deploy to Cloud Run
gcloud run deploy rag-backend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/rag-images/backend:latest \
  --platform=managed \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=300 \
  --set-env-vars="
    CHROMA_HOST=your-chromadb-host,
    POSTGRES_HOST=your-postgres-host,
    GCS_ENABLED=true,
    GCS_BUCKET=${PROJECT_ID}-pdf-uploads
  "
```

### 6. Create Cloud Function for Event Processing

Create `cloud_function/main.py`:

```python
"""
Cloud Function to handle Cloud Storage events.
Replaces the File Watcher Service in GCP.
"""
import json
import base64
import requests
from google.cloud import storage
import functions_framework

# Configuration
BACKEND_URL = "https://rag-backend-xxxxx-uc.a.run.app"
PROCESS_ENDPOINT = "/api/v1/documents/process-file"


@functions_framework.cloud_event
def process_pdf_upload(cloud_event):
    """
    Triggered by Cloud Storage OBJECT_FINALIZE event via Pub/Sub.

    This function replaces the entire File Watcher Service:
    - Watchdog monitoring → Cloud Storage notifications
    - Event detection → Pub/Sub message
    - HTTP publishing → This function calling Cloud Run
    """
    # Parse the Pub/Sub message
    data = cloud_event.data

    # Get storage event details
    if "message" in data:
        message_data = base64.b64decode(data["message"]["data"]).decode()
        storage_event = json.loads(message_data)
    else:
        storage_event = data

    bucket_name = storage_event.get("bucket")
    file_name = storage_event.get("name")
    file_size = int(storage_event.get("size", 0))

    # Validate file
    if not file_name.lower().endswith('.pdf'):
        print(f"Skipping non-PDF file: {file_name}")
        return

    print(f"Processing PDF: {file_name} from bucket {bucket_name}")

    # Create event payload (matches current FileEvent schema)
    event_payload = {
        "event_type": "OBJECT_FINALIZE",
        "file_path": f"gs://{bucket_name}/{file_name}",
        "file_name": file_name,
        "file_size": file_size,
        "bucket": bucket_name,
        "timestamp": storage_event.get("timeCreated"),
        "event_id": storage_event.get("generation", "")
    }

    # Call backend API
    url = f"{BACKEND_URL}{PROCESS_ENDPOINT}"

    try:
        response = requests.post(
            url,
            json=event_payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes for processing
        )

        if response.status_code in [200, 201, 202]:
            result = response.json()
            print(f"Successfully processed {file_name}: {result}")
        else:
            print(f"Backend error {response.status_code}: {response.text}")
            raise Exception(f"Processing failed: {response.text}")

    except requests.Timeout:
        print(f"Timeout processing {file_name}")
        raise
    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        raise


# Alternative: HTTP trigger for direct invocation
@functions_framework.http
def process_pdf_http(request):
    """
    HTTP endpoint for manual triggering or testing.
    """
    request_json = request.get_json(silent=True)

    if not request_json:
        return {"error": "No JSON payload"}, 400

    # Process the event
    process_pdf_upload(request_json)

    return {"status": "processed"}, 200
```

Create `cloud_function/requirements.txt`:

```txt
functions-framework==3.*
google-cloud-storage==2.*
requests==2.*
```

Deploy the Cloud Function:

```bash
cd cloud_function

gcloud functions deploy process-pdf-upload \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=process_pdf_upload \
  --trigger-topic=pdf-upload-notifications \
  --memory=512MB \
  --timeout=540s \
  --set-env-vars="BACKEND_URL=https://rag-backend-xxxxx-uc.a.run.app"
```

### 7. Update Backend for GCS Support

Add to `backend/app/core/config.py`:

```python
# GCP Cloud Storage settings
GCS_ENABLED: bool = False
GCS_BUCKET: str = ""
GCS_CREDENTIALS_PATH: str = ""
```

Update `backend/app/api/routes/documents.py`:

```python
from google.cloud import storage

@router.post("/process-file", response_model=ProcessFileResponse)
async def process_file_from_watcher(
    request: ProcessFileRequest,
    db: Session = Depends(get_db)
):
    # Check if this is a GCS path
    if request.file_path.startswith("gs://"):
        # Download from GCS
        storage_client = storage.Client()

        # Parse GCS path
        parts = request.file_path[5:].split("/", 1)
        bucket_name = parts[0]
        blob_name = parts[1]

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Download to temp location
        local_path = f"/tmp/{request.file_name}"
        blob.download_to_filename(local_path)

        # Update request to use local path
        request.file_path = local_path

    # Continue with existing processing logic...
```

### 8. Set Up Authentication

```bash
# Create service account for Cloud Function
gcloud iam service-accounts create pdf-processor \
  --display-name="PDF Processing Function"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pdf-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"

gcloud run services add-iam-policy-binding rag-backend \
  --region=$REGION \
  --member="serviceAccount:pdf-processor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Component Mapping

| Current Component | GCP Service | Migration Effort |
|-------------------|-------------|------------------|
| `FolderWatcher` | Cloud Storage Notifications | Replace entirely |
| `PDFFileHandler` | Cloud Storage Event | Replace entirely |
| `EventPublisher` | Pub/Sub | Replace `DirectHTTPPublisher` with native Pub/Sub |
| `FileTracker` | Cloud Storage metadata / Firestore | Partial replacement |
| Backend `/process-file` | Cloud Run | Minor updates (GCS download) |
| ChromaDB | Vertex AI Vector Search | Optional upgrade |
| PostgreSQL | Cloud SQL | Direct migration |

## Configuration Changes

### Environment Variables Mapping

| Docker Env | GCP Equivalent |
|------------|----------------|
| `WATCHER_WATCH_FOLDER` | GCS bucket name |
| `WATCHER_BACKEND_URL` | Cloud Run URL |
| `WATCHER_FILE_STABILITY_THRESHOLD` | Not needed (GCS handles) |
| `WATCHER_MAX_RETRIES` | Cloud Function retry policy |
| `WATCHER_PROCESS_EXISTING_ON_STARTUP` | Not applicable |

### GCP-Specific Configuration

```bash
# Cloud Function environment
BACKEND_URL=https://rag-backend-xxxxx-uc.a.run.app
GCS_BUCKET=your-project-pdf-uploads

# Cloud Run environment (backend)
GCS_ENABLED=true
GCS_BUCKET=your-project-pdf-uploads
CHROMA_HOST=your-chromadb-instance
POSTGRES_HOST=your-cloudsql-ip
```

## Benefits of GCP Migration

1. **Scalability**: Auto-scales with load, no manual container management
2. **Reliability**: Built-in retry logic, dead letter queues
3. **Cost Efficiency**: Pay per invocation (no idle container)
4. **Global Availability**: Deploy to multiple regions
5. **Managed Services**: No infrastructure maintenance
6. **Security**: IAM, VPC Service Controls, data encryption
7. **Monitoring**: Cloud Monitoring, Cloud Logging integrated
8. **Event Ordering**: Pub/Sub guarantees at-least-once delivery

## Monitoring & Observability

### Cloud Logging

```bash
# View Cloud Function logs
gcloud functions logs read process-pdf-upload --region=$REGION

# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit=100
```

### Cloud Monitoring

Set up alerts for:
- Function execution errors
- Processing latency > 60 seconds
- Cloud Run error rate > 1%
- Pub/Sub message backlog > 100

### Dashboard Example

```bash
# Create custom dashboard
gcloud monitoring dashboards create \
  --config-from-file=dashboard.json
```

## Cost Estimation

### Current (Docker)
- Container running 24/7
- Fixed cost regardless of usage
- ~$50-100/month for small VM

### GCP (Serverless)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| Cloud Storage | 10GB storage | ~$0.23 |
| Pub/Sub | 1000 messages | ~$0.04 |
| Cloud Functions | 1000 invocations | ~$0.40 |
| Cloud Run | 1000 requests, 60s each | ~$2.00 |
| **Total** | | **~$2.67** |

*For 1000 PDFs/month processed*

## Testing the Migration

1. **Upload Test PDF**:
```bash
gsutil cp test.pdf gs://${PROJECT_ID}-pdf-uploads/
```

2. **Check Pub/Sub**:
```bash
gcloud pubsub subscriptions pull pdf-upload-sub --auto-ack
```

3. **Check Cloud Function Logs**:
```bash
gcloud functions logs read process-pdf-upload --region=$REGION --limit=10
```

4. **Verify Processing**:
```bash
curl https://rag-backend-xxxxx-uc.a.run.app/api/v1/documents/
```

## Rollback Plan

If issues occur:

1. Disable Cloud Storage notifications:
```bash
gsutil notification list gs://${PROJECT_ID}-pdf-uploads
gsutil notification delete <notification-id> gs://${PROJECT_ID}-pdf-uploads
```

2. Re-enable File Watcher Service in Docker Compose

3. Switch backend to local file system mode

## Future Enhancements

1. **Vertex AI Vector Search**: Replace ChromaDB with managed vector search
2. **Cloud Tasks**: For long-running PDF processing with better retry
3. **Workflows**: Orchestrate complex multi-step processing
4. **Eventarc**: Advanced event routing and filtering
5. **Document AI**: Advanced PDF parsing with layout understanding

---

**Summary**: The File Watcher Service was intentionally designed with GCP migration in mind. The event schema matches GCS notifications, the publisher abstraction allows easy swapping to Pub/Sub, and the stateless design maps perfectly to Cloud Functions. Migration requires minimal code changes to the backend and completely replaces the watcher service with managed GCP infrastructure.
