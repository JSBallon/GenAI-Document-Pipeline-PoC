"""
Chunking View — CV Segmentation Analysis

Visualizes the Hybrid Chunking Strategy results:
- Section Overview (Table with all chunks)
- Chunk Details (Expandable cards with metadata)
- Chunk Size Distribution (Histogram)
- Hybrid Strategy Indicators (Section-based vs. Paragraph-split)

Status: IMPLEMENTED (Task 2.1a)
Dependencies: HybridChunker, CVParser, Chunk Model

Usage:
    Called from streamlit_app.py when "Chunking" view is selected
"""

import streamlit as st
import pandas as pd
from typing import List

from src.rag.chunker import HybridChunker
from src.parsers.cv_parser import CVParser
from src.rag.models import Chunk


def show_chunking_view(cv_path: str):
    """
    Display CV Chunking Analysis.
    
    Main entry point for Chunking View. Loads CV, performs chunking,
    and displays comprehensive visualization of the results.
    
    Args:
        cv_path: Path to CV markdown file
        
    Displays:
        - Summary metrics (Total chunks, avg size, section-based ratio)
        - Section overview table
        - Chunk size distribution histogram
        - Expandable chunk details with metadata
    """
    st.header("🔪 CV Chunking Analysis")
    
    # Governance Information
    st.info("""
    **Was passiert hier?**  
    Der CV wird in semantische Chunks segmentiert. Die Hybrid-Chunking-Strategie teilt 
    Dokumente nach Sektionen auf und splittet bei Bedarf zu große Abschnitte in kleinere Teile.
    
    **🛡️ Governance Controls:**
    - **PII-Isolation:** Persönliche Daten (Name, Kontakt) bleiben im Frontmatter und werden nicht in Chunks eingebettet
    - **Strukturierte Segmentierung:** Chunks enthalten nur Fachtext, keine sensiblen Rohdaten
    - **Reproduzierbarkeit:** Jeder Chunk erhält eine eindeutige ID und Metadaten zur Nachverfolgung
    """)
    
    # Load CV and perform chunking
    try:
        chunks = _load_and_chunk_cv(cv_path)
    except Exception as e:
        st.error(f"❌ **Fehler beim Chunking:** {str(e)}")
        st.exception(e)
        return
    
    if not chunks:
        st.warning("⚠️ Keine Chunks generiert. CV möglicherweise leer oder ungültig.")
        return
    
    # Display visualizations
    _display_summary_metrics(chunks)
    _display_section_overview(chunks)
    _display_size_distribution(chunks)
    _display_chunk_details(chunks)


# ============================================================
# CORE LOGIC: Load & Chunk
# ============================================================

def _load_and_chunk_cv(cv_path: str) -> List[Chunk]:
    """
    Load CV and perform hybrid chunking.
    
    Uses session state to avoid redundant parsing and chunking:
    - Reuses cv_model from Stage 1 (already parsed)
    - Generates chunks only once at Stage 2 entry
    - Stores chunks in session state for later stages (Retrieval, HITL Gate)
    
    Args:
        cv_path: Path to CV markdown file
    
    Returns:
        List[Chunk]: Generated chunks with metadata
    
    Raises:
        Exception: If CV model missing or chunking fails
    """
    # Check if chunks already exist in session state (avoid re-chunking)
    if st.session_state.chunks is not None:
        return st.session_state.chunks
    
    # Reuse parsed CV model from Stage 1 (avoid re-parsing)
    cv_model = st.session_state.cv_model
    if cv_model is None:
        raise Exception("CV Model nicht in Session State gefunden. Bitte Stage 1 (Einlesen) zuerst ausführen.")
    
    # Initialize chunker with hybrid strategy parameters
    chunker = HybridChunker(
        min_chunk_size=100,
        max_chunk_size=1000,
        overlap_size=50
    )
    
    # Generate chunks
    with st.spinner("🔪 Chunking läuft..."):
        chunks = chunker.chunk_cv(cv_model)
    
    # Store in session state for later pipeline stages
    st.session_state.chunks = chunks
    st.success(f"✅ {len(chunks)} Chunks erfolgreich generiert und gespeichert")
    
    return chunks


# ============================================================
# VISUALIZATION COMPONENTS
# ============================================================

def _display_summary_metrics(chunks: List[Chunk]):
    """
    Display summary metrics in 3 columns.
    
    Metrics:
    - Total Chunks
    - Average Chunk Size
    - Section-Based Ratio (vs. Paragraph-split)
    
    Args:
        chunks: List of generated chunks
    """
    st.subheader("📊 Summary Metrics")
    
    col1, col2, col3 = st.columns(3)
    
    # Metric 1: Total Chunks
    with col1:
        st.metric("Total Chunks", len(chunks))
    
    # Metric 2: Average Chunk Size
    with col2:
        avg_size = sum(len(c.text) for c in chunks) / len(chunks)
        st.metric("Avg Chunk Size", f"{avg_size:.0f} chars")
    
    # Metric 3: Section-Based Ratio
    with col3:
        section_based_count = sum(
            1 for c in chunks 
            if _detect_strategy(c.chunk_id) == "section"
        )
        ratio_text = f"{section_based_count}/{len(chunks)}"
        st.metric("Section-Based", ratio_text)


