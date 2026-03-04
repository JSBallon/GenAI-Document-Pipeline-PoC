"""
UI Module — Streamlit-based Inspection Views

Provides visualization and debugging tools for the RAG pipeline.
Used for development, testing, and demo purposes.

Views:
- chunking_view: CV Chunking Analysis
- retrieval_view: Skill Matching & Retrieval Results
- evidence_view: Evidence Linking & Source Attribution
- confidence_view: Confidence Scoring Dashboard

Usage:
    streamlit run src/streamlit_app.py
"""

__version__ = "0.1.0"
__all__ = [
    "chunking_view",
    "retrieval_view", 
    "evidence_view",
    "confidence_view"
]
