"""
Vector store service using ChromaDB
"""
import logging
from typing import List, Dict, Any, Optional
import chromadb

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB vector store for managing embeddings"""

    def __init__(self, host: str, port: int, collection_name: str = "documents"):
        """
        Initialize vector store

        Args:
            host: ChromaDB host
            port: ChromaDB port
            collection_name: Name of the collection
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize()

    def _initialize(self):
        try:
            logger.info(f"Connecting to ChromaDB at: {self.host}:{self.port}")
            self.client = chromadb.HttpClient(host=self.host, port=self.port)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Collection '{self.collection_name}' ready")

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def add_documents(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add documents to the vector store

        Args:
            ids: List of unique document IDs
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dictionaries

        Returns:
            True if successful
        """
        try:
            logger.info(f"Adding {len(ids)} documents to vector store")

            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas if metadatas else None
            )

            logger.info(f"Successfully added {len(ids)} documents")
            return True

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search for similar documents

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return
            where: Optional metadata filter

        Returns:
            Search results
        """
        try:
            logger.info(f"Searching for top {n_results} results")

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )

            return {
                "ids": results["ids"][0] if results["ids"] else [],
                "documents": results["documents"][0] if results["documents"] else [],
                "metadatas": results["metadatas"][0] if results["metadatas"] else [],
                "distances": results["distances"][0] if results["distances"] else []
            }

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise

    def delete_by_ids(self, ids: List[str]) -> bool:
        """
        Delete documents by IDs

        Args:
            ids: List of document IDs to delete

        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting {len(ids)} documents")
            self.collection.delete(ids=ids)
            logger.info(f"Successfully deleted {len(ids)} documents")
            return True

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            raise

    def delete_by_source(self, source: str) -> int:
        """
        Delete all documents from a specific source

        Args:
            source: Source filename

        Returns:
            Number of documents deleted
        """
        try:
            logger.info(f"Deleting documents from source: {source}")

            # Get all IDs with this source
            results = self.collection.get(
                where={"source": source}
            )

            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                count = len(results["ids"])
                logger.info(f"Deleted {count} documents from {source}")
                return count
            else:
                logger.info(f"No documents found for source: {source}")
                return 0

        except Exception as e:
            logger.error(f"Error deleting by source: {e}")
            raise

    def add_documents_batch(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]],
        document_id: Optional[int] = None
    ) -> int:
        """
        Add a batch of chunks to the vector store (used for streaming/incremental inserts).

        This method is designed for progressive insertion during streaming processing,
        allowing chunks to be stored as they are embedded rather than waiting for
        all chunks to be ready.

        Args:
            chunks: List of chunk dictionaries with 'id', 'content', and 'metadata'
            embeddings: List of embedding vectors corresponding to chunks
            document_id: Optional document ID to add to metadata

        Returns:
            Number of chunks successfully added
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
                    metadata["document_id"] = document_id
                metadatas.append(metadata)

            logger.info(f"Adding batch of {len(chunks)} chunks to vector store")

            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(f"Successfully added batch of {len(chunks)} chunks")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error adding batch of chunks: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Dictionary with collection stats
        """
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "count": count
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"name": self.collection_name, "count": 0}