def _display_section_overview(chunks: List[Chunk]):
    """
    Display section overview table with all chunks.
    
    Table columns:
    - Chunk ID
    - Section Type
    - Size (chars)
    - Strategy (section | paragraph)
    
    Args:
        chunks: List of generated chunks
    """
    st.subheader("📋 Section Overview")
    
    # Build DataFrame
    df = pd.DataFrame({
        "Chunk ID": [c.chunk_id for c in chunks],
        "Section Type": [c.section_type for c in chunks],
        "Size (chars)": [len(c.text) for c in chunks],
        "Strategy": [_detect_strategy(c.chunk_id) for c in chunks]
    })
    
    # Display table
    st.dataframe(df, use_container_width=True, height=300)
    
    # Additional info
    st.caption(
        f"**Total:** {len(chunks)} chunks | "
        f"**Section-based:** {sum(df['Strategy'] == 'section')} | "
        f"**Paragraph-split:** {sum(df['Strategy'] == 'paragraph')}"
    )


def _display_size_distribution(chunks: List[Chunk]):
    """
    Display chunk size distribution as bar chart.
    
    Shows character count for each chunk with threshold markers.
    
    Args:
        chunks: List of generated chunks
    """
    st.subheader("📈 Chunk Size Distribution")
    
    # Build DataFrame for chart
    df = pd.DataFrame({
        "Chunk ID": [c.chunk_id for c in chunks],
        "Size (chars)": [len(c.text) for c in chunks]
    })
    
    # Display bar chart
    st.bar_chart(df.set_index("Chunk ID")["Size (chars)"])
    
    # Display threshold markers
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption("🟢 **Min Threshold:** 100 chars")
    with col2:
        st.caption("🔴 **Max Threshold:** 1000 chars")
    with col3:
        min_size = min(len(c.text) for c in chunks)
        max_size = max(len(c.text) for c in chunks)
        st.caption(f"**Range:** {min_size} - {max_size} chars")


def _display_chunk_details(chunks: List[Chunk]):
    """
    Display expandable chunk details with full text and metadata.
    
    For each chunk:
    - Strategy icon (📘 section-based | 📙 paragraph-split)
    - Text preview (first 200 chars) in expandable section
    - Full metadata in JSON format
    
    Args:
        chunks: List of generated chunks
    """
    st.subheader("📄 Chunk Details")
    
    for chunk in chunks:
        # Detect strategy and select icon
        strategy = _detect_strategy(chunk.chunk_id)
        strategy_icon = "📘" if strategy == "section" else "📙"
        strategy_label = "Section-based" if strategy == "section" else "Paragraph-split"
        
        # Display title
        title = (
            f"{strategy_icon} {chunk.chunk_id} — {chunk.section_type} "
            f"({strategy_label})"
        )
        
        with st.expander(title, expanded=False):
            # Text Preview
            st.markdown("**Text Preview:**")
            preview = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            st.text_area(
                label="Text Preview",
                value=preview,
                height=150,
                disabled=True,
                label_visibility="collapsed",
                key=f"preview_{chunk.chunk_id}"
            )
            
            # Show full text button (optional)
            if len(chunk.text) > 200:
                if st.button("Show Full Text", key=f"full_{chunk.chunk_id}"):
                    st.text_area(
                        label="Full Text",
                        value=chunk.text,
                        height=300,
                        disabled=True,
                        label_visibility="visible",
                        key=f"fulltext_{chunk.chunk_id}"
                    )
            
            # Metadata
            st.markdown("**Metadata:**")
            metadata_display = {
                "chunk_id": chunk.chunk_id,
                "section_type": chunk.section_type,
                "section_title": chunk.section_title or "N/A",
                "char_range": f"{chunk.char_start} - {chunk.char_end}",
                "length": len(chunk.text),
                "strategy": strategy,
                **chunk.metadata  # Include additional metadata
            }
            st.json(metadata_display)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _detect_strategy(chunk_id: str) -> str:
    """
    Detect chunking strategy from chunk_id format.
    
    Logic:
    - chunk_id without sub-index → "section"
      Example: cv_experience_0
    - chunk_id with sub-index → "paragraph"
      Example: cv_experience_0_1
    
    Args:
        chunk_id: Chunk identifier (format: cv_<type>_<idx>(_<sub>)?)
    
    Returns:
        str: "section" or "paragraph"
    
    Example:
        >>> _detect_strategy("cv_experience_0")
        "section"
        >>> _detect_strategy("cv_experience_0_1")
        "paragraph"
    """
    parts = chunk_id.split('_')
    
    # If more than 3 parts, it has a sub-index (paragraph-split)
    # Format: cv_<section>_<index>_<sub> = 4 parts
    # Format: cv_<section>_<index> = 3 parts
    return "paragraph" if len(parts) > 3 else "section"
