"""
Vector store service using Vertex AI Vector Search
"""
import logging
import json
from typing import List, Dict, Any, Optional
from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import MatchNeighbor

logger = logging.getLogger(__name__)


class VectorStore:
    """Vertex AI Vector Search store for managing embeddings"""

    def __init__(
        self,
        project_id: str,
        region: str,
        index_endpoint_id: str,
        deployed_index_id: str,
        index_id: str = None
    ):
        """
        Initialize Vertex AI Vector Store

        Args:
            project_id: GCP project ID
            region: GCP region
            index_endpoint_id: Resource ID of the index endpoint
            deployed_index_id: ID of the deployed index
            index_id: Resource ID of the index (for updates)
        """
        self.project_id = project_id
        self.region = region
        self.index_endpoint_id = index_endpoint_id
        self.deployed_index_id = deployed_index_id
        self.index_id = index_id
        self.endpoint = None
        self.index = None
        self._initialize()

    def _initialize(self):
        """Initialize connection to Vertex AI"""
        try:
            logger.info(f"Connecting to Vertex AI in {self.region}")

            # Initialize AI Platform
            aiplatform.init(project=self.project_id, location=self.region)

            # Get the index endpoint
            self.endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=self.index_endpoint_id
            )
            logger.info(f"Connected to Index Endpoint: {self.endpoint.resource_name}")

            # Get the index for updates
            if self.index_id:
                self.index = aiplatform.MatchingEngineIndex(
                    index_name=self.index_id
                )
                logger.info(f"Connected to Index: {self.index.resource_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI Vector Store: {e}")
            raise

    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add documents to Vertex AI Vector Search via streaming update

        Args:
            ids: List of unique document IDs
            documents: List of document texts (stored in database)
            embeddings: List of embedding vectors
            metadatas: Optional metadata dictionaries

        Returns:
            True if successful
        """
        try:
            logger.info(f"Adding {len(ids)} embeddings to Vertex AI")

            if not self.index:
                logger.error("Index not configured for updates")
                return False

            # Prepare datapoints for upsert
            datapoints = []
            for i, (doc_id, embedding) in enumerate(zip(ids, embeddings)):
                # Build restricts from metadata for filtering
                restricts = []
                if metadatas and i < len(metadatas):
                    metadata = metadatas[i]
                    if "document_id" in metadata:
                        restricts.append({
                            "namespace": "document_id",
                            "allow_list": [str(metadata["document_id"])]
                        })

                datapoint = {
                    "datapoint_id": doc_id,
                    "feature_vector": embedding,
                }
                if restricts:
                    datapoint["restricts"] = restricts

                datapoints.append(datapoint)

            # Upsert datapoints using streaming update
            self.index.upsert_datapoints(datapoints=datapoints)

            logger.info(f"Successfully upserted {len(ids)} embeddings to Vertex AI")
            return True

        except Exception as e:
            logger.error(f"Error adding documents to Vertex AI: {e}")
            raise

    def add_documents_batch(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        document_id: Optional[int] = None
    ) -> int:
        """
        Add a batch of chunks to Vertex AI

        Args:
            chunks: List of chunk dictionaries with 'id', 'content', and 'metadata'
            embeddings: List of embedding vectors
            document_id: Optional document ID

        Returns:
            Number of chunks added
        """
        if not chunks or not embeddings:
            return 0

        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings")

        try:
            ids = [chunk["id"] for chunk in chunks]
            documents = [chunk["content"] for chunk in chunks]
            metadatas = []

            for chunk in chunks:
                metadata = chunk["metadata"].copy()
                if document_id is not None:
                    metadata["document_id"] = str(document_id)
                metadatas.append(metadata)

            self.add_documents(ids, documents, embeddings, metadatas)
            return len(chunks)

        except Exception as e:
            logger.error(f"Error adding batch: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar vectors in Vertex AI

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results
            where: Optional metadata filter

        Returns:
            Search results with ids and distances
        """
        try:
            logger.info(f"Searching Vertex AI for top {n_results} results")

            # Build numeric filters from where clause
            numeric_filter = None
            if where and "document_id" in where:
                # Vertex AI filter format
                numeric_filter = [
                    {
                        "namespace": "document_id",
                        "allow_list": [str(where["document_id"])]
                    }
                ]

            # Query the index endpoint
            response = self.endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[query_embedding],
                num_neighbors=n_results,
            )

            # Parse response
            ids = []
            distances = []

            if response and len(response) > 0:
                matches = response[0]  # First query results
                for match in matches:
                    ids.append(match.id)
                    # Vertex AI returns distance (lower = more similar for cosine)
                    distances.append(match.distance)

            logger.info(f"Found {len(ids)} results")

            # Note: documents and metadatas must be retrieved from database using IDs
            return {
                "ids": ids,
                "documents": [],  # Retrieve from database
                "metadatas": [],  # Retrieve from database
                "distances": distances
            }

        except Exception as e:
            logger.error(f"Error searching Vertex AI: {e}")
            raise

    def delete_by_ids(self, ids: List[str]) -> bool:
        """
        Delete vectors by IDs from Vertex AI

        Args:
            ids: List of IDs to delete

        Returns:
            True if successful
        """
        try:
            if not self.index:
                logger.error("Index not configured for updates")
                return False

            logger.info(f"Deleting {len(ids)} datapoints from Vertex AI")
            self.index.remove_datapoints(datapoint_ids=ids)
            logger.info(f"Successfully deleted {len(ids)} datapoints")
            return True

        except Exception as e:
            logger.error(f"Error deleting from Vertex AI: {e}")
            raise

    def delete_by_source(self, source: str) -> int:
        """
        Delete by source - requires fetching IDs from database first

        Args:
            source: Source identifier

        Returns:
            Number deleted (must be tracked externally)
        """
        logger.warning(f"delete_by_source not directly supported - use delete_by_ids with IDs from database")
        return 0

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get index statistics

        Returns:
            Dictionary with stats
        """
        try:
            return {
                "name": f"vertex-ai-{self.deployed_index_id}",
                "count": "track_in_database",  # Vertex AI doesn't expose count easily
                "endpoint": self.index_endpoint_id,
                "deployed_index": self.deployed_index_id
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "name": "vertex-ai",
                "count": 0
            }
