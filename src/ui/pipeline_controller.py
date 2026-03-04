"""
Pipeline Controller — Stage-based View Orchestration

Manages progressive view rendering based on pipeline stage.
Implements sequential flow control for M2 RAG Pipeline.

Architecture:
- Stage 0: App Start (only header visible)
- Stage 1: Document Loading View
- Stage 2: Chunking Analysis View
- Stage 3: Retrieval & Skill Matching View
- Stage 4: HITL Gate (Chunk Review & Confirmation)
- Stage 5: LLM Processing (Loading State)
- Stage 6: Output Rendering (Final Documents)

Design Pattern: Progressive Disclosure
- Views are added incrementally (additive visibility)
- Previous views remain visible for inspection
- User can scroll up to review earlier stages

Milestone: M2
Version: 2.0 (Pipeline Flow Redesign)
"""

import streamlit as st
from typing import Optional


class PipelineController:
    """Orchestrates progressive view rendering based on pipeline stage."""
    
    def render(self, stage: int, cv_file: str, job_file: str) -> None:
        """
        Render views based on current pipeline stage.
        
        Args:
            stage: Current pipeline stage (0-6)
            cv_file: Path to CV markdown file
            job_file: Path to Job Ad markdown file
            
        Pipeline Stages:
            0: Initial state (header only)
            1+: Document Loading View
            2+: Chunking Analysis View
            3+: Retrieval & Skill Matching View
            4: HITL Gate (Chunk Review)
            5: LLM Processing (Loading State)
            6+: Output Rendering View
        """
        # Always show header
        st.title("🔍 CV Governance Agent — RAG Pipeline Controller")
        st.caption("Milestone 2: RAG Layer + HITL Gate")
        st.divider()
        
        # Stage 1+: Document Loading View
        if stage >= 1:
            self._scroll_anchor("documents-view")
            self._render_document_view(cv_file, job_file)
            self._auto_scroll_to("documents-view")
            st.divider()
        
        # Stage 2+: Chunking View
        if stage >= 2:
            self._scroll_anchor("chunking-view")
            self._render_chunking_view(cv_file)
            self._auto_scroll_to("chunking-view")
            st.divider()
        
        # Stage 3+: Retrieval View
        if stage >= 3:
            self._scroll_anchor("retrieval-view")
            self._render_retrieval_view(cv_file, job_file)
            self._auto_scroll_to("retrieval-view")
            st.divider()
        
        # Stage 4: HITL Gate
        if stage == 4:
            self._scroll_anchor("hitl-view")
            self._render_hitl_gate()
            self._auto_scroll_to("hitl-view")
            st.divider()
        
        # Stage 5: Loading State (handled in HITL Gate)
        # (No separate view - loading animation in HITL submit)
        
        # Stage 6+: Output Rendering
        if stage >= 6:
            self._scroll_anchor("output-view")
            self._render_output_view()
            self._auto_scroll_to("output-view")

    def _scroll_anchor(self, anchor_id: str) -> None:
        """Insert an HTML anchor to allow scrolling."""
        st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)

    def _auto_scroll_to(self, anchor_id: str) -> None:
        """Scroll to anchor if it matches the current scroll target."""
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
    
    def _render_document_view(self, cv_file: str, job_file: str) -> None:
        """Render document loading view (Stage 1+)."""
        try:
            from ui.document_view import show_document_view
            show_document_view(cv_file, job_file)
        except ImportError:
            st.warning("⚠️ Document View not yet implemented (Task 2.1b)")
            st.info(f"**CV File:** {cv_file}\n\n**Job File:** {job_file}")
        except Exception as e:
            st.error(f"❌ Error loading Document View: {str(e)}")
            st.exception(e)
    
    def _render_chunking_view(self, cv_file: str) -> None:
        """Render chunking analysis view (Stage 2+)."""
        try:
            from ui.chunking_view import show_chunking_view
            show_chunking_view(cv_file)
        except ImportError:
            st.warning("⚠️ Chunking View not yet implemented (Task 2.1c)")
        except Exception as e:
            st.error(f"❌ Error loading Chunking View: {str(e)}")
            st.exception(e)
    
    def _render_retrieval_view(self, cv_file: str, job_file: str) -> None:
        """Render retrieval & skill matching view (Stage 3+)."""
        try:
            from ui.retrieval_view import show_retrieval_view
            show_retrieval_view(cv_file, job_file)
        except ImportError:
            st.warning("⚠️ Retrieval View not yet implemented (Task 2.5a)")
        except Exception as e:
            st.error(f"❌ Error loading Retrieval View: {str(e)}")
            st.exception(e)
    
    def _render_hitl_gate(self) -> None:
        """Render HITL Gate view (Stage 4)."""
        try:
            from ui.hitl_gate_view import show_hitl_gate
            show_hitl_gate()
        except ImportError as e:
            st.error(f"❌ HITL Gate Import Error: {str(e)}")
            st.warning("⚠️ HITL Gate View kann nicht geladen werden")
            st.info("**HITL Gate:** User reviews chunks before LLM submission")
            import traceback
            st.code(traceback.format_exc())
        except Exception as e:
            st.error(f"❌ Error in HITL Gate: {str(e)}")
            st.exception(e)
    
    def _render_output_view(self) -> None:
        """Render output rendering view (Stage 6+)."""
        try:
            from ui.output_view import show_output_view
            show_output_view()
        except ImportError:
            st.warning("⚠️ Output View not yet implemented (Task 2.7b)")
            st.info("**Output:** Generated Cover Letter & Relevant CV")
        except Exception as e:
            st.error(f"❌ Error loading Output View: {str(e)}")
            st.exception(e)
