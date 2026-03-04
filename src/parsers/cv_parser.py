"""
CV Parser für Markdown-Dateien mit YAML Frontmatter.

Parst CV.md Dateien und extrahiert strukturierte Daten in CVModel.
Folgt OOP/SOLID Principles: Single Responsibility, Dependency Injection.
"""

import re
from pathlib import Path
from typing import Dict, List, Any
import frontmatter
from pydantic import ValidationError

from src.models.cv import CVModel, WorkExperience, Education, Project, Language


class CVParsingError(Exception):
    """Custom Exception für CV-Parsing-Fehler."""
    pass


class CVParser:
    """
    Parser für CV.md Dateien.
    
    Extrahiert YAML Frontmatter und Markdown Sections zu strukturiertem CVModel.
    """
    
    def __init__(self):
        """Initialize CV Parser."""
        pass
    
    def parse_file(self, file_path: str) -> CVModel:
        """
        Parse CV.md Datei und returniere CVModel.
        
        Args:
            file_path: Pfad zur CV.md Datei
            
        Returns:
            CVModel: Validiertes CV-Datenmodell
            
        Raises:
            CVParsingError: Bei Parsing-Fehlern
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
            
            # Baue CVModel
            cv_data = self._build_cv_data(metadata, sections)
            
            # Validiere via Pydantic (wirft ValidationError bei Fehler)
            return CVModel(**cv_data)
            
        except FileNotFoundError:
            raise CVParsingError(f"CV-Datei nicht gefunden: {file_path}")
        except ValidationError:
            # ValidationError transparent durchreichen (nicht wrappen)
            raise
        except Exception as e:
            raise CVParsingError(f"Fehler beim Parsen der CV-Datei: {str(e)}")
    
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
    
    def _build_cv_data(self, metadata: Dict[str, Any], sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Baue CV-Daten-Dict aus Frontmatter + Sections.
        
        Kombiniert Metadaten und geparste Sections zu Pydantic-kompatiblem Dict.
        """
        cv_data = {
            # Frontmatter Felder
            'name': metadata.get('name', ''),
            'email': metadata.get('email', ''),
            'phone': metadata.get('phone'),
            'location': metadata.get('location'),
            'profile_summary': metadata.get('profile_summary'),
            
            # Sections (werden weiter geparst)
            'berufserfahrung': self._parse_berufserfahrung(sections.get('Berufserfahrung', '')),
            'skills': self._parse_skills(sections.get('Skills', '')),
            'bildung': self._parse_bildung(sections.get('Bildung', '')),
            'projekte': self._parse_projekte(sections.get('Projekte & Zusatzqualifikationen', '')),
            'sprachen': self._parse_sprachen(sections.get('Sprachen', '')),
            'interessen': sections.get('Interessen'),
        }
        
        return cv_data
    
    def _parse_berufserfahrung(self, section_content: str) -> List[WorkExperience]:
        """
        Parse Berufserfahrung Section zu List[WorkExperience].
        
        Erwartet Format:
        ### Position | Company
        **Zeitraum:** ...
        **Standort:** ...
        **Technologien:** ...
        """
        experiences = []
        
        # Split by ### Subsections
        pattern = r'^###\s+(.+?)$'
        parts = re.split(pattern, section_content, flags=re.MULTILINE)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                header = parts[i].strip()
                content = parts[i + 1].strip()
                
                # Parse Header: "Position | Company"
                if '|' in header:
                    position, company = [x.strip() for x in header.split('|', 1)]
                else:
                    position = header
                    company = "Unknown"
                
                # Parse Content für Metadaten
                zeitraum = self._extract_field(content, r'\*\*Zeitraum:\*\*\s*(.+?)(?:\n|$)')
                standort = self._extract_field(content, r'\*\*Standort:\*\*\s*(.+?)(?:\n|$)')
                technologien = self._extract_field(content, r'\*\*Technologien:\*\*\s*(.+?)(?:\n|$)')
                
                # Restlicher Content als Beschreibung
                hauptverantwortlichkeiten = self._extract_responsibilities(content)
                schluessel_projekte = self._extract_projects(content)
                
                experience = WorkExperience(
                    position=position,
                    company=company,
                    zeitraum=zeitraum or "",
                    standort=standort,
                    technologien=technologien,
                    hauptverantwortlichkeiten=hauptverantwortlichkeiten,
                    schluessel_projekte=schluessel_projekte
                )
                experiences.append(experience)
        
        return experiences
    
    def _parse_skills(self, section_content: str) -> Dict[str, List[str]]:
        """
        Parse Skills Section zu kategorisiertem Dict.
        
        Erwartet Format:
        ### Kategorie
        **Label:** Skill1, Skill2, Skill3
        """
        skills_dict = {}
        
        # Split by ### Subsections
        pattern = r'^###\s+(.+?)$'
        parts = re.split(pattern, section_content, flags=re.MULTILINE)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                category = parts[i].strip()
                content = parts[i + 1].strip()
                
                # Parse alle **Label:** Lines
                skill_lines = re.findall(r'\*\*(.+?):\*\*\s*(.+?)(?:\n|$)', content)
                
                category_skills = []
                for label, skills_str in skill_lines:
                    # Split Skills by comma
                    skills = [s.strip() for s in skills_str.split(',')]
                    category_skills.extend(skills)
                
                if category_skills:
                    skills_dict[category] = category_skills
        
        # Fallback: Falls keine Subsections, parse flat
        if not skills_dict and section_content.strip():
            skill_lines = re.findall(r'\*\*(.+?):\*\*\s*(.+?)(?:\n|$)', section_content)
            for label, skills_str in skill_lines:
                skills = [s.strip() for s in skills_str.split(',')]
                skills_dict[label] = skills
        
        return skills_dict
    
    def _parse_bildung(self, section_content: str) -> List[Education]:
        """Parse Bildung Section zu List[Education]."""
        educations = []
        
        # Split by ### Subsections
        pattern = r'^###\s+(.+?)$'
        parts = re.split(pattern, section_content, flags=re.MULTILINE)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                degree_line = parts[i].strip()
                content = parts[i + 1].strip()
                
                # Header ist kompletter Degree (kann "—" für Studiengang enthalten)
                degree = degree_line
                
                # Extrahiere Institution und Zeitraum aus separaten Feldern
                institution = self._extract_field(content, r'\*\*Universität:\*\*\s*(.+?)(?:\n|$)')
                zeitraum = self._extract_field(content, r'\*\*Zeitraum:\*\*\s*(.+?)(?:\n|$)')
                schwerpunkt = self._extract_field(content, r'\*\*Schwerpunkt:\*\*\s*(.+?)(?:\n|$)')
                note = self._extract_field(content, r'\*\*Abschlussnote:\*\*\s*(.+?)(?:\n|$)')
                
                education = Education(
                    degree=degree,
                    institution=institution or "Unknown",
                    zeitraum=zeitraum or "",
                    schwerpunkt=schwerpunkt,
                    note=note
                )
                educations.append(education)
        
        return educations
    
    def _parse_projekte(self, section_content: str) -> List[Project]:
        """Parse Projekte Section zu List[Project]."""
        projects = []
        
        # Einfaches Parsing: ### als Projekt-Titel
        pattern = r'^###\s+(.+?)$'
        parts = re.split(pattern, section_content, flags=re.MULTILINE)
        
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts):
                title = parts[i].strip()
                description = parts[i + 1].strip()
                
                project = Project(
                    title=title,
                    description=description,
                    category=None
                )
                projects.append(project)
        
        return projects
    
    def _parse_sprachen(self, section_content: str) -> List[Language]:
        """
        Parse Sprachen Section zu List[Language].
        
        Erwartet Format:
        - **Deutsch:** Muttersprache
        - **Englisch:** Fließend (C1)
        """
        languages = []
        
        # Parse bullet points mit **Language:** Level
        pattern = r'-\s*\*\*(.+?):\*\*\s*(.+?)(?:\n|$)'
        matches = re.findall(pattern, section_content)
        
        for language_name, level in matches:
            language = Language(
                language=language_name.strip(),
                level=level.strip()
            )
            languages.append(language)
        
        return languages
    
    def _extract_field(self, content: str, pattern: str) -> str | None:
        """Extrahiere Feld mit Regex Pattern."""
        match = re.search(pattern, content)
        return match.group(1).strip() if match else None
    
    def _extract_responsibilities(self, content: str) -> str | None:
        """Extrahiere Hauptverantwortlichkeiten Section."""
        pattern = r'\*\*Hauptverantwortlichkeiten:\*\*\s*(.+?)(?:\*\*Schlüsselprojekte:|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _extract_projects(self, content: str) -> str | None:
        """Extrahiere Schlüsselprojekte Section."""
        pattern = r'\*\*Schlüsselprojekte:\*\*\s*(.+?)(?:\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
