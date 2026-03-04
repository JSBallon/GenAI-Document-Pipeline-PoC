"""
Vector Retrieval for RAG-based Skill Matching.

Implementiert Embedding-basierte Retrieval für CV Chunks basierend auf Job Requirements.
Integriert LocalEmbedder und InMemoryVectorStore für semantisches Matching.

Architecture Pattern 4.3: RAG Patterns
- Top-K Retrieval with Relevance Threshold (Pattern 4.3.3)
- Multi-Factor Ranking (Pattern 4.3.4)
- Retrieval Logging (Pattern 4.5.3)

SOLID Principles:
- Single Responsibility: Retrieval-Logik isoliert
- Dependency Injection: Embedder und VectorStore injiziert
- Open/Closed: Erweiterbar für neue Ranking-Strategien
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path

import numpy as np

from .models import Chunk, Requirement, RequirementExtractionResult
from .embedder import LocalEmbedder
from .vector_store import InMemoryVectorStore


logger = logging.getLogger(__name__)


class RetrievalResult:
    """
    Container für Retrieval-Ergebnisse eines Requirements.
    
    Attributes:
        requirement: Das gesuchte Requirement
        retrieved_chunks: Liste von (Chunk, score) Tupeln
        query_embedding: Das verwendete Query-Embedding
        retrieval_params: Parameter der Retrieval-Operation
        timestamp: Zeitpunkt der Retrieval-Operation
    """
    
    def __init__(
        self,
        requirement: Requirement,
        retrieved_chunks: List[Tuple[Chunk, float]],
        query_embedding: np.ndarray,
        retrieval_params: Dict[str, Any]
    ):
        self.requirement = requirement
        self.retrieved_chunks = retrieved_chunks
        self.query_embedding = query_embedding
        self.retrieval_params = retrieval_params
        self.timestamp = datetime.now().isoformat()
    
    @property
    def chunk_count(self) -> int:
        """Anzahl der gefundenen Chunks."""
        return len(self.retrieved_chunks)
    
    @property
    def best_score(self) -> float:
        """Bester Similarity Score (erster Chunk)."""
        return self.retrieved_chunks[0][1] if self.retrieved_chunks else 0.0
    
    @property
    def average_score(self) -> float:
        """Durchschnittlicher Similarity Score."""
        if not self.retrieved_chunks:
            return 0.0
        return sum(score for _, score in self.retrieved_chunks) / len(self.retrieved_chunks)
    
    @property
    def has_sufficient_evidence(self) -> bool:
        """Prüft, ob ausreichend Evidence gefunden wurde (>=2 Chunks)."""
        return len(self.retrieved_chunks) >= 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiere zu Dictionary für Logging/Serialisierung."""
        return {
            "requirement_id": self.requirement.requirement_id,
            "requirement_text": self.requirement.text,
            "requirement_priority": self.requirement.priority,
            "chunk_count": self.chunk_count,
            "best_score": self.best_score,
            "average_score": self.average_score,
            "has_sufficient_evidence": self.has_sufficient_evidence,
            "retrieved_chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "section_type": chunk.section_type,
                    "score": score,
                    "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text
                }
                for chunk, score in self.retrieved_chunks
            ],
            "retrieval_params": self.retrieval_params,
            "timestamp": self.timestamp
        }


