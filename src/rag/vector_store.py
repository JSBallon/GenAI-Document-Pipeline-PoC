"""
In-Memory Vector Store for CV Governance Agent

Implements a simple in-memory vector store for the PoC phase.
Uses NumPy arrays and cosine similarity for retrieval.

Architecture Decision A3: In-Memory Store instead of Qdrant for PoC simplicity
Pattern 4.3.3: Top-K Retrieval with Relevance Threshold
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

from .models import Chunk

logger = logging.getLogger(__name__)


@dataclass
class StoredEmbedding:
    """Container for stored embedding with metadata."""
    chunk_id: str
    embedding: np.ndarray
    chunk: Chunk
    

class InMemoryVectorStore:
    """
    Simple in-memory vector store for CV chunks.
    
    Features:
    - Fast in-memory storage (no disk I/O)
    - Cosine similarity search
    - Top-K retrieval with threshold filtering
    - CRUD operations
    
    Limitations (by design for PoC):
    - No persistence (session-based)
    - No scalability (single CV per session)
    - No concurrent access handling
    
    For production: Migrate to Qdrant or similar vector DB.
    """
    
    def __init__(self, embedding_dim: int = 384):
        """
        Initialize the vector store.
        
        Args:
            embedding_dim: Expected embedding dimension (default: 384 for all-MiniLM-L6-v2)
        """
        self.embedding_dim = embedding_dim
        self.embeddings: Dict[str, StoredEmbedding] = {}
        
        logger.info(f"Initialized InMemoryVectorStore (dim={embedding_dim})")
    
    def add_embedding(
        self, 
        chunk_id: str, 
        embedding: np.ndarray, 
        chunk: Chunk
    ) -> None:
        """
        Add a single embedding to the store.
        
        Args:
            chunk_id: Unique identifier for the chunk
            embedding: Embedding vector
            chunk: Original chunk object
            
        Raises:
            ValueError: If embedding dimension doesn't match
        """
        # Validate embedding dimension
        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch. "
                f"Expected {self.embedding_dim}, got {embedding.shape[0]}"
            )
        
        # Ensure embedding is normalized for cosine similarity
        normalized_embedding = self._normalize(embedding)
        
        # Store
        self.embeddings[chunk_id] = StoredEmbedding(
            chunk_id=chunk_id,
            embedding=normalized_embedding,
            chunk=chunk
        )
        
        logger.debug(f"Added embedding for chunk {chunk_id}")
    
    def add_embeddings(
        self,
        chunk_ids: List[str],
        embeddings: List[np.ndarray],
        chunks: List[Chunk]
    ) -> None:
        """
        Add multiple embeddings in batch.
        
        Args:
            chunk_ids: List of chunk identifiers
            embeddings: List of embedding vectors
            chunks: List of chunk objects
            
        Raises:
            ValueError: If list lengths don't match or dimensions are wrong
        """
        if not (len(chunk_ids) == len(embeddings) == len(chunks)):
            raise ValueError(
                f"List length mismatch: "
                f"ids={len(chunk_ids)}, embeddings={len(embeddings)}, chunks={len(chunks)}"
            )
        
        logger.info(f"Adding {len(chunk_ids)} embeddings to store")
        
        for chunk_id, embedding, chunk in zip(chunk_ids, embeddings, chunks):
            self.add_embedding(chunk_id, embedding, chunk)
        
        logger.info(f"Successfully added {len(chunk_ids)} embeddings")
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for similar chunks using cosine similarity.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return (default: 5)
            threshold: Minimum similarity score (default: 0.3)
            
        Returns:
            List of (Chunk, score) tuples, sorted by score (descending)
            
        Example:
            >>> store = InMemoryVectorStore()
            >>> # ... add embeddings ...
            >>> results = store.search(query_embedding, top_k=5, threshold=0.3)
            >>> for chunk, score in results:
            ...     print(f"{chunk.id}: {score:.3f}")
        """
        if not self.embeddings:
            logger.warning("Vector store is empty, returning no results")
            return []
        
        # Validate query embedding dimension
        if query_embedding.shape[0] != self.embedding_dim:
            raise ValueError(
                f"Query embedding dimension mismatch. "
                f"Expected {self.embedding_dim}, got {query_embedding.shape[0]}"
            )
        
        # Normalize query embedding
        normalized_query = self._normalize(query_embedding)
        
        # Compute similarities
        similarities: List[Tuple[str, float, Chunk]] = []
        
        for chunk_id, stored in self.embeddings.items():
            similarity = self._cosine_similarity(normalized_query, stored.embedding)
            similarities.append((chunk_id, similarity, stored.chunk))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by threshold and limit to top_k
        results = [
            (chunk, score)
            for chunk_id, score, chunk in similarities[:top_k]
            if score >= threshold
        ]
        
        logger.info(
            f"Search returned {len(results)} results "
            f"(top_k={top_k}, threshold={threshold})"
        )
        
        return results
    
    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """
        Retrieve a chunk by ID.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Chunk object if found, None otherwise
        """
        stored = self.embeddings.get(chunk_id)
        return stored.chunk if stored else None
    
    def get_embedding(self, chunk_id: str) -> Optional[np.ndarray]:
        """
        Retrieve an embedding by chunk ID.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            Embedding vector if found, None otherwise
        """
        stored = self.embeddings.get(chunk_id)
        return stored.embedding if stored else None
    
    def remove_embedding(self, chunk_id: str) -> bool:
        """
        Remove an embedding from the store.
        
        Args:
            chunk_id: Chunk identifier
            
        Returns:
            True if removed, False if not found
        """
        if chunk_id in self.embeddings:
            del self.embeddings[chunk_id]
            logger.debug(f"Removed embedding for chunk {chunk_id}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all embeddings from the store."""
        count = len(self.embeddings)
        self.embeddings.clear()
        logger.info(f"Cleared {count} embeddings from store")
    
    def size(self) -> int:
        """Get the number of embeddings in the store."""
        return len(self.embeddings)
    
    def get_all_chunk_ids(self) -> List[str]:
        """Get all chunk IDs in the store."""
        return list(self.embeddings.keys())
    
    @staticmethod
    def _normalize(vector: np.ndarray) -> np.ndarray:
        """
        Normalize a vector to unit length.
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.
        
        Assumes vectors are already normalized (for performance).
        
        Args:
            vec1: First vector (normalized)
            vec2: Second vector (normalized)
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        # For normalized vectors: cosine_sim = dot_product
        similarity = float(np.dot(vec1, vec2))
        
        # Clamp to [0, 1] range (handle floating point errors)
        return max(0.0, min(1.0, similarity))
    
    def compute_similarity_matrix(self) -> np.ndarray:
        """
        Compute pairwise similarity matrix for all stored embeddings.
        
        Returns:
            Similarity matrix (N x N) where N is number of embeddings
            
        Use case: Analysis, clustering, duplicate detection
        """
        if not self.embeddings:
            return np.array([])
        
        chunk_ids = list(self.embeddings.keys())
        n = len(chunk_ids)
        
        # Create matrix
        similarity_matrix = np.zeros((n, n))
        
        for i, id1 in enumerate(chunk_ids):
            for j, id2 in enumerate(chunk_ids):
                if i == j:
                    similarity_matrix[i, j] = 1.0
                elif i < j:  # Compute only upper triangle (symmetric matrix)
                    sim = self._cosine_similarity(
                        self.embeddings[id1].embedding,
                        self.embeddings[id2].embedding
                    )
                    similarity_matrix[i, j] = sim
                    similarity_matrix[j, i] = sim  # Mirror
        
        return similarity_matrix
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with statistics
        """
        if not self.embeddings:
            return {
                "size": 0,
                "embedding_dim": self.embedding_dim,
                "section_types": {}
            }
        
        # Count chunks by section type
        section_counts = {}
        for stored in self.embeddings.values():
            section_type = stored.chunk.section_type or "unknown"
            section_counts[section_type] = section_counts.get(section_type, 0) + 1
        
        return {
            "size": len(self.embeddings),
            "embedding_dim": self.embedding_dim,
            "section_types": section_counts,
            "chunk_ids": self.get_all_chunk_ids()
        }
    
    def __len__(self) -> int:
        """Support len() function."""
        return len(self.embeddings)
    
    def __contains__(self, chunk_id: str) -> bool:
        """Support 'in' operator."""
        return chunk_id in self.embeddings
    
    def __repr__(self) -> str:
        return (
            f"InMemoryVectorStore("
            f"size={len(self.embeddings)}, "
            f"dim={self.embedding_dim})"
        )
