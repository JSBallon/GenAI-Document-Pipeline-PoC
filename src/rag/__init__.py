"""
RAG (Retrieval-Augmented Generation) Module für CV-Analyse.

Enthält Komponenten für:
- Chunking: CV-Dokumente in semantische Einheiten zerlegen
- Embedding: Chunks in Vektorraum transformieren
- Retrieval: Relevante Chunks basierend auf Job-Anforderungen finden
- Evidence Linking: Output-Statements mit Source-Chunks verknüpfen
"""

from .chunker import HybridChunker
from .embedder import LocalEmbedder
from .retriever import VectorRetriever
from .requirement_extractor import SimpleRequirementExtractor
from .evidence_linker import EvidenceLinker, EvidenceLinkerConfig
from .models import Chunk, Requirement, RequirementExtractionResult

__all__ = [
    "Chunk",
    "Requirement",
    "RequirementExtractionResult",
    "HybridChunker",
    "LocalEmbedder",
    "VectorRetriever",
    "SimpleRequirementExtractor",
    "EvidenceLinker",
    "EvidenceLinkerConfig"
]
