"""Shared ApplicationPipeline context for UI helpers."""

from uuid import uuid4

import streamlit as st

from config.env_loader import load_project_env
from src.infrastructure.logging_service import LoggingService
from src.llm.openai_client import create_client_from_env
from src.pipeline.application_pipeline import ApplicationPipeline
from src.pipeline.prompt_builder import PromptBuilder
from src.services.document_service import DocumentService
from src.services.generation_service import GenerationService
from src.services.retrieval_service import RetrievalService


def get_application_pipeline() -> ApplicationPipeline:
    """Lazily build and cache the shared ApplicationPipeline."""
    if "application_pipeline" not in st.session_state:
        load_project_env()
        logging_service = LoggingService()
        document_service = DocumentService()
        retrieval_service = RetrievalService(logging_service=logging_service)
        prompt_builder = PromptBuilder()
        llm_client = create_client_from_env()
        generation_service = GenerationService(
            llm_client=llm_client,
            prompt_builder=prompt_builder,
            logging_service=logging_service,
        )
        st.session_state.application_pipeline = ApplicationPipeline(
            document_service=document_service,
            retrieval_service=retrieval_service,
            generation_service=generation_service,
            logging_service=logging_service,
        )
    return st.session_state.application_pipeline


def new_trace_id(prefix: str) -> str:
    """Create a short trace id with a human prefix for logging."""
    return f"{prefix}_{uuid4().hex[:8]}"