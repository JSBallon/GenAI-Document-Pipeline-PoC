"""
Streamlit Retrieval View für RAG-basiertes Skill Matching - Pipeline Flow V2.

Redesigned für Sequential Pipeline Flow mit Session State Integration.
Interaktive Parameter-Slider für Top-K und Threshold mit Auto Re-Retrieval.

Task: M2 Task 2.5a - Streamlit Retrieval View (Redesign)
Version: 2.0 (Pipeline Flow Integration)
Dependencies: Session State (Stage 1+2), RequirementExtractor, VectorRetriever
"""

import streamlit as st
import pandas as pd
import logging
from datetime import date
from typing import Tuple

from src.rag.requirement_extractor import SimpleRequirementExtractor
from src.rag.embedder import LocalEmbedder
from src.rag.vector_store import InMemoryVectorStore
from src.rag.retriever import VectorRetriever
from src.rag.models import Requirement


logger = logging.getLogger(__name__)


def show_retrieval_view(cv_path: str, job_path: str) -> None:
    """
    Hauptfunktion für Retrieval View - Pipeline Flow V2.
    
    Workflow:
    1. One-Time Setup: Requirements Extraction & Vector Store (Stage 3 Entry)
    2. Interactive Slider Configuration (Top-K, Threshold)
    3. Requirement Selection
    4. Perform Retrieval (Auto Re-Retrieval on Slider Change)
    5. Display Results
    
    Args:
        cv_path: Pfad zur CV.md Datei (für Logging)
        job_path: Pfad zur JobAd.md Datei (für Logging)
    
    Notes:
        - Nutzt Session State aus Stage 1 (cv_model, job_model)
        - Nutzt Session State aus Stage 2 (chunks)
        - Erstellt Session State für Stage 3 (requirements, vector_store)
    """
    st.header("🔍 Skill Matching & Retrieval")
    st.caption("RAG-basierte semantische Suche für Job Requirements")

    _log_date = date.today().strftime("%Y-%m-%d")
    st.caption(f"📋 **Audit-Trail** — `./logs/retrieval/{_log_date}.jsonl`")

    # Governance Information
    st.info("""
    **Was passiert hier?**  
    Requirements werden aus der JobAd extrahiert und mit CV-Chunks semantisch verglichen. 
    Ein Vector Store findet die relevantesten CV-Abschnitte für jedes Requirement basierend auf Embeddings.
    
    **🛡️ Governance Controls:**
    - **Lokale Embeddings:** Alle Embeddings werden lokal generiert (keine CV-Daten an Cloud-APIs)
    - **Decision Logging:** Threshold- und Top-K-Entscheidungen werden protokolliert (JSONL)
    - **Transparente Parameter:** Interaktive Slider zeigen Retrieval-Entscheidungen in Echtzeit
    - **Score-basierte Filterung:** Nur Chunks über dem Threshold werden verwendet
    """)
    
    try:
        # 1. One-Time Setup (Requirements + Vector Store)
        _initialize_requirements_and_vector_store()
        
        # 2. Display Statistics Dashboard
        _show_statistics_dashboard()
        
        st.divider()
        
        # 3. Interactive Parameter Configuration
        top_k, threshold = _show_parameter_sliders()
        
        # 4. Requirement Selection & Results Display
        _show_requirement_selector_and_results(top_k, threshold)
        
    except Exception as e:
        st.error(f"❌ Fehler in Retrieval View: {e}")
        logger.exception(f"Error in retrieval view: {e}")
        st.stop()


