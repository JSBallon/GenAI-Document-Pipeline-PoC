"""
OpenAI/OpenRouter LLM Client mit Governance Logging.

Dieser Client nutzt OpenRouter.ai als einheitliches API Gateway für verschiedene
LLM Provider (OpenAI, Anthropic, etc.) und implementiert vollständiges Prompt Logging
gemäß Governance-Anforderungen.

Patterns:
- Secrets Management (systemPatterns.md §4.7.4)
- Prompt Logging (systemPatterns.md §4.5.1)
- Fallback Chain (systemPatterns.md §4.6.4)
"""

import os
import json
import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from pydantic import BaseModel, Field

from config.env_loader import load_project_env


class LLMConfig(BaseModel):
    """Konfiguration für LLM Client."""
    
    api_key: str = Field(..., description="OpenRouter API Key")
    base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="API Base URL (OpenRouter Gateway)"
    )
    model: str = Field(
        default="openai/gpt-4-turbo",
        description="Default Model (OpenRouter Format: provider/model)"
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum Tokens to generate"
    )
    temperature: float = Field(
        default=0.7,
        description="Sampling Temperature (0.0 - 2.0)"
    )
    timeout: int = Field(
        default=60,
        description="Request Timeout in Sekunden"
    )
    max_retries: int = Field(
        default=3,
        description="Maximale Anzahl Retries bei Fehlern"
    )
    log_prompts: bool = Field(
        default=True,
        description="Prompt Logging aktivieren"
    )
    log_dir: Path = Field(
        default=Path("logs/prompts"),
        description="Verzeichnis für Prompt Logs"
    )


class ChatMessage(BaseModel):
    """Chat Message für LLM API."""
    
    role: str = Field(..., description="Rolle: system, user, assistant")
    content: str = Field(..., description="Message Content")


class LLMResponse(BaseModel):
    """Strukturierte LLM Response mit Metadata."""
    
    content: str = Field(..., description="Generated Content")
    model: str = Field(..., description="Verwendetes Model")
    prompt_tokens: int = Field(default=0, description="Input Tokens")
    completion_tokens: int = Field(default=0, description="Output Tokens")
    total_tokens: int = Field(default=0, description="Total Tokens")
    finish_reason: str = Field(default="stop", description="Finish Reason")
    execution_time_ms: int = Field(default=0, description="Execution Time")
    trace_id: Optional[str] = Field(default=None, description="Trace ID für Logging")


