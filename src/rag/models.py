"""
Pydantic Models für RAG-Komponenten.

Definiert typsichere Models für Chunks, Requirements und RAG-Outputs.
Folgt OOP/SOLID Principles: Single Responsibility, Type Safety, Validation.
"""

from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Chunk(BaseModel):
    """
    Einzelner CV-Chunk mit Metadaten für RAG-Retrieval.
    
    Repräsentiert eine semantische Einheit aus dem CV-Dokument,
    entweder eine komplette Section (z.B. Skills) oder einen
    Paragraph aus einer großen Section (z.B. einzelne Position
    aus Berufserfahrung).
    
    Attributes:
        chunk_id: Unique Identifier (Format: cv_<section>_<index>)
        section_type: Kategorie (experience|skills|education|projects|languages|interests)
        section_title: Original Section/Position Title (optional)
        text: Chunk Text Content (100-1000 chars)
        char_start: Start Position im Original-Dokument
        char_end: End Position im Original-Dokument
        metadata: Zusätzliche Metadaten (timestamps, skill_levels, etc.)
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    chunk_id: str = Field(
        ..., 
        description="Unique ID (Format: cv_<section>_<index>)",
        min_length=1
    )
    
    section_type: str = Field(
        ...,
        description="Section Category: experience|skills|education|projects|languages|interests"
    )
    
    section_title: Optional[str] = Field(
        None,
        description="Original Section Title (z.B. 'Senior Backend Developer | TechVision GmbH')"
    )
    
    text: str = Field(
        ...,
        description="Chunk Text Content",
        min_length=1
    )
    
    char_start: int = Field(
        ...,
        description="Start Position im Original-Dokument",
        ge=0
    )
    
    char_end: int = Field(
        ...,
        description="End Position im Original-Dokument",
        ge=0
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Zusätzliche Metadaten (timestamps, skill_levels, recency_scores, etc.)"
    )
    
    def __str__(self) -> str:
        """String Representation für Debugging."""
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Chunk({self.chunk_id}, {self.section_type}, '{preview}')"
    
    def __repr__(self) -> str:
        """Developer-friendly Representation."""
        return (
            f"Chunk(id={self.chunk_id!r}, type={self.section_type!r}, "
            f"chars={self.char_start}-{self.char_end}, len={len(self.text)})"
        )
    
    @property
    def length(self) -> int:
        """Chunk Length in Characters."""
        return len(self.text)
    
    @property
    def has_metadata(self) -> bool:
        """Check if Chunk has additional metadata."""
        return len(self.metadata) > 0


class Requirement(BaseModel):
    """
    Strukturierte Job-Anforderung für RAG-basiertes Skill Matching.
    
    Erweitert das SkillRequirement Model aus job_ad.py mit RAG-spezifischen
    Feldern wie requirement_id, category und context für besseres Retrieval.
    
    Attributes:
        requirement_id: Unique Identifier (Format: req_<category>_<index>)
        text: Requirement Text (z.B. "Python Expert-Level 5+ Jahre")
        category: Kategorie (hard_skill|soft_skill|experience|education)
        priority: Priorität (critical|important|nice_to_have)
        details: Zusätzliche Details (optional)
        context: Kontext aus JobAd (z.B. "Backend-Entwicklung 70%")
        metadata: Zusätzliche Metadaten
    """
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    requirement_id: str = Field(
        ...,
        description="Unique ID (Format: req_<category>_<index>)",
        min_length=1
    )
    
    text: str = Field(
        ...,
        description="Requirement Text Content",
        min_length=1
    )
    
    category: str = Field(
        ...,
        description="Requirement Category: hard_skill|soft_skill|experience|education"
    )
    
    priority: str = Field(
        ...,
        description="Priorität: critical|important|nice_to_have"
    )
    
    details: Optional[str] = Field(
        None,
        description="Zusätzliche Details zur Anforderung"
    )
    
    context: Optional[str] = Field(
        None,
        description="Kontext aus JobAd (z.B. welche Aufgabe, Prozentsatz, etc.)"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Zusätzliche Metadaten (source_section, experience_years, etc.)"
    )
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validiere, dass Category einen erlaubten Wert hat."""
        allowed = ['hard_skill', 'soft_skill', 'experience', 'education']
        if v not in allowed:
            raise ValueError(f'Category muss einer von {allowed} sein')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validiere, dass Priority einen erlaubten Wert hat."""
        allowed = ['critical', 'important', 'nice_to_have']
        if v not in allowed:
            raise ValueError(f'Priority muss einer von {allowed} sein')
        return v
    
    def __str__(self) -> str:
        """String Representation für Debugging."""
        return f"Requirement({self.requirement_id}, {self.category}, {self.priority}, '{self.text[:50]}')"
    
    def __repr__(self) -> str:
        """Developer-friendly Representation."""
        return (
            f"Requirement(id={self.requirement_id!r}, category={self.category!r}, "
            f"priority={self.priority!r}, text={self.text!r})"
        )
    
    @property
    def is_critical(self) -> bool:
        """Check if Requirement is critical."""
        return self.priority == 'critical'
    
    @property
    def is_hard_skill(self) -> bool:
        """Check if Requirement is a hard skill."""
        return self.category == 'hard_skill'
    
    @property
    def is_soft_skill(self) -> bool:
        """Check if Requirement is a soft skill."""
        return self.category == 'soft_skill'


class RequirementExtractionResult(BaseModel):
    """
    Ergebnis der Requirement Extraction aus einem JobAd.
    
    Kapselt die extrahierten Requirements mit Metadaten über
    den Extraction-Prozess für Governance und Debugging.
    
    Attributes:
        requirements: Liste extrahierter Requirements
        source_job_id: Job ID (falls vorhanden)
        extraction_method: Methode (llm_based|rule_based)
        total_count: Anzahl extrahierter Requirements
        by_category: Gruppierung nach Category
        by_priority: Gruppierung nach Priority
    """
    
    model_config = ConfigDict(validate_assignment=True)
    
    requirements: List[Requirement] = Field(
        default_factory=list,
        description="Liste extrahierter Requirements"
    )
    
    source_job_id: Optional[str] = Field(
        None,
        description="Source Job Advertisement ID"
    )
    
    extraction_method: str = Field(
        default="simple",
        description="Extraction Method: simple|llm_based"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extraction Metadata (timestamp, confidence, etc.)"
    )
    
    @property
    def total_count(self) -> int:
        """Total number of extracted requirements."""
        return len(self.requirements)
    
    @property
    def by_category(self) -> Dict[str, List[Requirement]]:
        """Group requirements by category."""
        categories: Dict[str, List[Requirement]] = {
            'hard_skill': [],
            'soft_skill': [],
            'experience': [],
            'education': []
        }
        for req in self.requirements:
            categories[req.category].append(req)
        return categories
    
    @property
    def by_priority(self) -> Dict[str, List[Requirement]]:
        """Group requirements by priority."""
        priorities: Dict[str, List[Requirement]] = {
            'critical': [],
            'important': [],
            'nice_to_have': []
        }
        for req in self.requirements:
            priorities[req.priority].append(req)
        return priorities
    
    @property
    def critical_requirements(self) -> List[Requirement]:
        """Get all critical requirements."""
        return [req for req in self.requirements if req.is_critical]
    
    def get_by_category(self, category: str) -> List[Requirement]:
        """Get requirements by specific category."""
        return [req for req in self.requirements if req.category == category]
    
    def get_by_priority(self, priority: str) -> List[Requirement]:
        """Get requirements by specific priority."""
        return [req for req in self.requirements if req.priority == priority]
    
    def __str__(self) -> str:
        """String Representation für Debugging."""
        return (
            f"RequirementExtractionResult({self.total_count} requirements, "
            f"method={self.extraction_method})"
        )


class EvidenceLink(BaseModel):
    """
    Verknüpfung eines Output-Statements mit Source-Chunks.

    Attributes:
        statement_id: Eindeutige ID des Statements
        statement_text: Originaler Statement-Text
        cited_chunks: Liste zitierter Chunks mit Score und Preview
    """

    model_config = ConfigDict(validate_assignment=True)

    statement_id: str = Field(..., min_length=1)
    statement_text: str = Field(..., min_length=1)
    cited_chunks: List[Dict[str, Any]] = Field(default_factory=list)


class EvidenceMap(BaseModel):
    """
    Vollständige Evidence-Mapping-Struktur.

    Attributes:
        source_type: 'cv' oder 'cover_letter'
        statements: Mapping von Statement ID zu EvidenceLink
        summary: Aggregierte Statistiken
    """

    model_config = ConfigDict(validate_assignment=True)

    source_type: str = Field(..., description="cv|cover_letter")
    statements: List[EvidenceLink] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class AnnotatedOutput(BaseModel):
    """
    Annotierter Output mit Inline-Citations und Evidence Mapping.

    Attributes:
        annotated_text: Output-Text mit Inline-Citations
        evidence_map: EvidenceMap für Traceability
    """

    model_config = ConfigDict(validate_assignment=True)

    annotated_text: str = Field(..., min_length=1)
    evidence_map: EvidenceMap