def _initialize_requirements_and_vector_store() -> None:
    """
    One-Time Setup: Requirements Extraction & Vector Store Indexing.

    Runs only once when entering Stage 3 (pipeline_stage == 3).
    Uses Session State from previous stages:
    - job_model (Stage 1)
    - chunks (Stage 2)

    Creates Session State for Stage 3+:
    - requirements
    - vector_store
    - embedder (stored for retrieval)
    - retrieval_result  (RetrievalService result — logged immediately)
    - retrieval_trace_id
    """
    # 1. Extract Requirements (if not already done)
    if st.session_state.requirements is None:
        with st.spinner("📋 Extrahiere Requirements..."):
            extractor = SimpleRequirementExtractor()
            extraction_result = extractor.extract(st.session_state.job_model)

            # Store requirements (unwrap from ExtractionResult)
            st.session_state.requirements = extraction_result.requirements

            st.success(f"✅ {len(st.session_state.requirements)} Requirements extrahiert")
            logger.info(f"Requirements extracted: {len(st.session_state.requirements)}")

    # 2. Build Vector Store (if not already done)
    if st.session_state.vector_store is None:
        with st.spinner("🧠 Erstelle Vector Store..."):
            embedder = LocalEmbedder()

            # Embed all chunks
            embeddings = embedder.batch_embed_chunks(st.session_state.chunks)

            # Initialize vector store
            vector_store = InMemoryVectorStore(
                embedding_dim=embedder.get_embedding_dimension()
            )

            # Add chunks with embeddings to vector store
            chunk_ids = [chunk.chunk_id for chunk in st.session_state.chunks]
            vector_store.add_embeddings(chunk_ids, embeddings, st.session_state.chunks)

            # Store in session state
            st.session_state.vector_store = vector_store
            st.session_state.embedder = embedder  # Store for retriever

            st.success("✅ Vector Store erstellt und indexiert")
            logger.info(f"Vector store created with {len(st.session_state.chunks)} chunks")

    # 3. Run full pipeline retrieval with logging — genau HIER, in Stage 3.
    #    Ergebnis wird gecacht; hitl_gate_view verwendet es ohne erneuten Run.
    if st.session_state.get("retrieval_result") is None:
        with st.spinner("📝 Retrieval-Log wird geschrieben..."):
            from src.ui.pipeline_context import get_application_pipeline, new_trace_id
            trace_id = new_trace_id("retrieval")
            pipeline = get_application_pipeline()
            documents_stage = pipeline.parse_documents(
                st.session_state.cv_file_path,
                st.session_state.job_file_path,
            )
            retrieval_stage = pipeline.run_retrieval(
                documents_stage.data["result"],
                trace_id=trace_id,
            )
            st.session_state.retrieval_result = retrieval_stage.data["retrieval_result"]
            st.session_state.retrieval_trace_id = trace_id
            logger.info(f"Retrieval logged at Stage 3 — trace_id={trace_id}")


def _show_statistics_dashboard() -> None:
    """
    Zeige Statistik-Dashboard (Metrics).
    
    Uses Session State:
    - chunks (Stage 2)
    - requirements (Stage 3)
    - job_model (Stage 1)
    """
    st.subheader("📊 Pipeline Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "CV Chunks",
            len(st.session_state.chunks),
            help="Anzahl segmentierter CV-Bereiche"
        )
    
    with col2:
        st.metric(
            "Total Requirements",
            len(st.session_state.requirements),
            help="Extrahierte Job Requirements"
        )
    
    with col3:
        # Count critical requirements
        critical_count = sum(
            1 for req in st.session_state.requirements 
            if req.priority == "critical"
        )
        st.metric(
            "Critical Requirements",
            critical_count,
            help="Requirements mit höchster Priorität"
        )
    
    with col4:
        st.metric(
            "Job Title",
            st.session_state.job_model.job_title,
            help="Position aus JobAd"
        )


def _show_parameter_sliders() -> Tuple[int, float]:
    """
    Zeige interaktive Parameter-Slider für Retrieval.
    
    Returns:
        Tuple[int, float]: (top_k, threshold)
    
    Notes:
        Slider-Änderungen triggern automatisch Streamlit Rerun
        → Auto Re-Retrieval ohne expliziten Button
    """
    st.subheader("🔧 Retrieval-Parameter konfigurieren")
    
    col1, col2 = st.columns(2)
    
    with col1:
        top_k = st.slider(
            "Top-K Chunks", 
            min_value=1, 
            max_value=20, 
            value=5,
            help="Anzahl der relevantesten Chunks pro Requirement"
        )
    
    with col2:
        threshold = st.slider(
            "Score Threshold", 
            min_value=0.0, 
            max_value=1.0, 
            value=0.3,
            step=0.05,
            help="Minimaler Similarity Score (0.0 - 1.0)"
        )
    
    return top_k, threshold