class OpenRouterClient:
    """
    LLM Client für OpenRouter.ai Gateway.
    
    Unterstützt:
    - Multiple Models (OpenAI GPT-4, Anthropic Claude, etc.)
    - Comprehensive Prompt Logging
    - Error Handling mit Retries
    - Rate Limit Management
    - Timeout Control
    
    Example:
        >>> config = LLMConfig(api_key=os.getenv("OPENROUTER_API_KEY"))
        >>> client = OpenRouterClient(config)
        >>> response = client.chat_completion(
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
        >>> print(response.content)
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialisiere LLM Client.
        
        Args:
            config: LLM Configuration
        
        Raises:
            ValueError: Wenn API Key fehlt
        """
        self.config = config
        
        if not config.api_key:
            raise ValueError("API Key ist erforderlich")
        
        # OpenAI Client mit OpenRouter Base URL
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
            max_retries=0  # Manuelle Retry Logic
        )
        
        # Erstelle Log Directory
        if config.log_prompts:
            config.log_dir.mkdir(parents=True, exist_ok=True)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Chat Completion Request mit Retry Logic.
        
        Args:
            messages: Liste von Chat Messages (role + content)
            model: Model Name (OpenRouter Format), default: config.default_model
            temperature: Sampling Temperature (0.0 - 2.0)
            max_tokens: Maximum Tokens to generate
            trace_id: Optional Trace ID für Log Correlation
            **kwargs: Weitere OpenAI API Parameter
        
        Returns:
            LLMResponse mit generiertem Content und Metadata
        
        Raises:
            APIError: Bei kritischen API Fehlern
            Timeout: Bei Timeout
        """
        model = model or self.config.model
        trace_id = trace_id or self._generate_trace_id()
        
        start_time = time.time()
        last_error = None
        
        # Retry Loop
        for attempt in range(1, self.config.max_retries + 1):
            try:
                # API Call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
                
                # Extract Response Data
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                llm_response = LLMResponse(
                    content=response.choices[0].message.content,
                    model=response.model,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    total_tokens=response.usage.total_tokens if response.usage else 0,
                    finish_reason=response.choices[0].finish_reason,
                    execution_time_ms=execution_time_ms,
                    trace_id=trace_id
                )
                
                # Log Prompt & Response
                if self.config.log_prompts:
                    self._log_prompt(
                        trace_id=trace_id,
                        messages=messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response=llm_response,
                        attempt=attempt
                    )
                
                return llm_response
            
            except RateLimitError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    # Exponential Backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            
            except APITimeoutError as e:
                last_error = e
                if attempt < self.config.max_retries:
                    time.sleep(1)
                    continue
                else:
                    raise
            
            except APIError as e:
                # Kritische Fehler nicht retried
                last_error = e
                raise
        
        # Alle Retries fehlgeschlagen
        raise last_error
    
    def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        trace_id: Optional[str] = None
    ) -> LLMResponse:
        """
        Einfacher Completion Request (nur User Prompt).
        
        Args:
            prompt: User Prompt
            model: Model Name
            temperature: Sampling Temperature
            max_tokens: Maximum Tokens
            trace_id: Optional Trace ID
        
        Returns:
            LLMResponse
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            trace_id=trace_id
        )
    
    def _generate_trace_id(self) -> str:
        """Generiere eindeutige Trace ID."""
        timestamp = datetime.now().isoformat()
        random_component = os.urandom(8).hex()
        return f"trace_{hashlib.md5(f'{timestamp}_{random_component}'.encode()).hexdigest()[:16]}"
    
    def _log_prompt(
        self,
        trace_id: str,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        response: LLMResponse,
        attempt: int
    ) -> None:
        """
        Log Prompt & Response (Governance Requirement).
        
        Pattern: systemPatterns.md §4.5.1 (Prompt Logging)
        
        Args:
            trace_id: Trace ID
            messages: Chat Messages
            model: Model Name
            temperature: Temperature
            max_tokens: Max Tokens
            response: LLM Response
            attempt: Retry Attempt Number
        """
        # Combine Messages zu Full Prompt Text
        full_prompt = "\n\n".join([
            f"[{msg['role'].upper()}]\n{msg['content']}"
            for msg in messages
        ])
        
        log_entry = {
            "trace_id": trace_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": "llm_completion",
            "attempt": attempt,
            "prompt": {
                "messages": messages,
                "full_text": full_prompt,
                "char_count": len(full_prompt),
                "hash": hashlib.sha256(full_prompt.encode()).hexdigest()
            },
            "model": {
                "name": model,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "response": {
                "content": response.content,
                "content_preview": response.content[:200] + "..." if len(response.content) > 200 else response.content,
                "finish_reason": response.finish_reason
            },
            "usage": {
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens
            },
            "performance": {
                "execution_time_ms": response.execution_time_ms
            }
        }
        
        # Save to JSONL File (one log entry per line)
        log_file = self.config.log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def create_client_from_env() -> OpenRouterClient:
    """
    Factory Function: Erstelle Client aus Environment Variables.
    
    Required Environment Variables:
        OPENROUTER_API_KEY: API Key für OpenRouter.ai
    
    Optional Environment Variables:
        DEFAULT_MODEL: Default Model (z.B. "openai/gpt-4-turbo")
        LLM_TIMEOUT: Request Timeout in Sekunden (default: 60)
        LLM_MAX_RETRIES: Max Retries (default: 3)
    
    Returns:
        OpenRouterClient
    
    Raises:
        ValueError: Wenn OPENROUTER_API_KEY fehlt
    
    Example:
        >>> client = create_client_from_env()
        >>> response = client.simple_completion("Hello, world!")
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        load_project_env()
        api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY Environment Variable fehlt. "
            "Bitte setzen Sie die Variable oder erstellen Sie eine .env Datei."
        )
    
    config = LLMConfig(
        api_key=api_key,
        model=os.getenv("DEFAULT_MODEL", "openai/gpt-4-turbo"),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        timeout=int(os.getenv("LLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "3"))
    )
    
    return OpenRouterClient(config)
