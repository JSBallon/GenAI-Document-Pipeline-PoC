"""
Job Advertisement Parser für Markdown-Dateien mit YAML Frontmatter.

Parst JobAd.md Dateien und extrahiert strukturierte Daten in JobAdModel.
Folgt OOP/SOLID Principles: Single Responsibility, Dependency Injection.
"""

import re
from pathlib import Path
from typing import Dict, Any
import frontmatter
from pydantic import ValidationError

from src.models.job_ad import (
    JobAdModel, 
    HardSkillsRequirements, 
    SoftSkillsRequirements,
    EducationRequirement
)


class JobAdParsingError(Exception):
    """Custom Exception für JobAd-Parsing-Fehler."""
    pass


class JobAdParser:
    """
    Parser für JobAd.md Dateien.
    
    Extrahiert YAML Frontmatter und Markdown Body zu strukturiertem JobAdModel.
    """
    
    def __init__(self):
        """Initialize Job Ad Parser."""
        pass
    
    def parse_file(self, file_path: str) -> JobAdModel:
        """
        Parse JobAd.md Datei und returniere JobAdModel.
        
        Args:
            file_path: Pfad zur JobAd.md Datei
            
        Returns:
            JobAdModel: Validiertes Job Advertisement Datenmodell
            
        Raises:
            JobAdParsingError: Bei Parsing-Fehlern
            ValidationError: Bei fehlenden Pflichtfeldern (via Pydantic)
        """
        try:
            # Lese Datei
            content = self._read_file(file_path)
            
            # Parse Frontmatter + Markdown
            post = frontmatter.loads(content)
            
            # Extrahiere Frontmatter
            metadata = post.metadata
            
            # Extrahiere Markdown Sections
            sections = self._extract_sections(post.content)
            
            # Baue JobAdModel
            job_data = self._build_job_data(metadata, sections)
            
            # Validiere via Pydantic (wirft ValidationError bei Fehler)
            return JobAdModel(**job_data)
            
        except FileNotFoundError:
            raise JobAdParsingError(f"JobAd-Datei nicht gefunden: {file_path}")
        except ValidationError:
            # ValidationError transparent durchreichen (nicht wrappen)
            raise
        except Exception as e:
            raise JobAdParsingError(f"Fehler beim Parsen der JobAd-Datei: {str(e)}")
    
    def _read_file(self, file_path: str) -> str:
        """Lese Datei von Disk und bereinige Markdown/HTML vor Frontmatter."""
        path = Path(file_path)
        content = path.read_text(encoding='utf-8')
        
        # Entferne alles vor dem ersten --- (YAML Frontmatter Start)
        # Dies entfernt Markdown-Header und HTML-Kommentare
        # Pattern: Alles bis zum ersten ---, dann behalte --- und den Rest
        match = re.search(r'^(---\s*\n)', content, flags=re.MULTILINE)
        if match:
            # Behalte ab erstem --- Delimiter
            content = content[match.start():]
        
        return content
    
    def _extract_sections(self, markdown_content: str) -> Dict[str, str]:
        """
        Extrahiere Markdown Sections (## Header).
        
        Returns:
            Dict mit Section Name → Section Content
        """
        sections = {}
        
        # Split by ## Headers
        pattern = r'^##\s+(.+?)$'
        parts = re.split(pattern, markdown_content, flags=re.MULTILINE)
        
        # parts[0] ist Content vor erstem ##, ignorieren
        # Dann abwechselnd: Header, Content, Header, Content, ...
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                section_name = parts[i].strip()
                section_content = parts[i + 1].strip()
                sections[section_name] = section_content
        
        return sections
    
    def _build_job_data(self, metadata: Dict[str, Any], sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Baue JobAd-Daten-Dict aus Frontmatter + Sections.
        
        Kombiniert Metadaten und geparste Sections zu Pydantic-kompatiblem Dict.
        """
        # Parse Hard Skills Requirements
        hard_skills_data = metadata.get('hard_skills', {})
        hard_skills = HardSkillsRequirements(
            critical=hard_skills_data.get('critical', []),
            important=hard_skills_data.get('important', []),
            nice_to_have=hard_skills_data.get('nice_to_have', [])
        )
        
        # Parse Soft Skills Requirements (optional)
        soft_skills_data = metadata.get('soft_skills')
        soft_skills = None
        if soft_skills_data:
            soft_skills = SoftSkillsRequirements(
                critical=soft_skills_data.get('critical', []),
                important=soft_skills_data.get('important', [])
            )
        
        # Parse Education Requirements (optional)
        education_data = metadata.get('education')
        education = None
        if education_data:
            education = EducationRequirement(
                preferred=education_data.get('preferred'),
                alternative=education_data.get('alternative')
            )
        
        job_data = {
            # Pflicht-Metadaten
            'job_title': metadata.get('job_title', ''),
            'company': metadata.get('company', ''),
            
            # Optionale Metadaten
            'location': metadata.get('location'),
            'employment_type': metadata.get('employment_type'),
            'experience_level': metadata.get('experience_level'),
            'salary_range': metadata.get('salary_range'),
            'remote_policy': metadata.get('remote_policy'),
            
            # Requirements
            'hard_skills': hard_skills,
            'soft_skills': soft_skills,
            'education': education,
            
            # Markdown Body Sections
            'about_company': sections.get('Über uns'),
            'responsibilities': self._extract_responsibilities_section(sections),
            'profile': self._extract_profile_section(sections),
            'benefits': self._extract_benefits_section(sections),
            'tech_stack': sections.get('Technologie-Stack (Details)'),
        }
        
        return job_data
    
    def _extract_responsibilities_section(self, sections: Dict[str, str]) -> str | None:
        """Extrahiere Aufgaben-Section (kann verschiedene Namen haben)."""
        possible_names = ['Deine Aufgaben', 'Aufgaben', 'Responsibilities']
        for name in possible_names:
            if name in sections:
                return sections[name]
        return None
    
    def _extract_profile_section(self, sections: Dict[str, str]) -> str | None:
        """Extrahiere Profil-Section (kann verschiedene Namen haben)."""
        possible_names = ['Dein Profil', 'Profil', 'Requirements', 'Anforderungen']
        for name in possible_names:
            if name in sections:
                return sections[name]
        return None
    
    def _extract_benefits_section(self, sections: Dict[str, str]) -> str | None:
        """Extrahiere Benefits-Section (kann verschiedene Namen haben)."""
        possible_names = ['Was wir bieten', 'Benefits', 'Wir bieten']
        for name in possible_names:
            if name in sections:
                return sections[name]
        return None
