"""
Embedding generation service
Adapted from embedding_generator.py
"""
import logging
from typing import List, Iterator, Tuple, Dict, Any, Generator
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings for text using sentence-transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", batch_size: int = 32):
        """
        Initialize embedding service

        Args:
            model_name: Name of the sentence-transformers model
            batch_size: Batch size for processing
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the embedding model"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text string

        Returns:
            Embedding vector
        """
        return self.generate_embeddings([text])[0]

    def generate_embeddings_streaming(
        self,
        chunks_iterator: Iterator[Dict[str, Any]]
    ) -> Generator[Tuple[List[Dict[str, Any]], List[List[float]]], None, None]:
        """
        Generate embeddings for chunks as they arrive from a streaming source.

        Collects chunks into batches and yields (chunks, embeddings) pairs.
        This allows embeddings to be generated progressively without waiting
        for all chunks to be created first.

        Args:
            chunks_iterator: Iterator yielding chunk dictionaries with 'content' key

        Yields:
            Tuple of (list of chunk dicts, list of embedding vectors) for each batch
        """
        batch_chunks = []
        batch_texts = []

        try:
            for chunk in chunks_iterator:
                batch_chunks.append(chunk)
                batch_texts.append(chunk["content"])

                # When batch is full, generate embeddings and yield
                if len(batch_chunks) >= self.batch_size:
                    logger.info(f"Generating embeddings for batch of {len(batch_texts)} chunks")
                    embeddings = self.model.encode(
                        batch_texts,
                        batch_size=self.batch_size,
                        normalize_embeddings=True,
                        show_progress_bar=False
                    )
                    yield batch_chunks, embeddings.tolist()

                    # Reset batch
                    batch_chunks = []
                    batch_texts = []

            # Process any remaining chunks in the final partial batch
            if batch_chunks:
                logger.info(f"Generating embeddings for final batch of {len(batch_texts)} chunks")
                embeddings = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    show_progress_bar=False
                )
                yield batch_chunks, embeddings.tolist()

        except Exception as e:
            logger.error(f"Error in streaming embeddings generation: {e}")
            raise

    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        return self.model.get_sentence_embedding_dimension()
