"""
Local Embedding Module for CV Governance Agent

Implements local embedding generation using sentence-transformers
to ensure GDPR compliance (no CV data sent to external APIs).

Architecture Decision A4: Local Model (all-MiniLM-L6-v2) instead of OpenAI API
Pattern 4.3.2: Context-Prefix for better retrieval quality
"""

import numpy as np
from typing import List, Optional, Union
from sentence_transformers import SentenceTransformer
import logging

from .models import Chunk

logger = logging.getLogger(__name__)


class LocalEmbedder:
    """
    Local embedding generator using sentence-transformers.
    
    Features:
    - Fully local execution (GDPR-compliant)
    - Context-aware prefixing for better retrieval
    - Batch processing support
    - Caching for performance
    
    Model: all-MiniLM-L6-v2
    - Dimensions: 384
    - Speed: ~50ms per embedding
    - Multilingual support (German + English)
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        cache_folder: Optional[str] = None
    ):
        """
        Initialize the local embedder.
        
        Args:
            model_name: HuggingFace model identifier
            device: Device to use ('cpu', 'cuda', or None for auto-detect)
            cache_folder: Custom cache folder for model downloads
        """
        logger.info(f"Initializing LocalEmbedder with model: {model_name}")
        
        try:
            self.model = SentenceTransformer(
                model_name,
                device=device,
                cache_folder=cache_folder
            )
            self.model_name = model_name
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            
            logger.info(
                f"Model loaded successfully. "
                f"Embedding dimension: {self.embedding_dim}, "
                f"Device: {self.model.device}"
            )
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def embed_chunk(self, chunk: Chunk) -> np.ndarray:
        """
        Embed a single CV chunk with context prefix.
        
        Args:
            chunk: Chunk object to embed
            
        Returns:
            Embedding vector (numpy array of shape [384])
            
        Example:
            >>> embedder = LocalEmbedder()
            >>> chunk = Chunk(id="cv_exp_001", text="Python developer...", section_type="experience")
            >>> embedding = embedder.embed_chunk(chunk)
            >>> embedding.shape
            (384,)
        """
        # Context-aware prefix (Pattern 4.3.2)
        prefixed_text = self._add_chunk_prefix(chunk)
        
        try:
            embedding = self.model.encode(
                prefixed_text,
                convert_to_numpy=True,
                normalize_embeddings=True  # For cosine similarity
            )
            
            logger.debug(
                f"Embedded chunk {chunk.chunk_id} "
                f"(section: {chunk.section_type}, {len(chunk.text)} chars)"
            )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed chunk {chunk.chunk_id}: {e}")
            raise
    
    def embed_query(self, query: str, query_type: str = "job_requirement") -> np.ndarray:
        """
        Embed a query (e.g., job requirement) with context prefix.
        
        Args:
            query: Query text to embed
            query_type: Type of query for context prefix
            
        Returns:
            Embedding vector (numpy array of shape [384])
            
        Example:
            >>> embedder = LocalEmbedder()
            >>> query = "Python development experience"
            >>> embedding = embedder.embed_query(query)
            >>> embedding.shape
            (384,)
        """
        # Context-aware prefix for queries
        prefixed_query = f"{query_type.replace('_', ' ').title()}: {query}"
        
        try:
            embedding = self.model.encode(
                prefixed_query,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            
            logger.debug(f"Embedded query: '{query[:50]}...' (type: {query_type})")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise
    
    def batch_embed_chunks(self, chunks: List[Chunk]) -> List[np.ndarray]:
        """
        Embed multiple chunks in batch for better performance.
        
        Args:
            chunks: List of chunks to embed
            
        Returns:
            List of embedding vectors
            
        Example:
            >>> embedder = LocalEmbedder()
            >>> chunks = [chunk1, chunk2, chunk3]
            >>> embeddings = embedder.batch_embed_chunks(chunks)
            >>> len(embeddings)
            3
        """
        if not chunks:
            return []
        
        logger.info(f"Batch embedding {len(chunks)} chunks")
        
        # Prepare prefixed texts
        prefixed_texts = [self._add_chunk_prefix(chunk) for chunk in chunks]
        
        try:
            embeddings = self.model.encode(
                prefixed_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,  # Configurable batch size
                show_progress_bar=len(chunks) > 10  # Show progress for large batches
            )
            
            logger.info(f"Successfully embedded {len(chunks)} chunks")
            
            return list(embeddings)
            
        except Exception as e:
            logger.error(f"Failed to batch embed chunks: {e}")
            raise
    
    def batch_embed_queries(self, queries: List[str], query_type: str = "job_requirement") -> List[np.ndarray]:
        """
        Embed multiple queries in batch.
        
        Args:
            queries: List of query texts
            query_type: Type of queries for context prefix
            
        Returns:
            List of embedding vectors
        """
        if not queries:
            return []
        
        logger.info(f"Batch embedding {len(queries)} queries")
        
        # Add context prefix
        prefixed_queries = [
            f"{query_type.replace('_', ' ').title()}: {query}"
            for query in queries
        ]
        
        try:
            embeddings = self.model.encode(
                prefixed_queries,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32
            )
            
            logger.info(f"Successfully embedded {len(queries)} queries")
            
            return list(embeddings)
            
        except Exception as e:
            logger.error(f"Failed to batch embed queries: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension of the model."""
        return self.embedding_dim
    
    def _add_chunk_prefix(self, chunk: Chunk) -> str:
        """
        Add context-aware prefix to chunk text for better retrieval.
        
        Pattern 4.3.2: Prefix improves retrieval quality by task contextualization.
        
        Args:
            chunk: Chunk object
            
        Returns:
            Prefixed text
        """
        section_type = chunk.section_type or "general"
        return f"CV Section ({section_type}): {chunk.text}"
    
    def __repr__(self) -> str:
        return (
            f"LocalEmbedder(model='{self.model_name}', "
            f"dim={self.embedding_dim}, "
            f"device={self.model.device})"
        )
