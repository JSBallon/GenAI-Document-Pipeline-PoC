"""
Streamlit Entry Point — CV Governance Agent RAG Pipeline Controller

V2.0 Architecture: Sequential Pipeline Flow with HITL Gate

Design Pattern: Pipeline Flow Controller (not Inspection Tool)
- Sequential button-based processing control
- Progressive view expansion in main window
- Button state management (clickable → non-clickable after execution)
- HITL Gate before LLM submission (chunk review & confirmation)
- Active pipeline controller with user-in-the-loop integration

Pipeline Stages:
    0: App Start (only header visible)
    1: Document Loading (Parse CV & JobAd)
    2: Preprocessing (Chunking)
    3: Comparison (Requirements Extraction + Retrieval)
    4: Document Generation (HITL Gate: Chunk Review)
    5: LLM Submission (Loading State)
    6: Output Rendering (Final Documents)

Usage:
    streamlit run src/streamlit_app.py
    # or use: run_streamlit.cmd

Milestone: M2 (RAG / Mapping Layer)
Version: 2.0 (Pipeline Flow Redesign)
"""

import streamlit as st
from pathlib import Path
from typing import Optional, Tuple

from config.env_loader import load_project_env
from ui.document_view import show_document_view
from ui.chunking_view import show_chunking_view
from ui.retrieval_view import show_retrieval_view
from ui.hitl_gate_view import show_hitl_gate
from ui.output_view import show_output_view

# Load .env from project root (ensures OPENROUTER_API_KEY available in Streamlit)
load_project_env()

