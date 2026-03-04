"""Minimal Logging Service for Phase 1"""

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


class LoggingService:
    """Basic JSONL logging for prompts and retrieval events."""

    def __init__(self, logs_root: Path | str = "logs"):
        self._logs_root = Path(logs_root)

    def log_prompt_sent(
        self,
        trace_id: str,
        prompt_id: str,
        prompt_text: str,
        model: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Log prompt send events immediately."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "prompt_sent",
            "prompt_id": prompt_id,
            "model": model,
            "prompt_text": prompt_text,
            "metadata": metadata or {},
        }
        self._write_jsonl("prompts", entry)

    def log_response_received(
        self,
        trace_id: str,
        response: Any,
        finish_reason: str,
    ) -> None:
        """Log LLM response data for governance tracing."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "llm_response",
            "finish_reason": finish_reason,
            "response_preview": str(response.content)[:512],
        }
        self._write_jsonl("prompts", entry)

    def log_retrieval_event(
        self,
        trace_id: str,
        requirement: str,
        chunks: Sequence[Mapping[str, Any]],
        retrieval_params: Mapping[str, Any] | None = None,
    ) -> None:
        """Log retrieval decisions per requirement."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "retrieval",
            "requirement": requirement,
            "chunks": [dict(chunk) for chunk in chunks],
            "retrieval_params": retrieval_params or {},
        }
        self._write_jsonl("retrieval", entry)

    def _write_jsonl(self, subdir: str, entry: Dict[str, Any]) -> None:
        dir_path = self._logs_root / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        filename = date.today().strftime("%Y-%m-%d") + ".jsonl"
        file_path = dir_path / filename
        with file_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def log_retrieval_start(
        self,
        trace_id: str,
        requirement: str,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "retrieval_start",
            "requirement": requirement,
        }
        self._write_jsonl("retrieval", entry)

    def log_retrieval_success(
        self,
        trace_id: str,
        requirement: str,
        chunks: Sequence[Mapping[str, Any]],
        retrieval_params: Mapping[str, Any] | None = None,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "retrieval_success",
            "requirement": requirement,
            "chunks": [dict(chunk) for chunk in chunks],
            "retrieval_params": retrieval_params or {},
        }
        self._write_jsonl("retrieval", entry)

    def log_retrieval_failure(
        self,
        trace_id: str,
        requirement: str,
        error: str,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "retrieval_failure",
            "requirement": requirement,
            "error": error,
        }
        self._write_jsonl("retrieval", entry)

    def log_llm_failure(
        self,
        trace_id: str,
        prompt_id: str,
        error: str,
    ) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "event_type": "llm_failure",
            "prompt_id": prompt_id,
            "error": error,
        }
        self._write_jsonl("prompts", entry)