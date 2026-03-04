"""Modular Application Pipeline orchestrating services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from src.infrastructure.logging_service import LoggingService
from src.services.document_service import DocumentResult, DocumentService
from src.services.retrieval_service import RetrievalResult, RetrievalService
from src.services.generation_service import GenerationResult, GenerationService


@dataclass(frozen=True)
class StageResult:
    name: str
    data: Dict[str, Any]


class ApplicationPipeline:
    """Orchestrator, exposing staged API for Document → Retrieval → Generation."""

    def __init__(
        self,
        document_service: DocumentService,
        retrieval_service: RetrievalService,
        generation_service: GenerationService,
        logging_service: LoggingService,
    ) -> None:
        self._document_service = document_service
        self._retrieval_service = retrieval_service
        self._generation_service = generation_service
        self._logging_service = logging_service

    def parse_documents(
        self,
        cv_path: str,
        job_ad_path: str,
    ) -> StageResult:
        result = self._document_service.parse_documents(cv_path, job_ad_path)
        return StageResult(
            name="parse_documents",
            data={
                "result": result,
                "metadata": result.metadata.dict()
            }
        )

    def run_retrieval(
        self,
        document_result: DocumentResult,
        trace_id: str,
    ) -> StageResult:
        retrieval_result = self._retrieval_service.chunk_and_retrieve(
            cv_model=document_result.cv_model,
            job_model=document_result.job_model,
            trace_id=trace_id,
        )
        return StageResult(
            name="run_retrieval",
            data={
                "retrieval_result": retrieval_result,
                "metadata": retrieval_result.metadata,
            }
        )

    def generate_cover_letter(
        self,
        prompts: Dict[str, str],
        retrieval_result: RetrievalResult,
        trace_id: str,
        attempt: int = 1,
    ) -> StageResult:
        generation_result = self._generation_service.generate_with_continuation(
            prompt_id="cover_letter",
            system_prompt=prompts["system"],
            user_prompt=prompts["user"],
            trace_id=trace_id,
            metadata={
                "retrieval_count": retrieval_result.metadata.get("retrieval_count", 0)
            },
            attempt=attempt,
        )
        return StageResult(
            name="generate_cover_letter",
            data={
                "generation_result": generation_result,
                "metadata": generation_result.metadata,
            }
        )

    def continue_generation(
        self,
        prompts: Dict[str, str],
        trace_id: str,
        previous_text: str,
        attempt: int = 1,
    ) -> StageResult:
        patched_prompt = prompts["user"] + "\n" + previous_text
        generation_result = self._generation_service.generate_with_continuation(
            prompt_id="cover_letter",
            system_prompt=prompts["system"],
            user_prompt=patched_prompt,
            trace_id=trace_id,
            attempt=attempt,
        )
        return StageResult(name="continue_generation", data={"generation_result": generation_result})