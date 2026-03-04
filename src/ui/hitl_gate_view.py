"""Governance HITL Gate view that uses the ApplicationPipeline for generation."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, List

import streamlit as st

from pipeline.prompt_builder import PromptBuilder
from pipeline.prompt_loader import PromptLoader
from rag.embedder import LocalEmbedder
from rag.retriever import VectorRetriever
from rag.vector_store import InMemoryVectorStore
from src.services.generation_service import GenerationResult
from src.pipeline.cover_letter_renderer import (
    CandidateDetails,
    CoverLetterRenderer,
    RecipientDetails
)
from src.ui.pipeline_context import get_application_pipeline, new_trace_id

logger = st.session_state.get("logger")


def show_hitl_gate() -> None:
    st.header("⚠️ Human-in-the-Loop Gate")

    _log_date = date.today().strftime("%Y-%m-%d")
    # hitl_trace_id wird in _ensure_prompts() beim Gate-Öffnen gesetzt —
    # dieselbe ID, unter der Retrieval- und Prompt-Logs bereits geschrieben wurden.
    _trace_id = st.session_state.get("hitl_trace_id") or st.session_state.get("generation_trace_id", "")
    _trace_label = f" — `{_trace_id}`" if _trace_id else ""
    st.caption(
        f"📋 **Audit-Trail**{_trace_label} — "
        f"`./logs/retrieval/{_log_date}.jsonl` | `./logs/prompts/{_log_date}.jsonl`"
    )

    # Governance Information
    st.info("""
    **Was passiert hier?**  
    Dies ist der zentrale Governance-Checkpoint. Alle Daten, die an das LLM übermittelt werden sollen, 
    werden zur Überprüfung angezeigt. Sie haben volle Transparenz und Kontrolle über die Datenübertragung.
    
    **🛡️ Governance Controls:**
    - **Datentransparenz:** Alle an das LLM zu übermittelnden Chunks sind vollständig einsehbar
    - **Human Approval:** Keine Datenübermittlung ohne explizite Freigabe durch Button-Klick
    - **Prompt Logging:** System- und User-Prompts werden mit Version und Trace-ID protokolliert
    - **Deduplizierung:** Identische Chunks werden nur einmal übermittelt (Kostenoptimierung)
    """)
    
    _ensure_prompts()
    _render_review_sections()
    _render_generation_feedback()
    _render_submit_button()


def _ensure_prompts() -> None:
    if st.session_state.get("prompts") is not None:
        return

    prompt_loader = PromptLoader()
    prompt_builder = PromptBuilder()
    templates = prompt_loader.load_all_prompts("0.2.0")
    system_template = templates["system_prompt"]
    cover_letter_template = templates["cover_letter_prompt"]

    retrieval_results = _ensure_retrieval_context()
    retrieved_chunks_text = prompt_builder.format_retrieved_chunks(retrieval_results)

    prompts = prompt_builder.build_cover_letter_prompt(
        cv=st.session_state.cv_model,
        job_ad=st.session_state.job_model,
        system_prompt_template=system_template,
        cover_letter_template=cover_letter_template,
        retrieved_chunks=retrieved_chunks_text,
    )

    st.session_state.prompts = {
        "system": prompts["system"],
        "user": prompts["user"],
        "metadata": cover_letter_template.metadata,
        "prompt_id": cover_letter_template.prompt_id,
        "prompt_version": cover_letter_template.version,
    }

    # Prompts sofort beim Gate-Öffnen loggen — NICHT erst nach Button-Klick.
    # trace_id wird gecacht und von _submit_to_pipeline() wiederverwendet.
    trace_id = new_trace_id("hitl")
    st.session_state.hitl_trace_id = trace_id

    from src.infrastructure.logging_service import LoggingService
    _logging_service = LoggingService()
    _logging_service.log_prompt_sent(
        trace_id=trace_id,
        prompt_id=cover_letter_template.prompt_id,
        prompt_text=prompts["user"],
        model="(pre-send — awaiting HITL approval)",
        metadata={
            "stage": "hitl_gate_review",
            "prompt_version": cover_letter_template.version,
            "system_prompt_preview": prompts["system"][:200],
        },
    )


def _ensure_retrieval_context() -> List[Any]:
    if st.session_state.get("retrieval_results"):
        return st.session_state.retrieval_results

    embedder = LocalEmbedder()
    vector_store = InMemoryVectorStore(embedding_dim=embedder.get_embedding_dimension())
    embeddings = embedder.batch_embed_chunks(st.session_state.chunks)
    chunk_ids = [chunk.chunk_id for chunk in st.session_state.chunks]
    vector_store.add_embeddings(chunk_ids, embeddings, st.session_state.chunks)

    retriever = VectorRetriever(
        embedder=embedder,
        vector_store=vector_store,
        enable_logging=False,
    )
    retrieval_results = retriever.batch_retrieve(st.session_state.requirements)
    st.session_state.retrieval_results = retrieval_results
    return retrieval_results


def _render_review_sections() -> None:
    st.header("⚠️ Datenübermittlung an Rechenzentrum")
    st.warning(
        """
        **⚠️ Alle zu übermittelnden Daten werden sichtbar gemacht.**
        Bitte prüfen Sie die Daten, die an das LLM übertragen werden.
        Geben Sie Daten durch einen Klick auf den Button am Ende der Seite frei.
        """
    )

    _render_chunks_overview()

    st.markdown("---")


def _render_generation_feedback() -> None:
    result: GenerationResult | None = st.session_state.get("generation_result")
    if not result:
        return

    st.subheader("🧾 Aktueller Output")
    status = "✅ abgeschlossen" if result.complete else "⚠️ Token-Limit erreicht"
    st.info(f"Status: {status} (Versuch {result.attempts}/{result.metadata['max_attempts']})")
    st.text_area("Text", value=result.text, height=200, disabled=True)
    if not result.complete:
        if st.button("🔄 Fortsetzen", key="continue_generation"):
            _continue_generation()


def _render_chunks_overview() -> None:
    requirements = st.session_state.get("requirements")
    if not requirements:
        st.warning("Keine Requirements gefunden.")
        return

    st.subheader("📋 Job Requirements")
    for idx, requirement in enumerate(requirements, start=1):
        st.markdown(f"{idx}. {requirement.text}")

    st.markdown("---")

    retrieval_results = st.session_state.get("retrieval_results")
    if not retrieval_results:
        st.warning("Keine Retrieval-Daten verfügbar.")
        return

    st.subheader("📦 Deduplizierte CV-Chunks")
    seen_chunk_ids = set()
    unique_chunks = []
    for retrieval_result in retrieval_results:
        for chunk, _ in retrieval_result.retrieved_chunks:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                unique_chunks.append(chunk)

    if not unique_chunks:
        st.warning("Keine Chunks gefunden.")
        return

    for idx, chunk in enumerate(unique_chunks, start=1):
        st.markdown(f"**Chunk {idx}**")
        st.text_area(
            f"chunk_display_{idx}",
            value=chunk.text,
            height=150,
            disabled=True,
            label_visibility="collapsed"
        )
        st.caption(f"Chunk ID: {chunk.chunk_id}")


def _extract_json_from_markdown(text: str) -> str:
    """Extrahiert JSON aus Markdown-Codeblöcken (```json ... ```)."""
    trimmed = text.strip()
    if not trimmed.startswith("```"):
        return trimmed

    json_lines: list[str] = []
    inside_block = False
    for line in trimmed.splitlines():
        if line.startswith("```"):
            inside_block = not inside_block
            continue
        if inside_block:
            json_lines.append(line)

    return "\n".join(json_lines).strip()


def _render_submit_button() -> None:
    if st.session_state.get("generation_complete"):
        st.success("LLM-Generierung abgeschlossen, bereit für Stage 6.")
        return

    if st.button("✅ Daten abschicken und Anschreiben generieren", type="primary"):
        st.session_state.generation_result = None
        _submit_to_pipeline()


def _submit_to_pipeline() -> None:
    # Gecachte trace_id verwenden — dieselbe ID, unter der die Prompts
    # bereits beim Gate-Öffnen in logs/prompts/ geloggt wurden.
    trace_id = st.session_state.get("hitl_trace_id") or new_trace_id("hitl")
    pipeline = get_application_pipeline()
    retrieval_result = _prepare_pipeline_retrieval(trace_id)
    stage_result = pipeline.generate_cover_letter(
        prompts=st.session_state.prompts,
        retrieval_result=retrieval_result,
        trace_id=trace_id,
        attempt=1,
    )
    _handle_generation_result(stage_result.data["generation_result"])


def _continue_generation() -> None:
    attempt = st.session_state.get("continuation_attempt", 1) + 1
    trace_id = st.session_state.get("generation_trace_id")
    pipeline = get_application_pipeline()
    stage_result = pipeline.continue_generation(
        prompts=st.session_state.prompts,
        retrieval_result=st.session_state.retrieval_result,
        trace_id=trace_id,
        previous_text=st.session_state.generation_result.text,
        attempt=attempt,
    )
    st.session_state.continuation_attempt = attempt
    _handle_generation_result(stage_result.data["generation_result"])


def _handle_generation_result(result: GenerationResult) -> None:
    st.session_state.generation_result = result
    st.session_state.generation_trace_id = result.trace_id
    st.session_state.retrieval_result = st.session_state.get("retrieval_result")
    if not result.complete:
        st.session_state.generation_complete = False
        return

    try:
        json_text = _extract_json_from_markdown(result.text)
        llm_json = json.loads(json_text)
    except json.JSONDecodeError:
        st.error("Die LLM-Antwort war kein gültiges JSON.")
        st.session_state.generation_complete = False
        return

    timestamp_dir = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    renderer = CoverLetterRenderer()
    cv_model = st.session_state.cv_model
    candidate_details = CandidateDetails(
        name=cv_model.name,
        location=cv_model.location,
        phone=cv_model.phone,
        email=cv_model.email
    )
    job_model = st.session_state.job_model
    recipient_details = RecipientDetails(
        company=job_model.company,
        location=job_model.location or "",
    )

    rendered_cover_letter = renderer.render(
        paragraphs=llm_json.get("paragraphs", []),
        candidate_details=candidate_details,
        summary=llm_json.get("summary"),
        recipient_details=recipient_details,
        job_title=job_model.job_title,
        letter_date=date.today()
    )

    output_dir = Path("outputs") / f"{timestamp_dir}_trace_{result.trace_id[:8]}"
    output_dir.mkdir(parents=True, exist_ok=True)
    cover_letter_path = output_dir / "cover_letter.md"
    cover_letter_path.write_text(rendered_cover_letter, encoding="utf-8")

    prompts = st.session_state.get("prompts", {})
    requirements = st.session_state.get("requirements", [])
    chunks = st.session_state.get("chunks", [])
    retrieval_results = st.session_state.get("retrieval_results", [])
    unique_chunk_ids = {
        chunk.chunk_id
        for retrieval in retrieval_results
        for chunk, _ in getattr(retrieval, "retrieved_chunks", [])
    }

    metadata = {
        "trace_id": result.trace_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "prompt_id": prompts.get("prompt_id", "unknown"),
        "prompt_version": prompts.get("prompt_version", "unknown"),
        "model": result.metadata.get("model", "unknown"),
        "token_usage": {
            "prompt_tokens": result.metadata.get("prompt_tokens", 0),
            "completion_tokens": result.metadata.get("completion_tokens", 0),
            "total_tokens": result.metadata.get("total_tokens", 0),
        },
        "generation": {
            "attempts": result.attempts,
            "max_attempts": result.metadata.get("max_attempts", result.attempts),
            "complete": result.complete,
        },
        "retrieval": {
            "requirements_count": len(requirements),
            "retrieval_rounds": len(retrieval_results),
            "unique_chunks": len(unique_chunk_ids),
        },
        "files": {
            "cover_letter": "cover_letter.md",
        },
    }

    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    st.session_state.llm_outputs = {
        "cover_letter_markdown": rendered_cover_letter,
        "cover_letter_path": str(cover_letter_path),
        "output_dir": str(output_dir),
        "trace_id": result.trace_id,
        "timestamp": metadata["generated_at"],
        "metadata_path": str(metadata_path)
    }

    st.session_state.generation_complete = True
    st.session_state.pipeline_stage = 6
    st.rerun()


def _prepare_pipeline_retrieval(trace_id: str) -> Any:
    # Stage 3 (retrieval_view) hat Retrieval bereits ausgeführt und geloggt.
    # Gecachtes Ergebnis verwenden — kein erneuter Run, kein doppeltes Log.
    if st.session_state.get("retrieval_result") is not None:
        return st.session_state.retrieval_result

    # Fallback: Pipeline ausführen falls Stage 3 übersprungen wurde.
    pipeline = get_application_pipeline()
    documents_stage = pipeline.parse_documents(
        st.session_state.cv_file_path,
        st.session_state.job_file_path,
    )
    retrieval_stage = pipeline.run_retrieval(
        documents_stage.data["result"], trace_id=trace_id
    )
    st.session_state.retrieval_result = retrieval_stage.data["retrieval_result"]
    return st.session_state.retrieval_result


def _reset_generation_state() -> None:
    st.session_state.pop("generation_result", None)
    st.session_state.pop("generation_complete", None)
    st.session_state.pop("continuation_attempt", None)
    st.session_state.pop("generation_trace_id", None)