def _show_requirement_selector_and_results(top_k: int, threshold: float) -> None:
    """
    Zeige Requirement Selector und Retrieval Results.
    
    Args:
        top_k: Anzahl Top-K Chunks
        threshold: Similarity Score Threshold
    """
    st.subheader("🎯 Requirement Matching")
    
    requirements = st.session_state.requirements
    
    if not requirements:
        st.warning("⚠️ Keine Requirements gefunden!")
        return
    
    # Build Requirement Options (mit Priority Icons)
    priority_icons = {
        "critical": "🔴",
        "important": "🟡",
        "nice_to_have": "🟢"
    }
    
    category_icons = {
        "hard_skill": "💻",
        "soft_skill": "🤝",
        "experience": "📅",
        "education": "🎓"
    }
    
    req_options = [
        f"{priority_icons.get(req.priority, '⚪')} {category_icons.get(req.category, '📌')} {req.text[:60]}..."
        if len(req.text) > 60 else
        f"{priority_icons.get(req.priority, '⚪')} {category_icons.get(req.category, '📌')} {req.text}"
        for req in requirements
    ]
    
    # Selectbox mit Custom Format
    selected_idx = st.selectbox(
        "Requirement",
        range(len(requirements)),
        format_func=lambda i: req_options[i],
        label_visibility="collapsed"
    )
    
    selected_req = requirements[selected_idx]
    
    # Display Requirement Details
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.info(f"**Requirement ID:** `{selected_req.requirement_id}`")
    
    with col2:
        priority_colors = {
            "critical": "red",
            "important": "orange",
            "nice_to_have": "green"
        }
        priority_color = priority_colors.get(selected_req.priority, "gray")
        st.markdown(f"**Priority:** :{priority_color}[{selected_req.priority.upper()}]")
    
    with col3:
        st.markdown(f"**Category:** `{selected_req.category}`")
    
    st.divider()
    
    # Perform Retrieval (with current slider values)
    with st.spinner("🔍 Suche passende CV-Abschnitte..."):
        retrieval_result = _perform_retrieval(selected_req, top_k, threshold)
    
    # Display Results
    _show_retrieval_results(selected_req, retrieval_result, threshold)


def _perform_retrieval(requirement: Requirement, top_k: int, threshold: float):
    """
    Führe Retrieval durch mit aktuellen Parametern.
    
    Args:
        requirement: Zu suchendes Requirement
        top_k: Anzahl Top-K Results
        threshold: Score Threshold
    
    Returns:
        RetrievalResult mit gefundenen Chunks
    """
    # Initialize Retriever with current parameters
    retriever = VectorRetriever(
        embedder=st.session_state.embedder,
        vector_store=st.session_state.vector_store,
        top_k=top_k,
        threshold=threshold,
        enable_reranking=True,
        enable_logging=False  # Disable für UI Performance
    )
    
    # Perform retrieval
    retrieval_result = retriever.retrieve(requirement)
    
    return retrieval_result


def _show_retrieval_results(requirement, retrieval_result, threshold: float) -> None:
    """
    Zeige Retrieval Results für ein Requirement.
    
    Args:
        requirement: Das gesuchte Requirement
        retrieval_result: RetrievalResult mit gefundenen Chunks
        threshold: Verwendeter Threshold (für Display)
    """
    st.subheader(f"📋 Top-{retrieval_result.chunk_count} Matching CV Sections")
    
    # Results Summary Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Chunks Gefunden",
            retrieval_result.chunk_count,
            help=f"Anzahl Chunks über Threshold ({threshold})"
        )
    
    with col2:
        if retrieval_result.chunk_count > 0:
            score_color = (
                "green" if retrieval_result.best_score > 0.8 
                else "orange" if retrieval_result.best_score >= 0.6 
                else "red"
            )
            st.markdown("**Best Match Score**")
            st.markdown(f":{score_color}[**{retrieval_result.best_score:.3f}**]")
        else:
            st.metric("Best Match Score", "N/A")
    
    with col3:
        if retrieval_result.chunk_count > 0:
            st.metric(
                "Durchschnitt Score",
                f"{retrieval_result.average_score:.3f}",
                help="Durchschnittlicher Match Score"
            )
        else:
            st.metric("Durchschnitt Score", "N/A")
    
    # Warning: Insufficient Evidence
    if not retrieval_result.has_sufficient_evidence:
        st.warning(
            f"⚠️ **Insufficient Evidence:** Nur {retrieval_result.chunk_count} Chunks gefunden "
            f"(Empfohlen: ≥ 2 für robustes Matching)"
        )
    
    # No Results Case
    if retrieval_result.chunk_count == 0:
        st.error(
            f"❌ **Keine passenden CV-Abschnitte gefunden!**\n\n"
            f"Das Requirement '{requirement.text}' konnte nicht mit dem CV gematcht werden. "
            f"Mögliche Gründe:\n"
            f"- Skill nicht im CV vorhanden\n"
            f"- Semantische Ähnlichkeit zu gering (< {threshold})\n"
            f"- Unterschiedliche Terminologie\n\n"
            f"**Tipp:** Threshold senken oder andere Requirement wählen."
        )
        return
    
    st.divider()
    
    # Score Visualization (Bar Chart)
    st.markdown("**🌡️ Match Score Verteilung**")
    _show_score_visualization(retrieval_result)
    
    st.divider()
    
    # Chunk Details (Expandable Cards)
    st.markdown("**📄 Chunk Details**")
    _show_chunk_details(retrieval_result)


