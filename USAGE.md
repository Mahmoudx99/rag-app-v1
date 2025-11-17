
# 📘 RAG Knowledge Base - Usage Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Uploading Documents](#uploading-documents)
3. [Searching Documents](#searching-documents)
4. [Managing Documents](#managing-documents)
5. [Understanding the System](#understanding-the-system)
6. [Troubleshooting](#troubleshooting)

## Getting Started

### Starting the Application

```bash
cd rag_app
./start.sh
```

Or manually:

```bash
docker-compose up -d
```

### Accessing the Interface

Open your browser and navigate to:
- **Web UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

## Uploading Documents

### Via Web Interface

1. **Navigate to Documents Tab**
   - Click on the "📚 Documents" tab at the top

2. **Upload a PDF**
   - **Option A**: Drag and drop a PDF file into the upload area
   - **Option B**: Click the upload area and select a file

3. **Wait for Processing**
   - System extracts text using plain mode
   - Text is chunked into paragraphs (1000 chars, 200 overlap)
   - Embeddings are generated (384 dimensions)
   - Stored in ChromaDB for searching

4. **Verify Upload**
   - Document appears in the documents list
   - Status shows "✅ Completed"
   - Chunk count is displayed

### Via API

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/your/document.pdf"
```

## Searching Documents

### Via Web Interface

1. **Navigate to Search Tab**
   - Click on the "🔍 Search" tab

2. **Enter Your Query**
   - Type a natural language question or search term
   - Examples:
     - "What is machine learning?"
     - "Explain artificial intelligence"
     - "Benefits of using RAG"

3. **Select Number of Results**
   - Choose Top 3, 5, or 10 results
   - More results = broader coverage but potentially less relevant

4. **View Results**
   - Results are ranked by similarity score
   - Each result shows:
     - **Match percentage**: How relevant the chunk is
     - **Content**: The actual text from the document
     - **Source**: Which document it came from
     - **Metadata**: Chunk index, word count, etc.

### Search Tips

**Good Queries:**
- ✅ "What are the main benefits of AI?"
- ✅ "How does machine learning work?"
- ✅ "Explain the concept of embeddings"

**Less Effective:**
- ❌ Single words like "AI" or "learning"
- ❌ Very short queries
- ❌ Queries with only stop words

### Via API

```bash
curl -X POST "http://localhost:8000/api/v1/search/" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "top_k": 5
  }'
```

## Managing Documents

### Viewing Documents

The Documents tab shows all uploaded PDFs with:
- **Filename**: Original PDF name
- **Status**: Processing state
- **Metadata**: Title, author, pages
- **Chunks**: Number of text chunks created
- **Upload Time**: When the document was added

### Deleting Documents

1. **Find the Document**
   - Go to Documents tab
   - Locate the document to delete

2. **Click Delete Button**
   - Click the "🗑️ Delete" button on the document card
   - Confirm the deletion

3. **What Gets Deleted**
   - ✅ PDF file from storage
   - ✅ Database record
   - ✅ All embeddings from ChromaDB
   - ✅ All associated chunks

### Via API

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/1"
```

## Understanding the System

### How It Works

```
1. Upload PDF
   ↓
2. Extract Text (Plain Mode)
   ↓
3. Chunk Text (Paragraph Strategy)
   ↓
4. Generate Embeddings (all-MiniLM-L6-v2)
   ↓
5. Store in ChromaDB
   ↓
6. Ready for Search!
```

### Chunking Strategy

**Paragraph-based Chunking:**
- Respects natural paragraph boundaries
- Target size: 1000 characters
- Overlap: 200 characters
- Ensures context preservation

**Why Paragraphs?**
- ✅ Maintains semantic coherence
- ✅ Better search quality
- ✅ Natural information units
- ✅ Easier to read results

### Embedding Model

**Model**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Speed**: Fast (~500-1000 chunks/sec)
- **Quality**: Good for general-purpose search
- **Language**: English (optimized)

### Storage Architecture

```
PostgreSQL
├── Documents table
│   ├── Metadata (title, author, pages)
│   ├── Upload info (time, status)
│   └── Chunk IDs (references to ChromaDB)

ChromaDB
├── Vector embeddings (384 dims)
├── Chunk text content
└── Metadata (source, index, etc.)

File System
└── Original PDF files
```

## Troubleshooting

### Upload Fails

**Problem**: Upload doesn't complete

**Solutions**:
1. Check file size (max 50MB)
2. Ensure file is a valid PDF
3. Check backend logs: `docker-compose logs backend`
4. Verify disk space

### Search Returns No Results

**Problem**: Query returns empty results

**Solutions**:
1. Upload more documents
2. Try different query phrasings
3. Check if documents processed successfully
4. Verify ChromaDB has embeddings:
   ```bash
   docker-compose logs backend | grep "Successfully added"
   ```

### Slow Processing

**Problem**: Documents take long to process

**Causes**:
- Large PDF files
- Complex layouts
- Limited CPU resources

**Solutions**:
1. Allocate more CPU to Docker
2. Process smaller PDFs first
3. Check system resources
4. Review logs for bottlenecks

### Service Won't Start

**Problem**: Docker services fail to start

**Solutions**:
1. Check Docker is running
2. Verify ports 3000, 8000, 5432 are available
3. Check logs: `docker-compose logs`
4. Rebuild: `docker-compose up --build`
5. Clean restart: `docker-compose down -v && docker-compose up`

### Database Connection Error

**Problem**: Backend can't connect to PostgreSQL

**Solutions**:
1. Wait for PostgreSQL to be ready (takes ~10 seconds)
2. Check PostgreSQL health:
   ```bash
   docker-compose ps postgres
   ```
3. Restart services:
   ```bash
   docker-compose restart backend
   ```

### Memory Issues

**Problem**: System runs out of memory

**Solutions**:
1. Increase Docker memory limit
2. Process fewer documents at once
3. Reduce batch size in `.env`:
   ```
   BATCH_SIZE=16
   ```
4. Use smaller embedding model

## Advanced Usage

### Customizing Chunk Size

Edit `.env`:

```bash
CHUNK_SIZE=500      # Smaller chunks, more granular
CHUNK_OVERLAP=100   # Adjust overlap accordingly
```

Then restart:
```bash
docker-compose restart backend
```

### Using Different Embedding Models

Edit `.env`:

```bash
# Better quality (but slower)
EMBEDDING_MODEL=all-mpnet-base-v2
EMBEDDING_DIMENSION=768

# Multilingual support
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384
```

Rebuild:
```bash
docker-compose up --build backend
```

### Backing Up Data

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U raguser ragdb > backup.sql

# Backup uploads and ChromaDB
tar -czf data_backup.tar.gz data/
```

### Restoring Data

```bash
# Restore PostgreSQL
docker-compose exec -T postgres psql -U raguser ragdb < backup.sql

# Restore uploads and ChromaDB
tar -xzf data_backup.tar.gz
```

## Performance Optimization

### For Large Document Collections

1. **Increase Batch Size** (if you have RAM):
   ```bash
   BATCH_SIZE=64
   ```

2. **Use Better Hardware**:
   - More CPU cores
   - More RAM
   - SSD storage

3. **Optimize Database**:
   - Regular VACUUM in PostgreSQL
   - Index optimization

### For Faster Searches

1. **Limit Result Count**: Request fewer results (Top 3 vs Top 10)
2. **Filter by Document**: Search within specific documents
3. **Use ChromaDB Indexes**: Already optimized by default

## Monitoring

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Check System Stats

```bash
# Container resource usage
docker stats

# Service health
docker-compose ps
```

### API Metrics

Visit: http://localhost:8000/docs

All endpoints include timing information in responses.

---

## Need More Help?

- **API Documentation**: http://localhost:8000/docs
- **Check Logs**: `docker-compose logs`
- **Restart Services**: `docker-compose restart`
- **Full Reset**: `docker-compose down -v && docker-compose up`

Happy searching! 🚀
