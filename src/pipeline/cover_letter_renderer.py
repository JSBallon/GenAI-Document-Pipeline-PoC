"""
Cover Letter Renderer

Verantwortung: Rendert ein Anschreiben aus strukturierter JSON-Ausgabe
inkl. Standard-Einleitung/Abschluss und Inline-Citations.

Compliance: SOLID Principles, Single Responsibility
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CoverLetterRenderConfig:
    """
    Konfiguration für das Anschreiben-Rendering.

    Attributes:
        salutation: Standard-Einleitung
        closing: Standard-Abschluss
        include_citations: Inline-Citations aktivieren
        include_confidence: Confidence in Citations anzeigen
    """

    salutation: str = "Sehr geehrte Damen und Herren,"
    closing: str = "Mit freundlichen Grüßen"
    include_citations: bool = True
    include_confidence: bool = True
    no_evidence_message: str = (
        "Leider liegen keine ausreichenden Nachweise im CV vor, um die "
        "Anforderungen belastbar zu belegen."
    )


@dataclass(frozen=True)
class CandidateDetails:
    """
    Kandidaten-Details für Briefkopf und Signatur.

    Attributes:
        name: Vollständiger Name
        location: Wohnort
        phone: Telefonnummer
        email: E-Mail Adresse
    """

    name: str
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


@dataclass(frozen=True)
class RecipientDetails:
    """
    Empfänger-Details für den Adressblock.

    Attributes:
        company: Unternehmen
        location: Standort
        department: Abteilung (z.B. "HR Abteilung")
    """

    company: str
    location: str
    department: str = "HR Abteilung"


class CoverLetterRenderer:
    """
    Rendert ein vollständiges Anschreiben aus JSON-Absätzen.

    Erwartetes JSON-Format:
    {
      "paragraphs": [
        {
          "text": "...",
          "chunk_ids": ["cv_exp_001"],
          "confidence": 0.87
        }
      ]
    }
    """

    def __init__(self, config: CoverLetterRenderConfig | None = None):
        self._config = config or CoverLetterRenderConfig()

    def render(
        self,
        paragraphs: List[Dict[str, Any]],
        candidate_details: CandidateDetails,
        summary: str | None = None,
        recipient_details: RecipientDetails | None = None,
        job_title: str | None = None,
        letter_date: date | None = None
    ) -> str:
        """
        Render Anschreiben inkl. Einleitung, Absätze und Abschluss.

        Args:
            paragraphs: Liste von Absatz-Dictionaries
            candidate_details: Kandidaten-Details für Briefkopf/Signatur
            summary: Optionaler Zusammenfassungs-Absatz (1-3 Sätze)
            recipient_details: Empfängerblock (Company, Location, HR Abteilung)
            job_title: Jobtitel für Betreffzeile
            letter_date: Datum für Datumszeile

        Returns:
            Anschreiben als Markdown-Text
        """
        body_paragraphs: List[str] = []

        for paragraph in paragraphs:
            text = str(paragraph.get("text", "")).strip()
            if not text:
                continue
            citations = self._format_citations(paragraph)
            body_paragraphs.append(f"{text} {citations}".strip())

        if not body_paragraphs:
            body_paragraphs.append(self._config.no_evidence_message)
        summary_text = (summary or "").strip()
        opening_blocks = [self._build_header(candidate_details)]

        if recipient_details is not None:
            opening_blocks.append(self._build_recipient_block(recipient_details))

        if job_title:
            opening_blocks.append(self._build_subject(job_title))

        if letter_date is not None:
            opening_blocks.append(self._format_date(letter_date))

        opening_blocks.append(self._config.salutation)
        if summary_text:
            opening_blocks.append(summary_text)

        closing_block = self._build_closing(candidate_details.name)

        return "\n\n".join(
            [*opening_blocks, *body_paragraphs, closing_block]
        ).strip()

    def _format_citations(self, paragraph: Dict[str, Any]) -> str:
        if not self._config.include_citations:
            return ""

        chunk_ids = paragraph.get("chunk_ids") or []
        if not chunk_ids:
            return ""

        sources = ", ".join(str(chunk_id) for chunk_id in chunk_ids)
        confidence = paragraph.get("confidence")

        if self._config.include_confidence and confidence is not None:
            try:
                confidence_value = float(confidence)
                return f"[Sources: {sources} | Confidence: {confidence_value:.2f}]"
            except (TypeError, ValueError):
                return f"[Sources: {sources}]"

        return f"[Sources: {sources}]"

    def _build_closing(self, candidate_name: str) -> str:
        name = (candidate_name or "").strip()
        if name:
            return f"{self._config.closing}\n{name}"
        return self._config.closing

    def _build_header(self, candidate_details: CandidateDetails) -> str:
        name = (candidate_details.name or "").strip()
        header_lines = [name] if name else []

        if candidate_details.location:
            header_lines.append(candidate_details.location)
        if candidate_details.phone:
            header_lines.append(candidate_details.phone)
        if candidate_details.email:
            header_lines.append(candidate_details.email)

        return "\n".join(line for line in header_lines if line)

    def _build_recipient_block(self, recipient_details: RecipientDetails) -> str:
        lines = [recipient_details.company, recipient_details.location, recipient_details.department]
        return "\n".join(line for line in lines if line)

    def _build_subject(self, job_title: str) -> str:
        clean_title = job_title.strip()
        return f"**Bewerbung um eine Stelle als {clean_title}**"

    def _format_date(self, letter_date: date) -> str:
        return letter_date.strftime("%d.%m.%Y")