class VectorRetriever:
    """
    RAG-basierter Vector Retriever für Skill Matching.
    
    Features:
    - Embedding-basierte semantische Suche
    - Top-K Retrieval mit Score-Threshold
    - Multi-Factor Re-Ranking (Semantic + Recency + Section Type)
    - Retrieval Logging für Governance
    - Batch Processing für Multiple Requirements
    
    Design Pattern: Strategy Pattern für Ranking-Algorithmen
    
    Attributes:
        embedder: LocalEmbedder für Query-Embeddings
        vector_store: InMemoryVectorStore mit CV-Chunk-Embeddings
        top_k: Standard Top-K Parameter (default: 5)
        threshold: Standard Relevance Threshold (default: 0.3)
        enable_reranking: Multi-Factor Re-Ranking aktivieren
        enable_logging: Retrieval Logging aktivieren
    """
    
    # Standard-Parameter aus Decision C3 (activeContext_M2.md)
    DEFAULT_TOP_K = 5
    DEFAULT_THRESHOLD = 0.3
    INSUFFICIENT_EVIDENCE_THRESHOLD = 2
    
    def __init__(
        self,
        embedder: LocalEmbedder,
        vector_store: InMemoryVectorStore,
        top_k: int = DEFAULT_TOP_K,
        threshold: float = DEFAULT_THRESHOLD,
        enable_reranking: bool = True,
        enable_logging: bool = True,
        log_dir: Optional[str] = None
    ):
        """
        Initialize VectorRetriever.
        
        Args:
            embedder: LocalEmbedder für Query-Embeddings
            vector_store: InMemoryVectorStore mit CV-Chunk-Embeddings
            top_k: Standard Top-K Parameter (default: 5)
            threshold: Minimum Similarity Score (default: 0.3)
            enable_reranking: Multi-Factor Re-Ranking aktivieren
            enable_logging: Retrieval Logging aktivieren
            log_dir: Directory für Retrieval Logs (default: logs/retrieval)
        """
        self.embedder = embedder
        self.vector_store = vector_store
        self.top_k = top_k
        self.threshold = threshold
        self.enable_reranking = enable_reranking
        self.enable_logging = enable_logging
        
        # Setup Logging Directory
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            self.log_dir = Path("logs") / "retrieval"
        
        if enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"VectorRetriever initialized: "
            f"top_k={top_k}, threshold={threshold}, "
            f"reranking={enable_reranking}, logging={enable_logging}"
        )
    
    def retrieve(
        self,
        requirement: Requirement,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> RetrievalResult:
        """
        Retrieve relevante CV-Chunks für ein Requirement.
        
        Args:
            requirement: Job Requirement zum Matchen
            top_k: Override für Top-K Parameter (default: self.top_k)
            threshold: Override für Threshold (default: self.threshold)
        
        Returns:
            RetrievalResult mit gefundenen Chunks und Scores
        
        Example:
            >>> retriever = VectorRetriever(embedder, vector_store)
            >>> requirement = Requirement(text="Python development", ...)
            >>> result = retriever.retrieve(requirement)
            >>> print(f"Found {result.chunk_count} chunks, best score: {result.best_score:.3f}")
        """
        # Parameter Override
        k = top_k if top_k is not None else self.top_k
        t = threshold if threshold is not None else self.threshold
        
        logger.info(
            f"Retrieving for requirement '{requirement.text}' "
            f"(priority: {requirement.priority}, top_k={k}, threshold={t})"
        )
        
        # 1. Embed Query (Requirement Text)
        query_embedding = self.embedder.embed_query(
            query=requirement.text,
            query_type="job_requirement"
        )
        
        # 2. Vector Search
        retrieved_chunks = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            threshold=t
        )
        
        # 3. Multi-Factor Re-Ranking (optional)
        if self.enable_reranking and retrieved_chunks:
            retrieved_chunks = self._rerank_chunks(
                chunks_with_scores=retrieved_chunks,
                requirement=requirement
            )
        
        # 4. Create Result
        result = RetrievalResult(
            requirement=requirement,
            retrieved_chunks=retrieved_chunks,
            query_embedding=query_embedding,
            retrieval_params={
                "top_k": k,
                "threshold": t,
                "reranking_enabled": self.enable_reranking
            }
        )
        
        # 5. Log Result (Governance Pattern 4.5.3)
        if self.enable_logging:
            self._log_retrieval(result)
        
        # 6. Warn if Insufficient Evidence
        if not result.has_sufficient_evidence:
            logger.warning(
                f"Insufficient evidence for requirement '{requirement.text}': "
                f"Only {result.chunk_count} chunks found (threshold: {self.INSUFFICIENT_EVIDENCE_THRESHOLD})"
            )
        
        logger.info(
            f"Retrieved {result.chunk_count} chunks for '{requirement.text}' "
            f"(best score: {result.best_score:.3f}, avg: {result.average_score:.3f})"
        )
        
        return result
    
    def batch_retrieve(
        self,
        requirements: List[Requirement],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Batch-Retrieval für mehrere Requirements.
        
        Args:
            requirements: Liste von Requirements
            top_k: Override für Top-K Parameter
            threshold: Override für Threshold
        
        Returns:
            Liste von RetrievalResult für jedes Requirement
        
        Example:
            >>> results = retriever.batch_retrieve(requirements)
            >>> total_chunks = sum(r.chunk_count for r in results)
        """
        logger.info(f"Starting batch retrieval for {len(requirements)} requirements")
        
        results = []
        for requirement in requirements:
            try:
                result = self.retrieve(
                    requirement=requirement,
                    top_k=top_k,
                    threshold=threshold
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to retrieve for requirement '{requirement.text}': {e}"
                )
                # Create empty result for failed retrieval
                results.append(RetrievalResult(
                    requirement=requirement,
                    retrieved_chunks=[],
                    query_embedding=np.zeros(self.embedder.get_embedding_dimension()),
                    retrieval_params={"error": str(e)}
                ))
        
        logger.info(
            f"Batch retrieval complete: {len(results)} results, "
            f"avg chunks per requirement: {sum(r.chunk_count for r in results) / len(results):.1f}"
        )
        
        return results
    
    def retrieve_from_extraction_result(
        self,
        extraction_result: RequirementExtractionResult,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve für alle Requirements aus einem ExtractionResult.
        
        Args:
            extraction_result: RequirementExtractionResult mit Requirements
            top_k: Override für Top-K Parameter
            threshold: Override für Threshold
        
        Returns:
            Liste von RetrievalResult für alle Requirements
        """
        return self.batch_retrieve(
            requirements=extraction_result.requirements,
            top_k=top_k,
            threshold=threshold
        )
    
    def _rerank_chunks(
        self,
        chunks_with_scores: List[Tuple[Chunk, float]],
        requirement: Requirement
    ) -> List[Tuple[Chunk, float]]:
        """
        Multi-Factor Re-Ranking (Pattern 4.3.4).
        
        Kombiniert:
        - Semantic Similarity (50%)
        - Recency Score (20%)
        - Section Type Weight (20%)
        - Keyword Overlap (10%)
        
        Args:
            chunks_with_scores: Original (Chunk, semantic_score) Tupel
            requirement: Das gesuchte Requirement
        
        Returns:
            Re-ranked (Chunk, final_score) Tupel
        """
        if not chunks_with_scores:
            return []
        
        reranked = []
        
        for chunk, semantic_score in chunks_with_scores:
            # Factor 1: Semantic Similarity (Base Score) - 50%
            semantic_weight = 0.5
            
            # Factor 2: Recency Score - 20%
            recency_score = chunk.metadata.get("recency_score", 0.5)  # Default: Medium Recency
            recency_weight = 0.2
            
            # Factor 3: Section Type Weight - 20%
            section_weights = {
                "experience": 1.2,
                "skills": 1.0,
                "education": 0.8,
                "summary": 0.9,
                "projects": 1.1
            }
            section_score = section_weights.get(chunk.section_type, 1.0)
            section_weight = 0.2
            
            # Factor 4: Keyword Overlap - 10%
            keyword_score = self._calculate_keyword_overlap(chunk.text, requirement.text)
            keyword_weight = 0.1
            
            # Weighted Combination
            final_score = (
                semantic_weight * semantic_score +
                recency_weight * recency_score +
                section_weight * (section_score / 1.2) +  # Normalize to [0,1]
                keyword_weight * keyword_score
            )
            
            reranked.append((chunk, final_score))
        
        # Re-sort by final score (descending)
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        logger.debug(
            f"Re-ranked {len(reranked)} chunks: "
            f"best score {reranked[0][1]:.3f} → {reranked[0][1]:.3f}"
        )
        
        return reranked
    
    def _calculate_keyword_overlap(self, chunk_text: str, requirement_text: str) -> float:
        """
        Berechne Keyword-Overlap zwischen Chunk und Requirement.
        
        Simple Token-based Overlap (für PoC ausreichend).
        
        Args:
            chunk_text: Text des Chunks
            requirement_text: Text des Requirements
        
        Returns:
            Overlap Score (0.0 - 1.0)
        """
        # Normalize & Tokenize
        chunk_tokens = set(chunk_text.lower().split())
        req_tokens = set(requirement_text.lower().split())
        
        if not req_tokens:
            return 0.0
        
        # Jaccard Similarity
        intersection = chunk_tokens & req_tokens
        union = chunk_tokens | req_tokens
        
        return len(intersection) / len(union) if union else 0.0
    
    def _log_retrieval(self, result: RetrievalResult) -> None:
        """
        Log Retrieval Result (Governance Pattern 4.5.3).
        
        Format: JSONL (one line per retrieval operation)
        Storage: logs/retrieval/YYYY-MM-DD.jsonl
        
        Args:
            result: RetrievalResult zum Loggen
        """
        try:
            # Log File: logs/retrieval/YYYY-MM-DD.jsonl
            log_file = self.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
            
            # Log Entry
            log_entry = {
                "event_type": "retrieval",
                "timestamp": result.timestamp,
                "requirement": {
                    "id": result.requirement.requirement_id,
                    "text": result.requirement.text,
                    "category": result.requirement.category,
                    "priority": result.requirement.priority
                },
                "results": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "section_type": chunk.section_type,
                        "score": float(score),
                        "rank": idx + 1,
                        "text_preview": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text
                    }
                    for idx, (chunk, score) in enumerate(result.retrieved_chunks)
                ],
                "retrieval_params": result.retrieval_params,
                "statistics": {
                    "chunk_count": result.chunk_count,
                    "best_score": float(result.best_score),
                    "average_score": float(result.average_score),
                    "has_sufficient_evidence": result.has_sufficient_evidence
                }
            }
            
            # Append to JSONL file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            logger.debug(f"Logged retrieval to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log retrieval: {e}")
            # Don't fail retrieval if logging fails
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get Statistics about the Retriever and Vector Store.
        
        Returns:
            Dictionary mit Statistiken
        """
        vector_store_stats = self.vector_store.get_statistics()
        
        return {
            "retriever": {
                "default_top_k": self.top_k,
                "default_threshold": self.threshold,
                "reranking_enabled": self.enable_reranking,
                "logging_enabled": self.enable_logging
            },
            "vector_store": vector_store_stats,
            "embedder": {
                "model": self.embedder.model_name,
                "dimension": self.embedder.get_embedding_dimension()
            }
        }
    
    def __repr__(self) -> str:
        return (
            f"VectorRetriever("
            f"top_k={self.top_k}, "
            f"threshold={self.threshold}, "
            f"store_size={len(self.vector_store)})"
        )
