"""
Streamlit Evidence View für Output-Source-Traceability.

Zeigt:
- Annotierten Output mit Inline-Citations
- Evidence Mapping Tabelle (Statement → Chunk → Score → Preview)

Dependencies:
- HybridChunker
- LocalEmbedder
- InMemoryVectorStore
- SimpleRequirementExtractor
- VectorRetriever
- EvidenceLinker
"""

import logging
from typing import List

import pandas as pd
import streamlit as st

from src.parsers.cv_parser import CVParser
from src.parsers.job_parser import JobAdParser
from src.rag.chunker import HybridChunker
from src.rag.embedder import LocalEmbedder
from src.rag.vector_store import InMemoryVectorStore
from src.rag.requirement_extractor import SimpleRequirementExtractor
from src.rag.retriever import VectorRetriever, RetrievalResult
from src.rag.evidence_linker import EvidenceLinker


logger = logging.getLogger(__name__)


def show_evidence_view(cv_path: str, job_path: str) -> None:
    """
    Hauptfunktion für Evidence View.

    Workflow:
    1. Parse CV + JobAd
    2. Chunk CV → Embed → Store
    3. Extract Requirements
    4. Retrieval Results (alle Requirements)
    5. Evidence Linking auf CV + Anschreiben Demo-Text
    """
    st.header("🔗 Evidence Linking & Source Attribution")
    st.caption("Trace Output-Statements zu den zugrunde liegenden CV-Chunks")

    try:
        with st.spinner("📚 Lade CV und JobAd..."):
            cv_parser = CVParser()
            job_parser = JobAdParser()

            cv_model = cv_parser.parse_file(cv_path)
            job_model = job_parser.parse_file(job_path)

        with st.spinner("🔪 Segmentiere CV..."):
            chunker = HybridChunker()
            chunks = chunker.chunk_cv(cv_model)

        with st.spinner("🧠 Erstelle Embeddings..."):
            embedder = LocalEmbedder()
            embeddings = embedder.batch_embed_chunks(chunks)
            vector_store = InMemoryVectorStore(embedding_dim=embedder.get_embedding_dimension())
            chunk_ids = [chunk.chunk_id for chunk in chunks]
            vector_store.add_embeddings(chunk_ids, embeddings, chunks)

        with st.spinner("📋 Extrahiere Requirements..."):
            extractor = SimpleRequirementExtractor()
            extraction_result = extractor.extract(job_model)

        with st.spinner("🔍 Retrieval für Requirements..."):
            retriever = VectorRetriever(
                embedder=embedder,
                vector_store=vector_store,
                top_k=5,
                threshold=0.3,
                enable_reranking=True,
                enable_logging=False
            )
            retrieval_results = retriever.retrieve_from_extraction_result(extraction_result)

        st.divider()
        _show_evidence_for_output(
            output_label="CV (Demo-Ausgabe)",
            output_text=_build_demo_cv_output(cv_model),
            retrieval_results=retrieval_results,
            source_type="cv"
        )

        st.divider()
        _show_evidence_for_output(
            output_label="Anschreiben (Demo-Ausgabe)",
            output_text=_build_demo_cover_letter_output(cv_model, job_model),
            retrieval_results=retrieval_results,
            source_type="cover_letter"
        )

    except FileNotFoundError as e:
        st.error(f"❌ Datei nicht gefunden: {e}")
        logger.error(f"File not found in evidence view: {e}")
    except Exception as e:
        st.error(f"❌ Fehler beim Laden der Daten: {e}")
        logger.exception(f"Error in evidence view: {e}")


def _show_evidence_for_output(
    output_label: str,
    output_text: str,
    retrieval_results: List[RetrievalResult],
    source_type: str
) -> None:
    """
    Render Evidence für einen Output-Text.
    """
    st.subheader(output_label)
    linker = EvidenceLinker()
    annotated = linker.link_output_to_sources(
        output_text=output_text,
        retrieval_results=retrieval_results,
        source_type=source_type
    )

    st.markdown("**📝 Annotierter Output**")
    st.text_area(
        "annotated_output",
        annotated.annotated_text,
        height=250,
        label_visibility="collapsed"
    )

    st.markdown("**🔎 Evidence Mapping**")
    table = _build_evidence_table(annotated.evidence_map.statements)
    if table.empty:
        st.info("Keine Evidence Links gefunden.")
    else:
        st.dataframe(table, use_container_width=True)

    st.markdown("**📊 Summary**")
    st.json(annotated.evidence_map.summary)


def _build_evidence_table(statements) -> pd.DataFrame:
    rows = []
    for link in statements:
        if not link.cited_chunks:
            rows.append({
                "statement_id": link.statement_id,
                "statement": link.statement_text,
                "chunk_id": "—",
                "score": "—",
                "preview": "—"
            })
            continue

        for chunk in link.cited_chunks:
            rows.append({
                "statement_id": link.statement_id,
                "statement": link.statement_text,
                "chunk_id": chunk.get("chunk_id"),
                "score": f"{chunk.get('score', 0):.2f}",
                "preview": chunk.get("text_preview", "")
            })

    return pd.DataFrame(rows)


def _build_demo_cv_output(cv_model) -> str:
    """
    Leichte Demo-Ausgabe aus CV-Daten (statt LLM-Call).
    """
    parts = [
        f"Kurzprofil: {cv_model.profile_summary or 'Berufserfahrener Kandidat mit Fokus auf Backend und Daten.'}",
        f"Berufserfahrung: {cv_model.berufserfahrung[0].position} bei {cv_model.berufserfahrung[0].company}"
        if cv_model.berufserfahrung else "Berufserfahrung: Nicht angegeben.",
        f"Skills: {', '.join([s for lst in cv_model.skills.values() for s in lst][:6])}"
        if cv_model.skills else "Skills: Nicht angegeben."
    ]
    return "\n\n".join(parts)


def _build_demo_cover_letter_output(cv_model, job_model) -> str:
    """
    Leichte Demo-Ausgabe für Anschreiben (statt LLM-Call).
    """
    greeting = f"Sehr geehrte Damen und Herren," if not job_model.company else f"Sehr geehrte Damen und Herren von {job_model.company},"
    body = (
        f"mit großer Motivation bewerbe ich mich als {job_model.job_title}. "
        f"Meine Erfahrungen in der Backend-Entwicklung und meine Skills in {', '.join([s for lst in cv_model.skills.values() for s in lst][:4])} "
        "passen hervorragend zu Ihren Anforderungen."
    )
    closing = "Ich freue mich auf ein persönliches Gespräch."
    return "\n\n".join([greeting, body, closing])