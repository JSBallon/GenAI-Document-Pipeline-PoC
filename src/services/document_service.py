"""Document processing helper service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

from src.models.cv import CVModel
from src.models.job_ad import JobAdModel
from src.parsers.cv_parser import CVParser
from src.parsers.job_parser import JobAdParser


class DocumentMetadata(BaseModel):
    """Meta-Informationen für Dokumente."""

    cv_path: str
    job_ad_path: str
    parsed_at: datetime


class DocumentResult(BaseModel):
    """Aggregierte Ergebnisse aus DocumentService."""

    cv_model: CVModel
    job_model: JobAdModel
    metadata: DocumentMetadata

    class Config:
        frozen = True


class DocumentService:
    """Service für das Parsen und Validieren von CVs und Stellenausschreibungen."""

    def __init__(
        self,
        cv_parser: Optional[CVParser] = None,
        job_parser: Optional[JobAdParser] = None,
    ) -> None:
        self._cv_parser = cv_parser or CVParser()
        self._job_parser = job_parser or JobAdParser()
        self._cache: Dict[str, DocumentResult] = {}

    def parse_documents(
        self,
        cv_path: str,
        job_ad_path: str,
    ) -> DocumentResult:
        """Parset die Dokumente und gibt das geparste Ergebnis zurück."""

        cache_key = f"{cv_path}|{job_ad_path}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        cv_model = self._cv_parser.parse_file(cv_path)
        job_model = self._job_parser.parse_file(job_ad_path)

        metadata = DocumentMetadata(
            cv_path=cv_path,
            job_ad_path=job_ad_path,
            parsed_at=datetime.utcnow(),
        )

        result = DocumentResult(
            cv_model=cv_model,
            job_model=job_model,
            metadata=metadata,
        )

        self._cache[cache_key] = result
        return result