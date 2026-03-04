"""
Document Loading View — Side-by-Side Display of CV and Job Ad

Displays loaded input documents after parsing (Pipeline Stage 1).
Implements progressive disclosure pattern with meta-info and raw content.

Architecture:
- Parses CV and JobAd via respective parsers
- Stores parsed models in Session State
- Displays documents side-by-side with metadata
- Shows raw file content for transparency

Milestone: M2
Task: 2.1b
Version: 1.0
"""

import streamlit as st
from pathlib import Path
from typing import Tuple

from parsers.cv_parser import CVParser, CVParsingError
from parsers.job_parser import JobAdParser, JobAdParsingError
from models.cv import CVModel
from models.job_ad import JobAdModel


class DocumentViewError(Exception):
    """Custom exception for document view errors."""
    pass


def show_document_view(cv_path: str, job_path: str) -> None:
    """
    Display loaded CV and Job Ad side-by-side.
    
    Parses documents (if not already in session state) and displays them
    in a two-column layout with metadata and raw content.
    
    Args:
        cv_path: Path to CV markdown file (relative or absolute)
        job_path: Path to Job Ad markdown file (relative or absolute)
        
    Raises:
        DocumentViewError: If document loading or parsing fails
    """
    st.header("📄 Geladene Dokumente")
    
    # Governance Information
    st.info("""
    **Was passiert hier?**  
    CV und JobAd werden eingelesen und strukturiert geparst. Die Dokumente werden gegen 
    ihre Schemas validiert, um sicherzustellen, dass nur valide Daten in die Pipeline gelangen.
    
    **🛡️ Governance Controls:**
    - **Input-Validierung:** Nur strukturierte, schema-konforme Daten werden verarbeitet
    - **Schema-Check:** Pydantic-basierte Validierung stellt Datenintegrität sicher
    """)
    
    try:
        # Parse documents (only once - stored in session state)
        cv_model, job_model = _parse_documents_if_needed(cv_path, job_path)
        
        # Side-by-Side Display
        col1, col2 = st.columns(2)
        
        with col1:
            _display_cv(cv_model, cv_path)
        
        with col2:
            _display_job_ad(job_model, job_path)
        
        # Success Message
        st.success("✅ Dokumente erfolgreich eingelesen und geparst")
        
    except (CVParsingError, JobAdParsingError) as e:
        st.error(f"❌ Parsing-Fehler: {str(e)}")
        st.stop()
    except FileNotFoundError as e:
        st.error(f"❌ Datei nicht gefunden: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unerwarteter Fehler beim Laden der Dokumente: {str(e)}")
        st.exception(e)
        st.stop()


def _parse_documents_if_needed(cv_path: str, job_path: str) -> Tuple[CVModel, JobAdModel]:
    """
    Parse documents if not already in session state.
    
    This ensures parsing only happens once per session, improving performance
    and maintaining state consistency across pipeline stages.
    
    Args:
        cv_path: Path to CV file
        job_path: Path to Job Ad file
        
    Returns:
        Tuple of (CVModel, JobAdModel)
        
    Raises:
        CVParsingError: If CV parsing fails
        JobAdParsingError: If Job Ad parsing fails
    """
    # Parse CV if not in session state
    if st.session_state.cv_model is None:
        with st.spinner("📄 Parsing CV..."):
            cv_parser = CVParser()
            st.session_state.cv_model = cv_parser.parse_file(cv_path)
    
    # Parse Job Ad if not in session state
    if st.session_state.job_model is None:
        with st.spinner("📢 Parsing Job Advertisement..."):
            job_parser = JobAdParser()
            st.session_state.job_model = job_parser.parse_file(job_path)
    
    return st.session_state.cv_model, st.session_state.job_model


def _display_cv(cv_model: CVModel, cv_path: str) -> None:
    """
    Display CV in left column.
    
    Shows metadata (name, sections count) and raw file content.
    
    Args:
        cv_model: Parsed CV model
        cv_path: Path to CV file
    """
    st.subheader("📋 Lebenslauf")
    
    # Meta Information
    st.info(f"**Name:** {cv_model.name}")
    
    # Count available sections
    section_count = sum([
        len(cv_model.berufserfahrung) > 0,
        len(cv_model.skills) > 0,
        len(cv_model.bildung) > 0,
        len(cv_model.projekte) > 0,
        len(cv_model.sprachen) > 0,
        cv_model.interessen is not None
    ])
    st.info(f"**Sections:** {section_count}")
    
    # Raw file content for transparency
    raw_content = _read_raw_file(cv_path)
    st.text_area(
        "CV Inhalt",
        raw_content,
        height=500,
        disabled=True,
        label_visibility="collapsed",
        key="cv_raw_content"
    )


def _display_job_ad(job_model: JobAdModel, job_path: str) -> None:
    """
    Display Job Advertisement in right column.
    
    Shows metadata (position, company) and raw file content.
    
    Args:
        job_model: Parsed Job Ad model
        job_path: Path to Job Ad file
    """
    st.subheader("📢 Stellenausschreibung")
    
    # Meta Information
    st.info(f"**Position:** {job_model.job_title}")
    st.info(f"**Firma:** {job_model.company}")
    
    # Optional: Location if available
    if job_model.location:
        st.info(f"**Standort:** {job_model.location}")
    
    # Raw file content for transparency
    raw_content = _read_raw_file(job_path)
    st.text_area(
        "JobAd Inhalt",
        raw_content,
        height=500,
        disabled=True,
        label_visibility="collapsed",
        key="job_raw_content"
    )


def _read_raw_file(file_path: str) -> str:
    """
    Read raw file content from disk.
    
    Reads the complete markdown file including frontmatter and content.
    
    Args:
        file_path: Path to file
        
    Returns:
        Raw file content as string
        
    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Datei existiert nicht: {file_path}")
    
    try:
        return path.read_text(encoding='utf-8')
    except Exception as e:
        raise IOError(f"Fehler beim Lesen der Datei {file_path}: {str(e)}")
