"""
Hybrid Chunking Strategy für CV-Dokumente.

Implementiert zweistufige Chunking-Logik:
1. Primary: Section-basiertes Chunking (semantische Einheiten)
2. Fallback: Paragraph-basiertes Chunking (große Sections >1000 chars)

Folgt OOP/SOLID Principles:
- Single Responsibility: Nur Chunking Logic
- Open/Closed: Erweiterbar durch Subclassing
- Dependency Injection: Config via Constructor
"""

from typing import List, Dict, Any
import re
from datetime import datetime

from src.models.cv import CVModel, WorkExperience, Education, Project, Language
from src.rag.models import Chunk


class HybridChunker:
    """
    Hybrid Chunking Strategy für CV-Dokumente.
    
    Konvertiert CVModel in eine Liste von Chunks mit Metadaten.
    Verwendet section-basiertes Chunking als Primary Strategy und
    paragraph-basiertes Chunking als Fallback für große Sections.
    
    Attributes:
        _min_size: Minimale Chunk-Größe in Zeichen (default: 100)
        _max_size: Maximale Chunk-Größe in Zeichen (default: 1000)
        _overlap: Overlap zwischen Chunks in Zeichen (default: 50)
    
    Example:
        >>> chunker = HybridChunker(min_chunk_size=100, max_chunk_size=1000)
        >>> chunks = chunker.chunk_cv(cv_model)
        >>> print(f"Generated {len(chunks)} chunks")
    """
    
    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000,
        overlap_size: int = 50
    ):
        """
        Initialize HybridChunker mit Size Constraints.
        
        Args:
            min_chunk_size: Minimale Chunk-Größe (default: 100 chars)
            max_chunk_size: Maximale Chunk-Größe (default: 1000 chars)
            overlap_size: Overlap zwischen Chunks (default: 50 chars)
        
        Raises:
            ValueError: Wenn min_chunk_size >= max_chunk_size
        """
        if min_chunk_size >= max_chunk_size:
            raise ValueError(
                f"min_chunk_size ({min_chunk_size}) muss kleiner als "
                f"max_chunk_size ({max_chunk_size}) sein"
            )
        
        if overlap_size >= min_chunk_size:
            raise ValueError(
                f"overlap_size ({overlap_size}) muss kleiner als "
                f"min_chunk_size ({min_chunk_size}) sein"
            )
        
        self._min_size = min_chunk_size
        self._max_size = max_chunk_size
        self._overlap = overlap_size
    
    def chunk_cv(self, cv_model: CVModel) -> List[Chunk]:
        """
        Hauptmethode: Konvertiert CVModel in List[Chunk].
        
        Verarbeitet alle CV-Sections und erstellt eine Liste von
        semantisch sinnvollen Chunks mit vollständigen Metadaten.
        
        Args:
            cv_model: Validiertes CVModel (aus CV Parser)
        
        Returns:
            List[Chunk]: Liste von Chunks mit Metadaten
        
        Raises:
            ValueError: Wenn cv_model invalid oder leer
        """
        if not cv_model:
            raise ValueError("cv_model darf nicht None sein")
        
        chunks: List[Chunk] = []
        char_position = 0  # Track position im Original-Dokument
        
        # 1. Berufserfahrung (List[WorkExperience])
        for idx, exp in enumerate(cv_model.berufserfahrung):
            section_title = f"{exp.position} | {exp.company}"
            section_text = self._serialize_work_experience(exp)
            
            section_chunks = self._chunk_section(
                section_text=section_text,
                section_type="experience",
                section_title=section_title,
                section_index=idx,
                char_position=char_position
            )
            
            chunks.extend(section_chunks)
            char_position += len(section_text)
        
        # 2. Skills (Dict[str, List[str]])
        if cv_model.skills:
            skills_text = self._serialize_skills(cv_model.skills)
            section_chunks = self._chunk_section(
                section_text=skills_text,
                section_type="skills",
                section_title="Skills",
                section_index=0,
                char_position=char_position
            )
            chunks.extend(section_chunks)
            char_position += len(skills_text)
        
        # 3. Bildung (List[Education])
        for idx, edu in enumerate(cv_model.bildung):
            section_title = f"{edu.degree} | {edu.institution}"
            section_text = self._serialize_education(edu)
            
            section_chunks = self._chunk_section(
                section_text=section_text,
                section_type="education",
                section_title=section_title,
                section_index=idx,
                char_position=char_position
            )
            
            chunks.extend(section_chunks)
            char_position += len(section_text)
        
        # 4. Projekte (List[Project])
        for idx, project in enumerate(cv_model.projekte):
            section_title = project.title
            section_text = self._serialize_project(project)
            
            section_chunks = self._chunk_section(
                section_text=section_text,
                section_type="projects",
                section_title=section_title,
                section_index=idx,
                char_position=char_position
            )
            
            chunks.extend(section_chunks)
            char_position += len(section_text)
        
        # 5. Sprachen (List[Language])
        if cv_model.sprachen:
            languages_text = self._serialize_languages(cv_model.sprachen)
            section_chunks = self._chunk_section(
                section_text=languages_text,
                section_type="languages",
                section_title="Sprachen",
                section_index=0,
                char_position=char_position
            )
            chunks.extend(section_chunks)
            char_position += len(languages_text)
        
        # 6. Interessen (Optional[str])
        if cv_model.interessen:
            section_chunks = self._chunk_section(
                section_text=cv_model.interessen,
                section_type="interests",
                section_title="Interessen",
                section_index=0,
                char_position=char_position
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _chunk_section(
        self,
        section_text: str,
        section_type: str,
        section_title: str,
        section_index: int,
        char_position: int
    ) -> List[Chunk]:
        """
        Chunking mit Hybrid Strategy für eine einzelne Section.
        
        Logic:
        1. If len(text) <= max_size → 1 Chunk (Section-basiert)
        2. If len(text) > max_size → Split to Paragraphs (Fallback)
        3. Enforce min_size (verwerfe zu kleine Chunks oder merge)
        
        Args:
            section_text: Section Content als String
            section_type: Section Category (experience, skills, etc.)
            section_title: Section/Position Title
            section_index: Index innerhalb Section Type (0, 1, 2, ...)
            char_position: Start Position im Original-Dokument
        
        Returns:
            List[Chunk]: 1+ Chunks für diese Section
        """
        section_text = section_text.strip()
        
        # Skip zu kleine Sections
        if len(section_text) < self._min_size:
            return []
        
        # PRIMARY STRATEGY: Section-basiert (wenn klein genug)
        if len(section_text) <= self._max_size:
            chunk = self._create_chunk(
                text=section_text,
                section_type=section_type,
                section_title=section_title,
                section_index=section_index,
                sub_index=0,
                char_position=char_position
            )
            return [chunk]
        
        # FALLBACK STRATEGY: Paragraph-basiert (für große Sections)
        paragraphs = self._split_large_section(section_text)
        chunks = []
        current_pos = char_position
        
        for sub_idx, para_text in enumerate(paragraphs):
            if len(para_text.strip()) >= self._min_size:
                chunk = self._create_chunk(
                    text=para_text,
                    section_type=section_type,
                    section_title=section_title,
                    section_index=section_index,
                    sub_index=sub_idx,
                    char_position=current_pos
                )
                chunks.append(chunk)
                current_pos += len(para_text)
        
        return chunks
    
    def _split_large_section(self, text: str) -> List[str]:
        """
        Paragraph-basierter Split für große Sections.
        
        Strategy:
        - Split by \n\n (Markdown paragraph breaks)
        - If paragraph still >max_size → sentence-based split
        - Add overlap_size chars from previous paragraph
        
        Args:
            text: Section Text zu splitten
        
        Returns:
            List[str]: Paragraph-Chunks
        """
        # Split by double newline (Markdown paragraphs)
        raw_paragraphs = text.split('\n\n')
        
        refined_chunks = []
        previous_chunk = ""
        
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Paragraph passt in max_size
            if len(para) <= self._max_size:
                # Add overlap from previous chunk (wenn vorhanden)
                if previous_chunk and self._overlap > 0:
                    overlap_text = previous_chunk[-self._overlap:]
                    chunk_text = overlap_text + "\n" + para
                else:
                    chunk_text = para
                
                refined_chunks.append(chunk_text)
                previous_chunk = para
            else:
                # Paragraph zu groß → Sentence-based split
                sentences = self._split_to_sentences(para)
                current_chunk = ""
                
                for sentence in sentences:
                    # Kann Sentence hinzugefügt werden?
                    if len(current_chunk + " " + sentence) <= self._max_size:
                        current_chunk += (" " if current_chunk else "") + sentence
                    else:
                        # Current chunk speichern (wenn groß genug)
                        if current_chunk and len(current_chunk) >= self._min_size:
                            refined_chunks.append(current_chunk.strip())
                        
                        # Neuer chunk mit overlap
                        if current_chunk and self._overlap > 0:
                            overlap_text = current_chunk[-self._overlap:]
                            current_chunk = overlap_text + " " + sentence
                        else:
                            current_chunk = sentence
                
                # Letzten chunk speichern
                if current_chunk and len(current_chunk.strip()) >= self._min_size:
                    refined_chunks.append(current_chunk.strip())
                    previous_chunk = current_chunk
        
        return refined_chunks
    
    def _create_chunk(
        self,
        text: str,
        section_type: str,
        section_title: str,
        section_index: int,
        sub_index: int,
        char_position: int
    ) -> Chunk:
        """
        Erstellt ein Chunk-Objekt mit allen Metadaten.
        
        Args:
            text: Chunk Text Content
            section_type: Section Category
            section_title: Section/Position Title
            section_index: Index innerhalb Section Type
            sub_index: Sub-Index bei Paragraph-Splits
            char_position: Start Position im Original-Dokument
        
        Returns:
            Chunk: Validiertes Chunk-Objekt
        """
        chunk_id = self._generate_chunk_id(section_type, section_index, sub_index)
        metadata = self._extract_metadata(text, section_type)
        
        return Chunk(
            chunk_id=chunk_id,
            section_type=section_type,
            section_title=section_title,
            text=text.strip(),
            char_start=char_position,
            char_end=char_position + len(text),
            metadata=metadata
        )
    
    def _generate_chunk_id(
        self,
        section_type: str,
        section_index: int,
        sub_index: int = 0
    ) -> str:
        """
        Generiert Unique Chunk ID.
        
        Format: cv_<section>_<index> oder cv_<section>_<index>_<sub>
        
        Args:
            section_type: Section Category (experience, skills, etc.)
            section_index: Index innerhalb Section Type
            sub_index: Sub-Index bei Paragraph-Splits (default: 0)
        
        Returns:
            str: Unique Chunk ID
        
        Example:
            >>> _generate_chunk_id("experience", 0, 0)
            "cv_experience_0"
            >>> _generate_chunk_id("experience", 1, 2)
            "cv_experience_1_2"
        """
        if sub_index == 0:
            return f"cv_{section_type}_{section_index}"
        else:
            return f"cv_{section_type}_{section_index}_{sub_index}"
    
    def _extract_metadata(self, text: str, section_type: str) -> Dict[str, Any]:
        """
        Extrahiert Section-spezifische Metadaten.
        
        Metadata Types:
        - experience: timestamps (Jahr → Recency Score)
        - skills: skill_level (Expert/Advanced/Intermediate)
        - education: degree_type, year
        
        Args:
            text: Chunk Text Content
            section_type: Section Category
        
        Returns:
            Dict[str, Any]: Metadata Dictionary
        """
        metadata: Dict[str, Any] = {}
        
        # 1. EXPERIENCE METADATA: Timestamps & Recency
        if section_type == "experience":
            timestamps = self._extract_timestamps(text)
            if timestamps:
                metadata.update(timestamps)
                # Berechne Recency Score basierend auf End Year
                if 'end_year' in timestamps:
                    metadata['recency_score'] = self._calculate_recency(timestamps['end_year'])
        
        # 2. SKILLS METADATA: Skill Level
        elif section_type == "skills":
            skill_level = self._extract_skill_level(text)
            if skill_level:
                metadata['skill_level'] = skill_level
        
        # 3. EDUCATION METADATA: Degree Type & Year
        elif section_type == "education":
            timestamps = self._extract_timestamps(text)
            if timestamps:
                metadata.update(timestamps)
            
            # Extract Degree Type
            degree_type = self._extract_degree_type(text)
            if degree_type:
                metadata['degree_type'] = degree_type
        
        # 4. PROJECTS METADATA: Category
        elif section_type == "projects":
            if "Kategorie:" in text:
                # Extract category from serialized project
                category_match = re.search(r'Kategorie:\s*(.+)', text)
                if category_match:
                    metadata['category'] = category_match.group(1).strip()
        
        return metadata
    
    def _calculate_recency(self, end_year: int) -> float:
        """
        Berechnet Recency Score basierend auf End Year.
        
        Score: 1.0 (aktuell/recent) → 0.5 (10+ Jahre alt)
        Formula: max(0.5, 1.0 - (years_ago * 0.05))
        
        Args:
            end_year: End Year der Position/Bildung
        
        Returns:
            float: Recency Score zwischen 0.5 und 1.0
        """
        current_year = datetime.now().year
        years_ago = current_year - end_year
        return max(0.5, 1.0 - (years_ago * 0.05))
    
    def _extract_timestamps(self, text: str) -> Dict[str, int]:
        """
        Extrahiert Timestamps (Jahre) aus Text.
        
        Patterns:
        - "2022 - Heute" → start_year: 2022, end_year: 2026 (current)
        - "März 2022 - Februar 2024" → start_year: 2022, end_year: 2024
        - "2018" → start_year: 2018, end_year: 2018
        
        Args:
            text: Text mit Zeitangaben
        
        Returns:
            Dict mit start_year und end_year (wenn gefunden)
        """
        timestamps = {}
        
        # Pattern 1: "YYYY - Heute/heute/Present"
        pattern1 = r'(\d{4})\s*[-–]\s*(?:Heute|heute|Present)'
        match1 = re.search(pattern1, text)
        if match1:
            timestamps['start_year'] = int(match1.group(1))
            timestamps['end_year'] = datetime.now().year
            return timestamps
        
        # Pattern 2: "Monat YYYY - Monat YYYY"
        pattern2 = r'\w+\s+(\d{4})\s*[-–]\s*\w+\s+(\d{4})'
        match2 = re.search(pattern2, text)
        if match2:
            timestamps['start_year'] = int(match2.group(1))
            timestamps['end_year'] = int(match2.group(2))
            return timestamps
        
        # Pattern 3: "YYYY - YYYY"
        pattern3 = r'(\d{4})\s*[-–]\s*(\d{4})'
        match3 = re.search(pattern3, text)
        if match3:
            timestamps['start_year'] = int(match3.group(1))
            timestamps['end_year'] = int(match3.group(2))
            return timestamps
        
        # Pattern 4: Einzelnes Jahr "YYYY"
        pattern4 = r'\b(\d{4})\b'
        match4 = re.search(pattern4, text)
        if match4:
            year = int(match4.group(1))
            # Nur plausible Jahre (19xx oder 20xx)
            if 1900 <= year <= 2100:
                timestamps['start_year'] = year
                timestamps['end_year'] = year
                return timestamps
        
        return timestamps
    
    def _extract_skill_level(self, text: str) -> str:
        """
        Extrahiert Skill Level aus Skills-Text.
        
        Levels: expert, advanced, intermediate, basic
        
        Args:
            text: Skills Text
        
        Returns:
            str: Skill Level (lowercase) oder empty string
        """
        text_lower = text.lower()
        
        # Prüfe in Reihenfolge (spezifischste zuerst)
        if 'expert' in text_lower or 'experte' in text_lower:
            return 'expert'
        elif 'advanced' in text_lower or 'fortgeschritten' in text_lower:
            return 'advanced'
        elif 'intermediate' in text_lower or 'mittel' in text_lower:
            return 'intermediate'
        elif 'basic' in text_lower or 'grundkenntnisse' in text_lower:
            return 'basic'
        
        return ''
    
    def _extract_degree_type(self, text: str) -> str:
        """
        Extrahiert Degree Type aus Education-Text.
        
        Types: master, bachelor, diploma, phd, etc.
        
        Args:
            text: Education Text
        
        Returns:
            str: Degree Type (lowercase) oder empty string
        """
        text_lower = text.lower()
        
        # Prüfe gängige deutsche Abschlüsse
        if 'm.sc.' in text_lower or 'master' in text_lower:
            return 'master'
        elif 'b.sc.' in text_lower or 'bachelor' in text_lower:
            return 'bachelor'
        elif 'diplom' in text_lower or 'diploma' in text_lower:
            return 'diploma'
        elif 'dr.' in text_lower or 'phd' in text_lower or 'promotion' in text_lower:
            return 'phd'
        elif 'staatsexamen' in text_lower:
            return 'staatsexamen'
        
        return ''
    
    # ============================================================
    # SERIALIZATION METHODS (Pydantic Model → String)
    # ============================================================
    
    def _serialize_work_experience(self, exp: WorkExperience) -> str:
        """
        Serialisiert WorkExperience Model zu vollständigem Text.
        
        Args:
            exp: WorkExperience Pydantic Model
        
        Returns:
            str: Formatierter Text für Chunking
        """
        parts = [
            f"Position: {exp.position}",
            f"Firma: {exp.company}",
            f"Zeitraum: {exp.zeitraum}"
        ]
        
        if exp.standort:
            parts.append(f"Standort: {exp.standort}")
        
        if exp.technologien:
            parts.append(f"Technologien: {exp.technologien}")
        
        if exp.hauptverantwortlichkeiten:
            parts.append(f"\nHauptverantwortlichkeiten:\n{exp.hauptverantwortlichkeiten}")
        
        if exp.schluessel_projekte:
            parts.append(f"\nSchlüsselprojekte:\n{exp.schluessel_projekte}")
        
        return "\n".join(parts)
    
    def _serialize_skills(self, skills: Dict[str, List[str]]) -> str:
        """
        Serialisiert Skills Dictionary zu Text.
        
        Args:
            skills: Dict[str, List[str]] — Skills kategorisiert
        
        Returns:
            str: Formatierter Skills Text
        """
        parts = []
        
        for category, skill_list in skills.items():
            if skill_list:
                skills_str = ", ".join(skill_list)
                parts.append(f"{category}: {skills_str}")
        
        return "\n".join(parts)
    
    def _serialize_education(self, edu: Education) -> str:
        """
        Serialisiert Education Model zu Text.
        
        Args:
            edu: Education Pydantic Model
        
        Returns:
            str: Formatierter Education Text
        """
        parts = [
            f"Abschluss: {edu.degree}",
            f"Institution: {edu.institution}",
            f"Zeitraum: {edu.zeitraum}"
        ]
        
        if edu.schwerpunkt:
            parts.append(f"Schwerpunkt: {edu.schwerpunkt}")
        
        if edu.note:
            parts.append(f"Note: {edu.note}")
        
        return "\n".join(parts)
    
    def _serialize_project(self, project: Project) -> str:
        """
        Serialisiert Project Model zu Text.
        
        Args:
            project: Project Pydantic Model
        
        Returns:
            str: Formatierter Project Text
        """
        parts = [f"Projekt: {project.title}"]
        
        if project.category:
            parts.append(f"Kategorie: {project.category}")
        
        parts.append(f"Beschreibung: {project.description}")
        
        return "\n".join(parts)
    
    def _serialize_languages(self, languages: List[Language]) -> str:
        """
        Serialisiert Languages List zu Text.
        
        Args:
            languages: List[Language] — Sprachkenntnisse
        
        Returns:
            str: Formatierter Languages Text
        """
        parts = []
        
        for lang in languages:
            parts.append(f"{lang.language}: {lang.level}")
        
        return "\n".join(parts)
    
    def _split_to_sentences(self, text: str) -> List[str]:
        """
        Splittet Text in Sätze (einfache Heuristik).
        
        Strategy:
        - Split by '. ' (Punkt + Leerzeichen)
        - Berücksichtigt gängige Abkürzungen (z.B., u.a., etc.)
        
        Args:
            text: Text zu splitten
        
        Returns:
            List[str]: Liste von Sätzen
        """
        # Einfache Sentence-Split Heuristik
        # Berücksichtigt gängige deutsche Abkürzungen
        
        # Schütze Abkürzungen temporär
        protected_text = text.replace("z.B.", "z_B_")
        protected_text = protected_text.replace("u.a.", "u_a_")
        protected_text = protected_text.replace("etc.", "etc_")
        protected_text = protected_text.replace("M.Sc.", "M_Sc_")
        protected_text = protected_text.replace("B.Sc.", "B_Sc_")
        protected_text = protected_text.replace("Dr.", "Dr_")
        
        # Split by '. ' oder '.\n'
        sentences = re.split(r'\.\s+|\.\n', protected_text)
        
        # Restauriere Abkürzungen und normalisiere
        sentences = [
            s.replace("z_B_", "z.B.")
             .replace("u_a_", "u.a.")
             .replace("etc_", "etc.")
             .replace("M_Sc_", "M.Sc.")
             .replace("B_Sc_", "B.Sc.")
             .replace("Dr_", "Dr.")
             .strip()
            for s in sentences
            if s.strip()
        ]
        
        # Füge Punkt wieder hinzu (außer letzter Satz)
        normalized_sentences = []
        for i, sent in enumerate(sentences):
            if i < len(sentences) - 1 and not sent.endswith('.'):
                normalized_sentences.append(sent + ".")
            else:
                normalized_sentences.append(sent)
        
        return normalized_sentences
