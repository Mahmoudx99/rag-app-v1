"""
Search API routes - Semantic search across documents
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...services.embedding_service import EmbeddingService
from ...services.vector_store import VectorStore
from ...core.config import get_settings
from ...core.database import SessionLocal
from ...models.document import Chunk

router = APIRouter()
settings = get_settings()

# Services will be initialized on first use
embedding_service = None
vector_store = None


def get_services():
    """Get service instances"""
    global embedding_service, vector_store

    if embedding_service is None:
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            batch_size=settings.BATCH_SIZE
        )

    if vector_store is None:
        vector_store = VectorStore(
            project_id=settings.GCP_PROJECT_ID,
            region=settings.GCP_REGION,
            index_endpoint_id=settings.VERTEX_AI_INDEX_ENDPOINT_ID,
            deployed_index_id=settings.VERTEX_AI_DEPLOYED_INDEX_ID,
            index_id=settings.VERTEX_AI_INDEX_ID
        )

    return embedding_service, vector_store


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: Optional[int] = None
    document_ids: Optional[List[int]] = None  # Multiple document filtering
    # Date filters
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    # Boolean operators
    must_include: Optional[List[str]] = None  # AND - all these terms must be present
    must_exclude: Optional[List[str]] = None  # NOT - exclude results with these terms
    any_of: Optional[List[str]] = None  # OR - at least one of these terms


class SearchResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    filters_applied: dict = {}


def apply_boolean_filters(results: List[SearchResult], request: SearchRequest) -> List[SearchResult]:
    """Apply boolean operators to filter results"""
    filtered_results = results

    # AND - must include all terms
    if request.must_include:
        filtered_results = [
            r for r in filtered_results
            if all(term.lower() in r.content.lower() for term in request.must_include)
        ]

    # NOT - must exclude these terms
    if request.must_exclude:
        filtered_results = [
            r for r in filtered_results
            if not any(term.lower() in r.content.lower() for term in request.must_exclude)
        ]

    # OR - must contain at least one of these terms
    if request.any_of:
        filtered_results = [
            r for r in filtered_results
            if any(term.lower() in r.content.lower() for term in request.any_of)
        ]

    return filtered_results


@router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Perform semantic (vector) search across all documents

    - Uses vector similarity search for semantic understanding
    - Filter by document IDs, date range, and boolean operators
    - Returns top K most relevant chunks with similarity scores
    """
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )

    if request.top_k < 1 or request.top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 50"
        )

    try:
        # Get services
        embed_svc, vec_store = get_services()

        # Determine document filter
        where_filter = None
        if request.document_ids and len(request.document_ids) > 0:
            where_filter = {"document_id": {"$in": request.document_ids}}
        elif request.document_id:
            where_filter = {"document_id": request.document_id}

        # Fetch more results to account for filtering
        fetch_multiplier = 3 if (request.must_include or request.must_exclude or request.any_of) else 1
        fetch_k = min(request.top_k * fetch_multiplier, 50)

        # Generate query embedding
        query_embedding = embed_svc.generate_embedding(request.query)

        # Perform vector search
        search_results = vec_store.search(
            query_embedding=query_embedding,
            n_results=fetch_k,
            where=where_filter
        )

        # Convert distances to similarity scores (1 - distance for cosine)
        scores = [1 - d for d in search_results["distances"]]

        # Retrieve chunk content from database
        chunk_ids = search_results["ids"]
        documents = []
        metadatas = []

        if chunk_ids:
            db = SessionLocal()
            try:
                # Get chunks from database by their IDs
                db_chunks = db.query(Chunk).filter(Chunk.chunk_id.in_(chunk_ids)).all()

                # Create a map for quick lookup
                chunk_map = {c.chunk_id: c for c in db_chunks}

                # Maintain order from search results
                for chunk_id in chunk_ids:
                    if chunk_id in chunk_map:
                        chunk = chunk_map[chunk_id]
                        documents.append(chunk.content)
                        metadatas.append(chunk.chunk_metadata or {})
                    else:
                        # Chunk not found in DB - use placeholder
                        documents.append("")
                        metadatas.append({})
            finally:
                db.close()

        # Format results
        results = []
        for i in range(len(chunk_ids)):
            results.append(SearchResult(
                chunk_id=chunk_ids[i],
                content=documents[i],
                score=scores[i],
                metadata=metadatas[i]
            ))

        # Apply boolean filters
        results = apply_boolean_filters(results, request)

        # Trim to requested top_k
        results = results[:request.top_k]

        # Track filters applied
        filters_applied = {}
        if request.document_id or request.document_ids:
            filters_applied["documents"] = request.document_ids or [request.document_id]
        if request.date_from:
            filters_applied["date_from"] = request.date_from.isoformat()
        if request.date_to:
            filters_applied["date_to"] = request.date_to.isoformat()
        if request.must_include:
            filters_applied["must_include"] = request.must_include
        if request.must_exclude:
            filters_applied["must_exclude"] = request.must_exclude
        if request.any_of:
            filters_applied["any_of"] = request.any_of

        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            filters_applied=filters_applied
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
