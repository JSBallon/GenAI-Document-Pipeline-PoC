"""LLM generation helper with continuation awareness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from src.infrastructure.logging_service import LoggingService
from src.llm.openai_client import OpenRouterClient, LLMResponse
from src.pipeline.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class GenerationResult:
    text: str
    complete: bool
    attempts: int
    finish_reason: str
    trace_id: str
    metadata: Dict[str, Any]


class GenerationService:
    """Handles prompt construction, LLM call, logging, and continuation hints."""

    def __init__(
        self,
        llm_client: OpenRouterClient,
        prompt_builder: PromptBuilder,
        logging_service: LoggingService,
        max_attempts: int = 3,
    ) -> None:
        self._llm_client = llm_client
        self._prompt_builder = prompt_builder
        self._logging_service = logging_service
        self._max_attempts = max_attempts

    def generate_with_continuation(
        self,
        prompt_id: str,
        system_prompt: str,
        user_prompt: str,
        trace_id: str,
        metadata: Dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> GenerationResult:
        """Invoke the LLM once and return a GenerationResult for the given attempt."""
        if attempt > self._max_attempts:
            return GenerationResult(
                text="",
                complete=False,
                attempts=attempt,
                finish_reason="max_attempts",
                trace_id=trace_id,
                metadata={"attempts": attempt, "max_attempts": self._max_attempts},
            )

        current_prompt = user_prompt
        aggregated_texts: List[str] = []
        finish_reason = "length"
        attempts_made = attempt

        while attempts_made <= self._max_attempts:
            self._logging_service.log_prompt_sent(
                trace_id=trace_id,
                prompt_id=prompt_id,
                prompt_text=current_prompt,
                model=self._llm_client.config.model,
                metadata=metadata,
            )

            try:
                response: LLMResponse = self._llm_client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": current_prompt}
                    ],
                    trace_id=trace_id,
                )

                self._logging_service.log_response_received(
                    trace_id=trace_id,
                    response=response,
                    finish_reason=response.finish_reason,
                )
            except Exception as exc:
                self._logging_service.log_llm_failure(
                    trace_id=trace_id,
                    prompt_id=prompt_id,
                    error=str(exc),
                )
                raise

            aggregated_texts.append(response.content)
            finish_reason = response.finish_reason

            if finish_reason != "length":
                break

            if attempts_made == self._max_attempts:
                break

            current_prompt = f"{current_prompt}\n{response.content}"
            attempts_made += 1

        complete = finish_reason != "length"
        metadata_out = {
            "attempts": attempts_made,
            "max_attempts": self._max_attempts,
            "finish_reason": finish_reason,
            "llm_model": self._llm_client.config.model,
            "temperature": self._llm_client.config.temperature,
            "max_tokens": self._llm_client.config.max_tokens,
        }

        return GenerationResult(
            text="\n".join(aggregated_texts).strip(),
            complete=complete,
            attempts=attempts_made,
            finish_reason=finish_reason,
            trace_id=trace_id,
            metadata=metadata_out,
        )