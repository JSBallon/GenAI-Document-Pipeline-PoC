"""
Pydantic Models für Job Advertisement Datenstruktur.

Definiert typsichere Models für JobAd-Parsing mit automatischer Validation.
Folgt OOP/SOLID Principles: Single Responsibility, Type Safety, Validation.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator, ConfigDict


class SkillRequirement(BaseModel):
    """Model für einzelne Skill-Anforderung."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    skill: str = Field(..., description="Skill Name (z.B. 'Python', 'Django')")
    priority: str = Field(..., description="Priorität: 'critical', 'important', 'nice_to_have'")
    details: Optional[str] = Field(None, description="Zusätzliche Details zur Anforderung")
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        """Validiere, dass Priorität einen erlaubten Wert hat."""
        allowed = ['critical', 'important', 'nice_to_have']
        if v not in allowed:
            raise ValueError(f'Priority muss einer von {allowed} sein')
        return v


class HardSkillsRequirements(BaseModel):
    """Model für Hard Skills Requirements (kategorisiert nach Priorität)."""
    
    critical: List[str] = Field(default_factory=list, description="Kritische Hard Skills (must-have)")
    important: List[str] = Field(default_factory=list, description="Wichtige Hard Skills")
    nice_to_have: List[str] = Field(default_factory=list, description="Nice-to-have Hard Skills")
    
    @field_validator('critical')
    @classmethod
    def validate_critical_not_empty(cls, v):
        """Validiere, dass mindestens ein critical Hard Skill vorhanden ist."""
        if not v or len(v) == 0:
            raise ValueError('Mindestens ein critical Hard Skill ist erforderlich')
        return v


class SoftSkillsRequirements(BaseModel):
    """Model für Soft Skills Requirements (kategorisiert nach Priorität)."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    critical: List[str] = Field(default_factory=list, description="Kritische Soft Skills")
    important: List[str] = Field(default_factory=list, description="Wichtige Soft Skills")


class EducationRequirement(BaseModel):
    """Model für Bildungsanforderungen."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    preferred: Optional[str] = Field(None, description="Bevorzugter Abschluss")
    alternative: Optional[str] = Field(None, description="Alternative Qualifikation")


class JobAdModel(BaseModel):
    """
    Hauptmodel für Job Advertisement Daten.
    
    Validiert Pflichtfelder und strukturiert JobAd-Inhalte für weitere Verarbeitung.
    """
    
    # Pflichtfelder aus YAML Frontmatter
    job_title: str = Field(..., description="Job Titel")
    company: str = Field(..., description="Firmenname")
    
    # Optionale Metadaten
    location: Optional[str] = Field(None, description="Arbeitsort")
    employment_type: Optional[str] = Field(None, description="Anstellungsart (z.B. 'Vollzeit')")
    experience_level: Optional[str] = Field(None, description="Erfahrungslevel (z.B. 'Senior')")
    salary_range: Optional[str] = Field(None, description="Gehaltsrange")
    remote_policy: Optional[str] = Field(None, description="Remote-Regelung")
    
    # Requirements (Pflicht: mindestens Hard Skills)
    hard_skills: HardSkillsRequirements = Field(
        ..., 
        description="Hard Skills Requirements (kategorisiert)"
    )
    soft_skills: Optional[SoftSkillsRequirements] = Field(
        None, 
        description="Soft Skills Requirements (optional)"
    )
    education: Optional[EducationRequirement] = Field(
        None, 
        description="Bildungsanforderungen (optional)"
    )
    
    # Markdown Body Content (optional)
    about_company: Optional[str] = Field(None, description="Über das Unternehmen")
    responsibilities: Optional[str] = Field(None, description="Aufgaben & Verantwortlichkeiten")
    profile: Optional[str] = Field(None, description="Anforderungsprofil")
    benefits: Optional[str] = Field(None, description="Benefits & Angebote")
    tech_stack: Optional[str] = Field(None, description="Technologie-Stack Details")
    
    @field_validator('job_title', 'company')
    @classmethod
    def validate_required_fields_not_empty(cls, v):
        """Validiere, dass Pflichtfelder nicht leer sind."""
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError('Feld darf nicht leer sein')
        return v
    
    def get_all_requirements_flat(self) -> List[SkillRequirement]:
        """
        Hilfsmethode: Gibt alle Requirements als flache Liste zurück.
        
        Nützlich für spätere Requirement Extraction in M2.
        """
        requirements = []
        
        # Hard Skills
        for skill in self.hard_skills.critical:
            requirements.append(SkillRequirement(skill=skill, priority='critical'))
        for skill in self.hard_skills.important:
            requirements.append(SkillRequirement(skill=skill, priority='important'))
        for skill in self.hard_skills.nice_to_have:
            requirements.append(SkillRequirement(skill=skill, priority='nice_to_have'))
        
        # Soft Skills (wenn vorhanden)
        if self.soft_skills:
            for skill in self.soft_skills.critical:
                requirements.append(SkillRequirement(skill=skill, priority='critical'))
            for skill in self.soft_skills.important:
                requirements.append(SkillRequirement(skill=skill, priority='important'))
        
        return requirements
    
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)