# Page Configuration
st.set_page_config(
    page_title="CV Pipeline Controller",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def _open_file_dialog(
    title: str,
    initial_dir: Path,
    file_types: Tuple[Tuple[str, str], ...]
) -> Optional[str]:
    """Open a native file dialog and return the selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        st.error(f"❌ Datei-Dialog kann nicht geöffnet werden: {exc}")
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        file_path = filedialog.askopenfilename(
            title=title,
            initialdir=str(initial_dir),
            filetypes=list(file_types)
        )
    finally:
        root.destroy()

    return file_path or None


def initialize_session_state() -> None:
    """Initialize all session state variables for pipeline tracking."""
    
    # Pipeline Stage Tracking (0-6)
    if 'pipeline_stage' not in st.session_state:
        st.session_state.pipeline_stage = 0

    if 'prev_pipeline_stage' not in st.session_state:
        st.session_state.prev_pipeline_stage = st.session_state.pipeline_stage

    if 'scroll_target' not in st.session_state:
        st.session_state.scroll_target = None

    if 'cv_file_path' not in st.session_state:
        st.session_state.cv_file_path = "samples/sample_cv_001.md"

    if 'job_file_path' not in st.session_state:
        st.session_state.job_file_path = "samples/sample_job_ad_001.md"
    
    # Parsed Document Models
    if 'cv_model' not in st.session_state:
        st.session_state.cv_model = None
    
    if 'job_model' not in st.session_state:
        st.session_state.job_model = None
    
    # RAG Components
    if 'chunks' not in st.session_state:
        st.session_state.chunks = None
    
    if 'requirements' not in st.session_state:
        st.session_state.requirements = None
    
    if 'vector_store' not in st.session_state:
        st.session_state.vector_store = None
    
    if 'retrieval_results' not in st.session_state:
        st.session_state.retrieval_results = None
    
    # Prompt & LLM Components
    if 'prompts' not in st.session_state:
        st.session_state.prompts = None
    
    if 'llm_outputs' not in st.session_state:
        st.session_state.llm_outputs = None

# Initialize session state
initialize_session_state()

# ============================================================================
# SIDEBAR: INPUT FILES & PIPELINE CONTROLS
# ============================================================================

with st.sidebar:
    # --- Input Files Section ---
    st.header("📁 Input Files")

    samples_dir = Path("samples").resolve()
    file_types = (("Markdown", "*.md"), ("All Files", "*.*"))
    
    # CV File Selection
    if st.button(
        "CV Datei auswählen",
        use_container_width=True,
        key="btn_select_cv"
    ):
        selected_path = _open_file_dialog(
            title="CV Datei auswählen",
            initial_dir=samples_dir,
            file_types=file_types
        )
        if selected_path:
            st.session_state.cv_file_path = selected_path

    st.text_input(
        "CV Datei",
        value=st.session_state.cv_file_path,
        disabled=True
    )

    # Job Ad File Selection
    if st.button(
        "Job Ad Datei auswählen",
        use_container_width=True,
        key="btn_select_job"
    ):
        selected_path = _open_file_dialog(
            title="Job Ad Datei auswählen",
            initial_dir=samples_dir,
            file_types=file_types
        )
        if selected_path:
            st.session_state.job_file_path = selected_path

    st.text_input(
        "Job Ad Datei",
        value=st.session_state.job_file_path,
        disabled=True
    )
    
    # Verify files exist
    cv_path = Path(st.session_state.cv_file_path)
    job_path = Path(st.session_state.job_file_path)
    
    if not cv_path.exists():
        st.error(f"❌ CV file not found: {st.session_state.cv_file_path}")
        st.stop()
    
    if not job_path.exists():
        st.error(f"❌ Job Ad file not found: {st.session_state.job_file_path}")
        st.stop()
    
    st.divider()
    
    # --- Document Generation Options ---
    st.header("📋 Zu generierende Dokumente")
    
    generate_cover_letter = st.checkbox(
        "Anschreiben",
        value=True,
        key="gen_cover",
        help="Generiert ein individuelles Anschreiben basierend auf CV und Stellenausschreibung"
    )
    
    generate_relevant_cv = st.checkbox(
        "Relevanter CV",
        value=False,
        disabled=True,
        key="gen_cv",
        help="Dieses Feature wird in Milestone 3 aktiviert"
    )
    
    st.divider()
    
    # --- Pipeline Steps Section ---
    st.header("🔄 Pipeline-Navigation")
    
    # Current stage for button logic
    current_stage = st.session_state.pipeline_stage
    
    # Button 1: Einlesen (Load Documents)
    if st.button(
        "1️⃣ Einlesen",
        disabled=(current_stage >= 1),
        use_container_width=True,
        key="btn_load",
        help="Parse CV and Job Ad files"
    ):
        st.session_state.pipeline_stage = 1
        st.rerun()
    
    # Button 2: Vorverarbeitung (Preprocessing/Chunking)
    if st.button(
        "2️⃣ Vorverarbeitung",
        disabled=(current_stage != 1),
        use_container_width=True,
        key="btn_preprocess",
        help="Chunk CV into semantic segments"
    ):
        st.session_state.pipeline_stage = 2
        st.rerun()
    
    # Button 3: CV und JobAd vergleichen (Comparison/Retrieval)
    if st.button(
        "3️⃣ CV und JobAd vergleichen",
        disabled=(current_stage != 2),
        use_container_width=True,
        key="btn_compare",
        help="Extract requirements and match skills"
    ):
        st.session_state.pipeline_stage = 3
        st.rerun()
    
    # Button 4: Dokumente erzeugen (Generate Documents/HITL Gate)
    if st.button(
        "4️⃣ Dokumente erzeugen",
        disabled=(current_stage != 3),
        use_container_width=True,
        key="btn_generate",
        help="Review chunks before LLM submission"
    ):
        st.session_state.pipeline_stage = 4
        st.rerun()
    
    # Button 5: Trainingsinterview starten (M3 Feature)
    st.button(
        "5️⃣ Trainingsinterview starten",
        disabled=True,
        use_container_width=True,
        key="btn_interview",
        help="Verfügbar ab Milestone 3"
    )
    
    st.divider()
    
    # --- Pipeline Status Display ---
    st.subheader("📊 Pipeline Status")
    
    # Stage Progress Indicator
    stage_labels = [
        "Start",
        "✅ Eingelesen",
        "✅ Vorverarbeitet",
        "✅ Verglichen",
        "⏳ Review",
        "⏳ Verarbeitung...",
        "✅ Fertig"
    ]
    
    if current_stage < len(stage_labels):
        st.info(f"**Aktueller Status:**\n\n{stage_labels[current_stage]}")
    
    # Stage Details
    with st.expander("ℹ️ Stage Details", expanded=False):
        st.markdown(f"""
        **Current Stage:** {current_stage}/6
        
        **Stage Breakdown:**
        - 0: Initial State
        - 1: Documents Loaded
        - 2: Chunking Complete
        - 3: Retrieval Complete
        - 4: HITL Gate Active
        - 5: LLM Processing
        - 6: Output Ready
        """)
    
    st.divider()
    
    # --- System Info ---
    st.subheader("System Info")
    st.info(f"""
    **Version:** 0.1 (Documenten Pipeline)
    
    **Mode:** Streamlit Demo
    """)

# ============================================================================
# MAIN CONTENT AREA: PROGRESSIVE VIEW RENDERING
# ============================================================================

stage_anchor_map = {
    1: "documents-view",
    2: "chunking-view",
    3: "retrieval-view",
    4: "hitl-view",
    6: "output-view"
}

def _render_stage(stage: int) -> None:
    st.title("AI Governance PoC: GenAI Pipeline")
    st.caption("Kontrollierte generative KI mit integrierten Governance Controls")
    # st.divider()

    # Render prelude info for all stages
    _render_prelude_info()
    st.divider()

    # Stage 0: Welcome Screen (only prelude info, no views)
    if stage == 0:
        return
    
    if stage >= 1:
        _scroll_anchor(stage_anchor_map[1])
        show_document_view(str(cv_path), str(job_path))
        _auto_scroll_to(stage_anchor_map[1])
        st.divider()

    if stage >= 2:
        _scroll_anchor(stage_anchor_map[2])
        show_chunking_view(str(cv_path))
        _auto_scroll_to(stage_anchor_map[2])
        st.divider()

    if stage >= 3:
        _scroll_anchor(stage_anchor_map[3])
        show_retrieval_view(str(cv_path), str(job_path))
        _auto_scroll_to(stage_anchor_map[3])
        st.divider()

    if stage >= 4:
        _scroll_anchor(stage_anchor_map[4])
        show_hitl_gate()
        _auto_scroll_to(stage_anchor_map[4])
        st.divider()

    if stage >= 6:
        _scroll_anchor(stage_anchor_map[6])
        show_output_view()
        _auto_scroll_to(stage_anchor_map[6])


def _render_prelude_info() -> None:
    """Render prelude information (visible in all stages)."""
    st.info("""
    ### 📌 Kernbotschaft
    
    GenAI in Financial Services erfordert mehr als gute Modelle — es braucht eine Pipeline, 
    die Halluzinationen verhindert, Daten schützt und jeden Schritt auditierbar macht.
    
    Eine **produktionsnahe Techdemo** für kontrollierte generative KI im Dokumentenkontext 
    auf Corporate-Governance-Niveau, fokussiert auf **Financial Services**.
    
    **Ziel:** Demonstrieren, dass Governance kein Blocker für GenAI ist, sondern der Enabler, 
    der GenAI in regulierte Industrien bringt.
    
    ---
    
    ### 📖 Bedienungsanleitung — Pipeline-Navigation
    
    Diese Pipeline ist **sequenziell** aufgebaut. Verwenden Sie die Buttons in der Sidebar, 
    um Schritt für Schritt durch den Prozess zu navigieren:
    
    **1️⃣ Einlesen**
    - CV und Stellenausschreibung werden geparst und strukturiert
    - **Governance:** Input-Validierung, Schema-Check
    
    **2️⃣ Vorverarbeitung**
    - CV wird in semantische Chunks segmentiert
    - **Governance:** PII-Isolation (persönliche Daten bleiben geschützt)
    
    **3️⃣ CV und JobAd vergleichen**
    - Requirements werden extrahiert und mit CV-Skills gematcht
    - **Governance:** Lokale Embeddings (keine Cloud-Übertragung), Decision Logging
    
    **4️⃣ Dokumente erzeugen**
    - Human-in-the-Loop Gate: Review aller Daten vor LLM-Submission
    - **Governance:** Datentransparenz, explizite Freigabe erforderlich
    
    **5️⃣ Output**
    - Generiertes Anschreiben mit vollständiger Nachvollziehbarkeit
    - **Governance:** Source Attribution, Prompt Logging
    
    ---
    
    **👉 Starten Sie mit Button "1️⃣ Einlesen" in der Sidebar!**
         
    ---
    
    ### 🛡️ Governance Controls im Überblick
    
    | Stage | Governance Control | Zweck |
    |-------|-------------------|-------|
    | **Einlesen** | Input-Validierung | Nur strukturierte Daten werden verarbeitet |
    | **Vorverarbeitung** | PII-Isolation | Persönliche Daten bleiben geschützt |
    | **Vergleich** | Lokale Embeddings | Keine Datenübertragung an Cloud-APIs |
    | **Vergleich** | Decision Logging | Retrieval-Entscheidungen protokolliert |
    | **Review Gate** | Datentransparenz | Alle LLM-Inputs einsehbar |
    | **Review Gate** | Human Approval | Keine Übermittlung ohne Freigabe |
    | **Output** | Source Attribution | Jede Aussage auf Quelle rückverfolgbar |
    | **Output** | Prompt Logging | Vollständige Audit-Trail |
    
    ---
    
    """)


def _render_welcome_screen() -> None:
    """Render welcome screen for Stage 0 (before pipeline starts)."""
    _render_prelude_info()


def _scroll_anchor(anchor_id: str) -> None:
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)


def _auto_scroll_to(anchor_id: str) -> None:
    if st.session_state.get("scroll_target") == anchor_id:
        st.components.v1.html(
            f"""
            <script>
                const anchor = parent.document.getElementById('{anchor_id}');
                if (anchor) {{
                    anchor.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                }}
            </script>
            """,
            height=0
        )

if st.session_state.pipeline_stage != st.session_state.prev_pipeline_stage:
    st.session_state.scroll_target = stage_anchor_map.get(
        st.session_state.pipeline_stage
    )
else:
    st.session_state.scroll_target = None

st.session_state.prev_pipeline_stage = st.session_state.pipeline_stage

# Render views based on current pipeline stage
_render_stage(st.session_state.pipeline_stage)

# ============================================================================
# FOOTER
# ============================================================================
