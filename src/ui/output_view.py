"""
Output Rendering View für CV Governance Agent.

Minimalistisch: Zeigt ausschließlich die gespeicherte Cover-Letter-Datei
aus dem Output-Verzeichnis der Session. Keine Render-Logik, kein Fallback.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, Any

import streamlit as st


def show_output_view() -> None:
    """Zeigt das gerenderte Anschreiben aus der gespeicherten Datei."""
    st.header("📝 Generiertes Anschreiben")

    _log_date = date.today().strftime("%Y-%m-%d")
    _trace_id = (st.session_state.get("llm_outputs") or {}).get("trace_id", "")
    _trace_label = f" — trace_{_trace_id[:8]}" if _trace_id else ""
    st.caption(
        f"📋 **Audit-Trail**{_trace_label} — "
        f"`./logs/retrieval/{_log_date}.jsonl` | `./logs/prompts/{_log_date}.jsonl`"
    )

    # Governance Information
    st.info("""
    **Was passiert hier?**  
    Das finale Anschreiben wird mit vollständiger Nachvollziehbarkeit angezeigt. Alle Metadaten 
    zur Generierung (Trace-ID, Prompt-Version, Token-Usage) sind verfügbar.
    
    **🛡️ Governance Controls:**
    - **Source Attribution:** Jede Aussage im Anschreiben ist auf Quell-Chunks rückverfolgbar (via Trace-ID)
    - **Prompt Logging:** Prompt-Version und Model-Parameter sind in Metadaten gespeichert
    - **Audit Trail:** Vollständiger Generierungsprozess ist über metadata.json nachvollziehbar
    - **Reproduzierbarkeit:** Trace-ID ermöglicht Korrelation mit Prompt- und Retrieval-Logs
    """)

    outputs: Dict[str, Any] | None = st.session_state.get("llm_outputs")
    if not outputs:
        st.error("❌ Kein Anschreiben generiert. Bitte Pipeline erneut ausführen.")
        return

    cover_letter_path = outputs.get("cover_letter_path")
    if not cover_letter_path or not Path(cover_letter_path).exists():
        st.error("❌ Die gespeicherte Cover Letter Datei fehlt.")
        return

    cover_letter_text = Path(cover_letter_path).read_text(encoding="utf-8")
    trace_id = outputs.get("trace_id", "n/a")
    timestamp = outputs.get("timestamp", "n/a")

    st.caption(f"Trace ID: {trace_id}")
    st.caption(f"Generiert: {timestamp}")
    metadata_path = outputs.get("metadata_path")
    if metadata_path and Path(metadata_path).exists():
        with st.expander("📊 Metadaten anzeigen"):
            metadata_text = Path(metadata_path).read_text(encoding="utf-8")
            try:
                metadata = json.loads(metadata_text)
                st.json(metadata)
            except json.JSONDecodeError:
                st.code(metadata_text)

    _rel_cover_path = cover_letter_path if cover_letter_path.startswith("./") else f"./{cover_letter_path}"
    st.caption(f"📁 **Speicherort:** `{_rel_cover_path}`")
    st.markdown("---")

    st.markdown(cover_letter_text)

    st.markdown("---")
    st.download_button(
        label="📥 Anschreiben herunterladen",
        data=cover_letter_text,
        file_name=f"cover_letter_{trace_id[:8]}.md",
        mime="text/markdown"
    )