"""
Evidence Linking für RAG Outputs.

Verknüpft Output-Statements (Absätze) mit Source-Chunks
aus Retrieval Results und erzeugt Inline-Citations + Mapping-Metadata.

SOLID Principles:
- Single Responsibility: Evidence Linking isoliert
- Dependency Injection: keine internen Instanzen
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple

from src.rag.models import AnnotatedOutput, EvidenceMap, EvidenceLink
from src.rag.retriever import RetrievalResult
from src.rag.models import Chunk


@dataclass(frozen=True)
class EvidenceLinkerConfig:
    """
    Konfiguration für EvidenceLinker.

    Attributes:
        max_chunks_per_statement: Maximale Anzahl zitierter Chunks
        include_text_preview: Ob Chunk-Previews im Mapping enthalten sind
    """

    max_chunks_per_statement: int = 2
    include_text_preview: bool = True


class EvidenceLinker:
    """
    Verknüpft Output-Statements mit Source-Chunks (Evidence Linking).

    Strategy:
    - Output wird absatzbasiert segmentiert
    - Statements werden den Retrieval Results in Reihenfolge zugeordnet
    - Inline-Citations im Format: [Source: <chunk_id>, Score: 0.87]
    """

    def __init__(self, config: EvidenceLinkerConfig | None = None):
        self._config = config or EvidenceLinkerConfig()

    def link_output_to_sources(
        self,
        output_text: str,
        retrieval_results: List[RetrievalResult],
        source_type: str
    ) -> AnnotatedOutput:
        """
        Erzeuge annotierten Output + Evidence Map.

        Args:
            output_text: LLM Output (CV oder Anschreiben)
            retrieval_results: Retrieval Results in Reihenfolge
            source_type: 'cv' oder 'cover_letter'

        Returns:
            AnnotatedOutput mit Inline-Citations und Mapping
        """
        statements = self._split_into_paragraphs(output_text)
        evidence_links: List[EvidenceLink] = []
        annotated_statements: List[str] = []

        for idx, statement in enumerate(statements, start=1):
            retrieval = self._safe_get_retrieval(retrieval_results, idx - 1)
            cited_chunks = self._select_cited_chunks(retrieval)
            citation_text = self._format_citations(cited_chunks)
            annotated = statement if not citation_text else f"{statement} {citation_text}"

            evidence_links.append(
                EvidenceLink(
                    statement_id=f"stmt_{idx:03d}",
                    statement_text=statement,
                    cited_chunks=self._build_cited_chunk_payload(cited_chunks)
                )
            )
            annotated_statements.append(annotated)

        annotated_text = "\n\n".join(annotated_statements)
        evidence_map = EvidenceMap(
            source_type=source_type,
            statements=evidence_links,
            summary=self._build_summary(evidence_links)
        )

        return AnnotatedOutput(
            annotated_text=annotated_text,
            evidence_map=evidence_map
        )

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Split text in Paragraphs (absatzbasiert).
        Entfernt leere Blöcke.
        """
        blocks = re.split(r"\n\s*\n", text.strip())
        return [b.strip() for b in blocks if b.strip()]

    def _safe_get_retrieval(
        self,
        retrieval_results: List[RetrievalResult],
        index: int
    ) -> RetrievalResult | None:
        if index < 0 or index >= len(retrieval_results):
            return None
        return retrieval_results[index]

    def _select_cited_chunks(
        self,
        retrieval_result: RetrievalResult | None
    ) -> List[Tuple[Chunk, float]]:
        if retrieval_result is None:
            return []
        return retrieval_result.retrieved_chunks[: self._config.max_chunks_per_statement]

    def _format_citations(self, chunks: List[Tuple[Chunk, float]]) -> str:
        if not chunks:
            return ""
        citations = [
            f"[Source: {chunk.chunk_id}, Score: {score:.2f}]"
            for chunk, score in chunks
        ]
        return " ".join(citations)

    def _build_cited_chunk_payload(
        self,
        chunks: List[Tuple[Chunk, float]]
    ) -> List[Dict[str, object]]:
        payload = []
        for chunk, score in chunks:
            entry: Dict[str, object] = {
                "chunk_id": chunk.chunk_id,
                "section_type": chunk.section_type,
                "score": float(score)
            }
            if self._config.include_text_preview:
                entry["text_preview"] = (
                    chunk.text[:120] + "..." if len(chunk.text) > 120 else chunk.text
                )
            payload.append(entry)
        return payload

    def _build_summary(self, evidence_links: List[EvidenceLink]) -> Dict[str, object]:
        total_statements = len(evidence_links)
        statements_with_sources = sum(1 for link in evidence_links if link.cited_chunks)
        total_citations = sum(len(link.cited_chunks) for link in evidence_links)

        return {
            "total_statements": total_statements,
            "statements_with_sources": statements_with_sources,
            "total_citations": total_citations
        }