def _show_score_visualization(retrieval_result) -> None:
    """
    Zeige Score Visualization als Bar Chart.
    
    Args:
        retrieval_result: RetrievalResult mit Chunks und Scores
    """
    # Prepare DataFrame
    chunks_data = []
    for idx, (chunk, score) in enumerate(retrieval_result.retrieved_chunks):
        chunks_data.append({
            "Rank": idx + 1,
            "Chunk ID": chunk.chunk_id,
            "Score": score
        })
    
    df = pd.DataFrame(chunks_data)
    
    # Bar Chart mit Streamlit
    st.bar_chart(df.set_index("Chunk ID")["Score"])
    
    # Threshold Legend
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🟢 **High:** > 0.8")
    with col2:
        st.markdown("🟡 **Medium:** 0.6 - 0.8")
    with col3:
        st.markdown("🔴 **Low:** < 0.6")


def _show_chunk_details(retrieval_result) -> None:
    """
    Zeige Chunk Details als Expandable Cards.
    
    Args:
        retrieval_result: RetrievalResult mit Chunks und Scores
    
    Notes:
        - Fixed Nested Expander Warning durch Removal von Metadata Sub-Expander
        - Metadata jetzt als st.code() statt st.json() in Sub-Expander
    """
    for idx, (chunk, score) in enumerate(retrieval_result.retrieved_chunks):
        # Score Color Coding
        if score > 0.8:
            score_icon = "🟢"
            score_color = "green"
        elif score >= 0.6:
            score_icon = "🟡"
            score_color = "orange"
        else:
            score_icon = "🔴"
            score_color = "red"
        
        # Expandable Card
        with st.expander(
            f"**Rank {idx + 1}:** {score_icon} {chunk.chunk_id} — "
            f":{score_color}[Score: {score:.3f}]",
            expanded=False
        ):
            # Chunk Text
            st.markdown("**📝 Chunk Text:**")
            st.text_area(
                "Text",
                chunk.text,
                height=150,
                disabled=True,
                label_visibility="collapsed",
                key=f"chunk_text_{idx}_{chunk.chunk_id}"
            )
            
            # Metadata
            st.markdown("**📊 Metadata:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Section Type:** `{chunk.section_type}`")
                st.markdown(f"**Char Range:** `{chunk.char_start} - {chunk.char_end}`")
                st.markdown(f"**Length:** `{len(chunk.text)} chars`")
            
            with col2:
                # Recency Score (if available)
                recency_score = chunk.metadata.get("recency_score", "N/A")
                if recency_score != "N/A":
                    st.markdown(f"**Recency Score:** `{recency_score:.2f}`")
                
                # Timestamps (if available)
                if "start_year" in chunk.metadata:
                    start_year = chunk.metadata["start_year"]
                    end_year = chunk.metadata.get("end_year", "Present")
                    st.markdown(f"**Period:** `{start_year} - {end_year}`")
            
            # Full Metadata (no nested expander - fixed warning)
            st.markdown("**🔍 Full Metadata:**")
            st.code(str(chunk.metadata), language="python")
