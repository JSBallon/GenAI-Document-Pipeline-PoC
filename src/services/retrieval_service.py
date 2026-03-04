"""RAG Retrieval helper service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.models.cv import CVModel
from src.models.job_ad import JobAdModel
from src.rag.chunker import HybridChunker
from src.rag.embedder import LocalEmbedder
from src.rag.requirement_extractor import SimpleRequirementExtractor
from src.rag.retriever import VectorRetriever
from src.rag.vector_store import InMemoryVectorStore
from src.infrastructure.logging_service import LoggingService


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    score: float
    text: str
    section_type: str
    requirement: str


class RetrievalResult:
    def __init__(
        self,
        trace_id: str,
        retrieved_chunks: List[RetrievedChunk],
        requirements: List[str],
    ) -> None:
        self.trace_id = trace_id
        self.retrieved_chunks = retrieved_chunks
        self.requirements = requirements
        self.metadata: Dict[str, Any] = {}


class RetrievalService:
    """RAG Retrieval Ablauf mit Logging."""

    def __init__(
        self,
        logging_service: LoggingService,
        chunker: HybridChunker | None = None,
        embedder: LocalEmbedder | None = None,
        extractor: SimpleRequirementExtractor | None = None,
    ) -> None:
        self._logging_service = logging_service
        self._chunker = chunker or HybridChunker()
        self._embedder = embedder or LocalEmbedder()
        self._extractor = extractor or SimpleRequirementExtractor()

    def chunk_and_retrieve(
        self,
        cv_model: CVModel,
        job_model: JobAdModel,
        trace_id: str,
    ) -> RetrievalResult:
        chunks = self._chunker.chunk_cv(cv_model)
        embeddings = self._embedder.batch_embed_chunks(chunks)

        vector_store = InMemoryVectorStore(
            embedding_dim=self._embedder.get_embedding_dimension()
        )
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        vector_store.add_embeddings(chunk_ids, embeddings, chunks)

        retriever = VectorRetriever(
            embedder=self._embedder,
            vector_store=vector_store,
            enable_logging=False
        )

        requirements = self._extractor.extract(job_model)
        requirement_list = requirements.requirements
        requirement_texts = [req.text for req in requirement_list]
        collected_chunks: List[RetrievedChunk] = []

        for requirement in requirement_list:
            self._logging_service.log_retrieval_start(
                trace_id=trace_id,
                requirement=requirement.text,
            )
            try:
                result = retriever.retrieve(requirement)
                structured = [
                    {
                        "chunk_id": chunk.chunk_id,
                        "score": score,
                        "text": chunk.text,
                        "section_type": chunk.section_type,
                    }
                    for chunk, score in result.retrieved_chunks
                ]
                self._logging_service.log_retrieval_success(
                    trace_id=trace_id,
                    requirement=requirement.text,
                    chunks=structured,
                    retrieval_params=result.retrieval_params,
                )
                retrieved_chunks = [
                    RetrievedChunk(
                        chunk_id=chunk.chunk_id,
                        score=score,
                        text=chunk.text,
                        section_type=chunk.section_type or "unknown",
                        requirement=requirement.text,
                    )
                    for chunk, score in result.retrieved_chunks
                ]
                collected_chunks.extend(retrieved_chunks)
            except Exception as exc:
                self._logging_service.log_retrieval_failure(
                    trace_id=trace_id,
                    requirement=requirement.text,
                    error=str(exc),
                )
                raise

        result = RetrievalResult(
            trace_id=trace_id,
            retrieved_chunks=collected_chunks,
            requirements=requirement_texts,
        )
        result.metadata["retrieval_count"] = len(collected_chunks)
        return result