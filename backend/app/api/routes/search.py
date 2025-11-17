"""
Search API routes - Semantic search across documents
"""
from typing import List, Optional, Literal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...services.embedding_service import EmbeddingService
from ...services.vector_store import VectorStore
from ...services.hybrid_search import HybridSearchService
from ...core.config import get_settings

router = APIRouter()
settings = get_settings()

# Services will be initialized on first use
embedding_service = None
vector_store = None
hybrid_search_service = None


def get_services():
    """Get service instances"""
    global embedding_service, vector_store, hybrid_search_service

    if embedding_service is None:
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            batch_size=settings.BATCH_SIZE
        )

    if vector_store is None:
        vector_store = VectorStore(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            collection_name=settings.CHROMA_COLLECTION
        )

    if hybrid_search_service is None:
        hybrid_search_service = HybridSearchService(
            vector_store=vector_store,
            embedding_service=embedding_service
        )

    return embedding_service, vector_store, hybrid_search_service


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    document_id: Optional[int] = None
    document_ids: Optional[List[int]] = None  # Multiple document filtering
    search_mode: Literal["hybrid", "semantic", "keyword"] = "hybrid"
    semantic_weight: float = Field(default=0.7, ge=0.0, le=1.0)
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
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_mode: str = "hybrid"
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
    Perform advanced hybrid search across all documents

    - Supports three modes: hybrid (default), semantic, or keyword
    - Hybrid mode combines semantic (vector) and keyword (BM25) search using RRF
    - semantic_weight controls the balance (0.5 = balanced, 1.0 = pure semantic, 0.0 = pure keyword)
    - Filter by document IDs, date range, and boolean operators
    - Returns top K most relevant chunks with both semantic and keyword scores
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
        embed_svc, vec_store, hybrid_svc = get_services()

        # Determine document filter
        doc_filter = None
        if request.document_ids and len(request.document_ids) > 0:
            doc_filter = request.document_ids
        elif request.document_id:
            doc_filter = request.document_id

        # Fetch more results to account for filtering
        fetch_multiplier = 3 if (request.must_include or request.must_exclude or request.any_of) else 1
        fetch_k = min(request.top_k * fetch_multiplier, 50)

        # Perform hybrid search
        search_results = hybrid_svc.hybrid_search(
            query=request.query,
            n_results=fetch_k,
            document_id=doc_filter if isinstance(doc_filter, int) else None,
            document_ids=doc_filter if isinstance(doc_filter, list) else None,
            semantic_weight=request.semantic_weight,
            search_mode=request.search_mode
        )

        # Format results
        results = []
        for i in range(len(search_results["ids"])):
            results.append(SearchResult(
                chunk_id=search_results["ids"][i],
                content=search_results["documents"][i],
                score=search_results["scores"][i],
                semantic_score=search_results["semantic_scores"][i],
                keyword_score=search_results["keyword_scores"][i],
                metadata=search_results["metadatas"][i]
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
            search_mode=search_results.get("search_mode", request.search_mode),
            filters_applied=filters_applied
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
