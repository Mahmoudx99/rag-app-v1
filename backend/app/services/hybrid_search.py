"""
Hybrid search service combining semantic and keyword (BM25) search
"""
import logging
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
import re

logger = logging.getLogger(__name__)


class HybridSearchService:
    """
    Combines semantic search (vector similarity) with keyword search (BM25)
    using Reciprocal Rank Fusion (RRF) for score combination.
    """

    def __init__(self, vector_store, embedding_service):
        """
        Initialize hybrid search service.

        Args:
            vector_store: VectorStore instance for semantic search
            embedding_service: EmbeddingService for generating query embeddings
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.bm25_index = None
        self.corpus_ids = []
        self.corpus_documents = []
        self.corpus_metadatas = []
        self._tokenized_corpus = []

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens (lowercase words)
        """
        # Simple tokenization: lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def build_bm25_index(self, where: Optional[Dict[str, Any]] = None) -> int:
        """
        Build BM25 index from documents in the vector store.

        Args:
            where: Optional metadata filter (e.g., {"document_id": 1})

        Returns:
            Number of documents indexed
        """
        try:
            logger.info("Building BM25 index from vector store")

            # Get all documents from ChromaDB
            if where:
                results = self.vector_store.collection.get(
                    where=where,
                    include=["documents", "metadatas"]
                )
            else:
                results = self.vector_store.collection.get(
                    include=["documents", "metadatas"]
                )

            if not results["ids"]:
                logger.warning("No documents found for BM25 indexing")
                self.bm25_index = None
                self.corpus_ids = []
                self.corpus_documents = []
                self.corpus_metadatas = []
                self._tokenized_corpus = []
                return 0

            self.corpus_ids = results["ids"]
            self.corpus_documents = results["documents"]
            self.corpus_metadatas = results["metadatas"]

            # Tokenize all documents
            self._tokenized_corpus = [
                self._tokenize(doc) for doc in self.corpus_documents
            ]

            # Build BM25 index
            self.bm25_index = BM25Okapi(self._tokenized_corpus)

            logger.info(f"BM25 index built with {len(self.corpus_ids)} documents")
            return len(self.corpus_ids)

        except Exception as e:
            logger.error(f"Error building BM25 index: {e}")
            raise

    def keyword_search(
        self,
        query: str,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """
        Perform keyword search using BM25.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            Dictionary with ids, documents, metadatas, and scores
        """
        if self.bm25_index is None or len(self.corpus_ids) == 0:
            logger.warning("BM25 index not built or empty")
            return {
                "ids": [],
                "documents": [],
                "metadatas": [],
                "scores": []
            }

        try:
            # Tokenize query
            query_tokens = self._tokenize(query)

            if not query_tokens:
                logger.warning("Query has no valid tokens for keyword search")
                return {
                    "ids": [],
                    "documents": [],
                    "metadatas": [],
                    "scores": []
                }

            # Get BM25 scores for all documents
            scores = self.bm25_index.get_scores(query_tokens)

            # Get top N results
            top_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:n_results]

            # Filter out zero scores
            top_indices = [i for i in top_indices if scores[i] > 0]

            return {
                "ids": [self.corpus_ids[i] for i in top_indices],
                "documents": [self.corpus_documents[i] for i in top_indices],
                "metadatas": [self.corpus_metadatas[i] for i in top_indices],
                "scores": [float(scores[i]) for i in top_indices]
            }

        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            raise

    def semantic_search(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Search query
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Dictionary with ids, documents, metadatas, and scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)

            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                n_results=n_results,
                where=where
            )

            # Convert distances to similarity scores (1 - distance for cosine)
            scores = [1 - d for d in results["distances"]]

            return {
                "ids": results["ids"],
                "documents": results["documents"],
                "metadatas": results["metadatas"],
                "scores": scores
            }

        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            raise

    def _reciprocal_rank_fusion(
        self,
        semantic_results: Dict[str, Any],
        keyword_results: Dict[str, Any],
        semantic_weight: float = 0.5,
        k: int = 60
    ) -> Dict[str, Any]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).

        RRF Score = sum(weight / (k + rank))

        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            semantic_weight: Weight for semantic search (0-1), keyword weight = 1 - semantic_weight
            k: RRF parameter (default 60, commonly used value)

        Returns:
            Combined and re-ranked results
        """
        keyword_weight = 1 - semantic_weight

        # Create a map of chunk_id -> {document, metadata, rrf_score}
        combined_scores = {}

        # Process semantic search results
        for rank, chunk_id in enumerate(semantic_results["ids"]):
            if chunk_id not in combined_scores:
                idx = semantic_results["ids"].index(chunk_id)
                combined_scores[chunk_id] = {
                    "document": semantic_results["documents"][idx],
                    "metadata": semantic_results["metadatas"][idx],
                    "rrf_score": 0,
                    "semantic_score": semantic_results["scores"][idx],
                    "keyword_score": 0
                }
            # RRF contribution from semantic search
            combined_scores[chunk_id]["rrf_score"] += semantic_weight / (k + rank + 1)

        # Process keyword search results
        for rank, chunk_id in enumerate(keyword_results["ids"]):
            if chunk_id not in combined_scores:
                idx = keyword_results["ids"].index(chunk_id)
                combined_scores[chunk_id] = {
                    "document": keyword_results["documents"][idx],
                    "metadata": keyword_results["metadatas"][idx],
                    "rrf_score": 0,
                    "semantic_score": 0,
                    "keyword_score": keyword_results["scores"][idx]
                }
            else:
                # Update keyword score if exists
                idx = keyword_results["ids"].index(chunk_id)
                combined_scores[chunk_id]["keyword_score"] = keyword_results["scores"][idx]

            # RRF contribution from keyword search
            combined_scores[chunk_id]["rrf_score"] += keyword_weight / (k + rank + 1)

        # Sort by RRF score
        sorted_results = sorted(
            combined_scores.items(),
            key=lambda x: x[1]["rrf_score"],
            reverse=True
        )

        # Normalize RRF scores to 0-1 range for better interpretability
        if sorted_results:
            max_rrf = sorted_results[0][1]["rrf_score"]
            min_rrf = sorted_results[-1][1]["rrf_score"] if len(sorted_results) > 1 else 0
            rrf_range = max_rrf - min_rrf if max_rrf != min_rrf else 1

            normalized_scores = []
            for item in sorted_results:
                # Normalize to 0-1, then scale based on semantic score for meaningful display
                normalized_rrf = (item[1]["rrf_score"] - min_rrf) / rrf_range if rrf_range > 0 else 1
                # Combine with semantic score to provide a more intuitive score
                # Use weighted average: 70% based on actual semantic similarity, 30% based on rank
                combined_display_score = (
                    item[1]["semantic_score"] * 0.7 + normalized_rrf * 0.3
                )
                normalized_scores.append(combined_display_score)
        else:
            normalized_scores = []

        # Format results
        return {
            "ids": [item[0] for item in sorted_results],
            "documents": [item[1]["document"] for item in sorted_results],
            "metadatas": [item[1]["metadata"] for item in sorted_results],
            "scores": normalized_scores,
            "semantic_scores": [item[1]["semantic_score"] for item in sorted_results],
            "keyword_scores": [item[1]["keyword_score"] for item in sorted_results]
        }

    def hybrid_search(
        self,
        query: str,
        n_results: int = 5,
        document_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None,
        semantic_weight: float = 0.5,
        search_mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Search query
            n_results: Number of final results to return
            document_id: Optional single document ID to filter results
            document_ids: Optional list of document IDs to filter results
            semantic_weight: Weight for semantic search (0-1)
                - 1.0 = pure semantic search
                - 0.0 = pure keyword search
                - 0.5 = balanced hybrid (default)
            search_mode: Search mode - "hybrid", "semantic", or "keyword"

        Returns:
            Dictionary with combined search results
        """
        try:
            logger.info(f"Performing {search_mode} search for: {query[:50]}...")

            # Build metadata filter
            where_filter = None
            if document_ids and len(document_ids) > 0:
                # Filter by multiple document IDs using $in operator
                where_filter = {"document_id": {"$in": document_ids}}
            elif document_id:
                where_filter = {"document_id": document_id}

            # Handle different search modes
            if search_mode == "semantic":
                semantic_results = self.semantic_search(
                    query=query,
                    n_results=n_results,
                    where=where_filter
                )
                return {
                    "ids": semantic_results["ids"],
                    "documents": semantic_results["documents"],
                    "metadatas": semantic_results["metadatas"],
                    "scores": semantic_results["scores"],
                    "semantic_scores": semantic_results["scores"],
                    "keyword_scores": [0.0] * len(semantic_results["ids"]),
                    "search_mode": "semantic"
                }

            elif search_mode == "keyword":
                # Build BM25 index for the filtered corpus
                self.build_bm25_index(where=where_filter)
                keyword_results = self.keyword_search(
                    query=query,
                    n_results=n_results
                )
                return {
                    "ids": keyword_results["ids"],
                    "documents": keyword_results["documents"],
                    "metadatas": keyword_results["metadatas"],
                    "scores": keyword_results["scores"],
                    "semantic_scores": [0.0] * len(keyword_results["ids"]),
                    "keyword_scores": keyword_results["scores"],
                    "search_mode": "keyword"
                }

            else:  # hybrid mode
                # Build BM25 index for the filtered corpus
                self.build_bm25_index(where=where_filter)

                # Fetch more results from each search for better fusion
                fetch_multiplier = 3
                fetch_n = min(n_results * fetch_multiplier, 50)

                # Perform both searches
                semantic_results = self.semantic_search(
                    query=query,
                    n_results=fetch_n,
                    where=where_filter
                )

                keyword_results = self.keyword_search(
                    query=query,
                    n_results=fetch_n
                )

                # Combine using RRF
                combined_results = self._reciprocal_rank_fusion(
                    semantic_results=semantic_results,
                    keyword_results=keyword_results,
                    semantic_weight=semantic_weight
                )

                # Return top N results
                return {
                    "ids": combined_results["ids"][:n_results],
                    "documents": combined_results["documents"][:n_results],
                    "metadatas": combined_results["metadatas"][:n_results],
                    "scores": combined_results["scores"][:n_results],
                    "semantic_scores": combined_results["semantic_scores"][:n_results],
                    "keyword_scores": combined_results["keyword_scores"][:n_results],
                    "search_mode": "hybrid"
                }

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            raise
