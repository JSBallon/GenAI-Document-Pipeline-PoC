"""
Pydantic Models für CV-Datenstruktur.

Definiert typsichere Models für CV-Parsing mit automatischer Validation.
Folgt OOP/SOLID Principles: Single Responsibility, Type Safety, Validation.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict


class WorkExperience(BaseModel):
    """Model für eine Berufserfahrungs-Position."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    position: str = Field(..., description="Job Titel (z.B. 'Senior Backend Developer')")
    company: str = Field(..., description="Firmenname")
    zeitraum: str = Field(..., description="Zeitraum (z.B. 'März 2022 - Heute')")
    standort: Optional[str] = Field(None, description="Arbeitsort")
    technologien: Optional[str] = Field(None, description="Verwendete Technologien")
    hauptverantwortlichkeiten: Optional[str] = Field(None, description="Aufgabenbeschreibung")
    schluessel_projekte: Optional[str] = Field(None, description="Key Projects")


class Education(BaseModel):
    """Model für Bildungsabschluss."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    degree: str = Field(..., description="Abschluss (z.B. 'M.Sc. Informatik')")
    institution: str = Field(..., description="Universität/Hochschule")
    zeitraum: str = Field(..., description="Zeitraum")
    schwerpunkt: Optional[str] = Field(None, description="Studienschwerpunkt")
    note: Optional[str] = Field(None, description="Abschlussnote")


class Project(BaseModel):
    """Model für Projekt oder Zusatzqualifikation."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    title: str = Field(..., description="Projekt-Titel")
    description: str = Field(..., description="Projekt-Beschreibung")
    category: Optional[str] = Field(None, description="Kategorie (z.B. 'Open Source', 'Zertifizierung')")


class Language(BaseModel):
    """Model für Sprachkenntnisse."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    language: str = Field(..., description="Sprache")
    level: str = Field(..., description="Niveau (z.B. 'Muttersprache', 'C1')")


class CVModel(BaseModel):
    """
    Hauptmodel für CV-Daten.
    
    Validiert Pflichtfelder und strukturiert CV-Inhalte für weitere Verarbeitung.
    """
    
    # Pflichtfelder aus YAML Frontmatter
    name: str = Field(..., description="Vollständiger Name")
    email: EmailStr = Field(..., description="E-Mail Adresse")
    
    # Optionale Kontaktdaten
    phone: Optional[str] = Field(None, description="Telefonnummer")
    location: Optional[str] = Field(None, description="Wohnort")
    profile_summary: Optional[str] = Field(None, description="Kurze Profilzusammenfassung")
    
    # Pflicht-Sections (mindestens 1 Eintrag erforderlich)
    berufserfahrung: List[WorkExperience] = Field(
        ..., 
        min_length=1, 
        description="Berufserfahrung (mind. 1 Position erforderlich)"
    )
    skills: Dict[str, List[str]] = Field(
        ..., 
        description="Skills kategorisiert (mind. 1 Kategorie erforderlich)"
    )
    
    # Optionale Sections
    bildung: List[Education] = Field(default_factory=list, description="Bildungsabschlüsse")
    projekte: List[Project] = Field(default_factory=list, description="Projekte & Zusatzqualifikationen")
    sprachen: List[Language] = Field(default_factory=list, description="Sprachkenntnisse")
    interessen: Optional[str] = Field(None, description="Persönliche Interessen")
    
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
    
    @field_validator('skills')
    @classmethod
    def validate_skills_not_empty(cls, v):
        """Validiere, dass mindestens eine Skill-Kategorie mit Einträgen vorhanden ist."""
        if not v or all(len(skills) == 0 for skills in v.values()):
            raise ValueError('Skills müssen mindestens eine Kategorie mit Einträgen enthalten')
        return v
    
    @field_validator('name', 'email')
    @classmethod
    def validate_required_fields_not_empty(cls, v):
        """Validiere, dass Pflichtfelder nicht leer sind."""
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError('Feld darf nicht leer sein')
        return v
