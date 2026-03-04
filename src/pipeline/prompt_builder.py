"""
Prompt Builder Module

Verantwortung: Füllt Prompt Templates mit konkreten Daten
Compliance: SOLID Principles, Security (Input Sanitization)
"""

from typing import Dict, Any, List
from src.models.cv import CVModel
from src.models.job_ad import JobAdModel
from src.pipeline.prompt_loader import PromptTemplate


class PromptBuildError(Exception):
    """Custom Exception für Prompt Building Errors"""
    pass


class PromptBuilder:
    """
    Baut vollständige Prompts aus Templates und Daten.
    
    Design Principles:
    - Single Responsibility: Nur Template Injection
    - Security: Input Sanitization gegen Injection
    - Type Safety: Pydantic Models als Input
    """
    
    def __init__(self, max_text_length: int = 10000):
        """
        Initialize PromptBuilder.
        
        Args:
            max_text_length: Max Länge für einzelne Text-Felder (Security)
        """
        self.max_text_length = max_text_length
    
    def build_cv_generation_prompt(
        self,
        cv: CVModel,
        job_ad: JobAdModel,
        system_prompt_template: PromptTemplate,
        cv_generation_template: PromptTemplate
    ) -> Dict[str, str]:
        """
        Baue CV Generation Prompt aus Templates und Daten.
        
        Args:
            cv: Parsed CV Model
            job_ad: Parsed Job Ad Model
            system_prompt_template: System Prompt Template
            cv_generation_template: CV Generation Template
        
        Returns:
            Dict mit "system" und "user" prompts
        
        Raises:
            PromptBuildError: Wenn Template Variablen fehlen
        """
        # Check if using simplified template (v0.1.0-minimal)
        template_id = cv_generation_template.prompt_id
        use_simplified = "minimal" in template_id or "simple" in template_id
        
        # Extract CV data (simplified or full)
        if use_simplified:
            cv_data = self._extract_cv_data_simple(cv)
        else:
            cv_data = self._extract_cv_data(cv)
        
        # Extract Job Ad requirements
        job_data = self._extract_job_data(job_ad)
        
        # Build System Prompt (usually static, but validate)
        system_prompt = system_prompt_template.system_prompt
        
        # Build User Prompt (inject variables)
        user_prompt = self._inject_variables(
            cv_generation_template.user_prompt_template,
            {
                **cv_data,
                **job_data
            }
        )
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }
    
    def build_cover_letter_prompt(
        self,
        cv: CVModel,
        job_ad: JobAdModel,
        system_prompt_template: PromptTemplate,
        cover_letter_template: PromptTemplate,
        retrieved_chunks: str | None = None
    ) -> Dict[str, str]:
        """
        Baue Cover Letter Prompt aus Templates und Daten.
        
        Args:
            cv: Parsed CV Model
            job_ad: Parsed Job Ad Model
            system_prompt_template: System Prompt Template
            cover_letter_template: Cover Letter Template
        
        Returns:
            Dict mit "system" und "user" prompts
        """
        # Check if using simplified template
        template_id = cover_letter_template.prompt_id
        use_simplified = "minimal" in template_id or "simple" in template_id
        
        # Extract CV data (simplified or full)
        if use_simplified:
            cv_data = self._extract_cv_data_simple(cv)
        else:
            cv_data = self._extract_cv_data(cv)
            
        job_data = self._extract_job_data(job_ad)
        
        system_prompt = system_prompt_template.system_prompt
        
        user_prompt = self._inject_variables(
            cover_letter_template.user_prompt_template,
            {
                **cv_data,
                **job_data,
                "retrieved_chunks": self._sanitize(retrieved_chunks or "")
            }
        )
        
        return {
            "system": system_prompt,
            "user": user_prompt
        }

    def format_retrieved_chunks(self, retrieval_results: List[Any]) -> str:
        """
        Formatiere Retrieval Results für Prompt Injection.

        Args:
            retrieval_results: Liste von RetrievalResult

        Returns:
            String mit kompaktem Chunk-Listing
        """
        if not retrieval_results:
            return "Keine Retrieval-Ergebnisse verfügbar."

        lines = []
        for result in retrieval_results:
            requirement_text = getattr(result.requirement, "text", "")
            requirement_id = getattr(result.requirement, "requirement_id", "")
            lines.append(f"- Requirement: {requirement_text} ({requirement_id})")

            for chunk, score in result.retrieved_chunks:
                preview = chunk.text[:180] + "..." if len(chunk.text) > 180 else chunk.text
                lines.append(
                    f"  - {chunk.chunk_id} | {chunk.section_type} | {score:.2f} | {preview}"
                )

        return "\n".join(lines)
    
    def _extract_cv_data(self, cv: CVModel) -> Dict[str, str]:
        """
        Extrahiere CV Daten für Template Injection.
        
        Args:
            cv: CVModel
        
        Returns:
            Dict mit Template-Variablen
        """
        # Berufserfahrung als formatted string
        experience_text = self._format_experience(cv.berufserfahrung)
        
        # Skills als formatted string
        skills_text = self._format_skills(cv.skills)
        
        # Bildung als formatted string
        education_text = self._format_education(cv.bildung)
        
        # Projekte (optional)
        projects_text = self._format_projects(cv.projekte) if cv.projekte else ""
        
        # Sprachen (optional)
        languages_text = self._format_languages(cv.sprachen) if cv.sprachen else ""
        
        # Personal Info zusammenstellen
        personal_info_parts = [cv.name]
        if cv.email:
            personal_info_parts.append(cv.email)
        if cv.phone:
            personal_info_parts.append(cv.phone)
        if cv.location:
            personal_info_parts.append(cv.location)
        personal_info = " | ".join(personal_info_parts)
        
        return {
            "candidate_name": self._sanitize(cv.name),
            "candidate_email": self._sanitize(cv.email),
            "candidate_phone": self._sanitize(cv.phone or ""),
            "candidate_location": self._sanitize(cv.location or ""),
            "candidate_personal_info": self._sanitize(personal_info),
            "profile_summary": self._sanitize(cv.profile_summary or ""),
            "experience_section": self._sanitize(experience_text),
            "candidate_experience": self._sanitize(experience_text),  # Alias für Template-Kompatibilität
            "skills_section": self._sanitize(skills_text),
            "candidate_skills": self._sanitize(skills_text),  # Alias für Template-Kompatibilität
            "education_section": self._sanitize(education_text),
            "candidate_education": self._sanitize(education_text),  # Alias für Template-Kompatibilität
            "projects_section": self._sanitize(projects_text),
            "candidate_projects": self._sanitize(projects_text),  # Alias für Template-Kompatibilität
            "languages": self._sanitize(languages_text),
            "candidate_languages": self._sanitize(languages_text)  # Alias für Template-Kompatibilität
        }
    
    def _extract_cv_data_simple(self, cv: CVModel) -> Dict[str, str]:
        """
        Simplified CV extraction for M1-Minimal templates.
        
        Flattens all CV data into a single summary string for easier template injection.
        Used by v0.1.0-minimal prompts.
        
        Args:
            cv: CVModel
        
        Returns:
            Dict with minimal template variables (candidate_summary only)
        """
        # Build comprehensive summary string
        summary_parts = []
        
        # Personal Info Header
        summary_parts.append(f"Name: {cv.name}")
        summary_parts.append(f"Kontakt: {cv.email}")
        if cv.phone:
            summary_parts.append(f"Telefon: {cv.phone}")
        if cv.location:
            summary_parts.append(f"Standort: {cv.location}")
        summary_parts.append("")  # Blank line
        
        # Profile Summary
        if cv.profile_summary:
            summary_parts.append(f"Profil: {cv.profile_summary}")
            summary_parts.append("")
        
        # Berufserfahrung (Top 3 positions)
        summary_parts.append("Berufserfahrung:")
        for i, exp in enumerate(cv.berufserfahrung[:3], 1):
            summary_parts.append(f"{i}. {exp.position} @ {exp.company} ({exp.zeitraum})")
            if exp.technologien:
                summary_parts.append(f"   Technologien: {exp.technologien}")
            if exp.hauptverantwortlichkeiten:
                # Take first 200 chars only
                responsibilities = exp.hauptverantwortlichkeiten[:200]
                summary_parts.append(f"   Details: {responsibilities}...")
        summary_parts.append("")
        
        # Skills (flatten all categories, top 15 skills)
        all_skills = []
        for category, skill_list in cv.skills.items():
            all_skills.extend(skill_list)
        summary_parts.append(f"Skills: {', '.join(all_skills[:15])}")
        summary_parts.append("")
        
        # Bildung (highest degree only)
        if cv.bildung:
            edu = cv.bildung[0]  # Most recent
            summary_parts.append(f"Bildung: {edu.degree}, {edu.institution} ({edu.zeitraum})")
            summary_parts.append("")
        
        # Sprachen (if any)
        if cv.sprachen:
            langs = [f"{lang.language} ({lang.level})" for lang in cv.sprachen]
            summary_parts.append(f"Sprachen: {', '.join(langs)}")
        
        summary_text = "\n".join(summary_parts)
        
        return {
            "candidate_summary": self._sanitize(summary_text)
        }
    
    def _extract_job_data(self, job_ad: JobAdModel) -> Dict[str, str]:
        """
        Extrahiere Job Ad Daten für Template Injection.
        
        Args:
            job_ad: JobAdModel
        
        Returns:
            Dict mit Template-Variablen
        """
        # Requirements als structured list
        requirements_text = self._format_requirements(job_ad)
        
        # Critical, Important und Nice-to-Have requirements separat extrahieren
        critical_reqs = ", ".join(job_ad.hard_skills.critical) if job_ad.hard_skills and job_ad.hard_skills.critical else ""
        important_reqs = ", ".join(job_ad.hard_skills.important) if job_ad.hard_skills and job_ad.hard_skills.important else ""
        nice_to_have_reqs = ", ".join(job_ad.hard_skills.nice_to_have) if job_ad.hard_skills and job_ad.hard_skills.nice_to_have else ""
        
        return {
            "job_title": self._sanitize(job_ad.job_title),
            "company": self._sanitize(job_ad.company),
            "company_name": self._sanitize(job_ad.company),  # Alias für Template-Kompatibilität
            "location": self._sanitize(job_ad.location or ""),
            "job_requirements": self._sanitize(requirements_text),
            "critical_requirements": self._sanitize(critical_reqs),
            "important_requirements": self._sanitize(important_reqs),
            "nice_to_have_requirements": self._sanitize(nice_to_have_reqs),
            "job_description": self._sanitize(getattr(job_ad, 'description', '') or ""),
            "benefits": self._sanitize(getattr(job_ad, 'benefits', '') or ""),
            "tech_stack": self._sanitize(getattr(job_ad, 'tech_stack', '') or "")
        }
    
    def _format_experience(self, experiences: list) -> str:
        """Format Berufserfahrung als Text"""
        if not experiences:
            return "Keine Berufserfahrung angegeben."
        
        formatted = []
        for exp in experiences:
            exp_text = f"""
Position: {exp.position}
            Firma: {exp.company}
Zeitraum: {exp.zeitraum}
Hauptverantwortlichkeiten: {exp.hauptverantwortlichkeiten or 'Nicht angegeben'}
"""
            formatted.append(exp_text.strip())
        
        return "\n\n".join(formatted)
    
    def _format_skills(self, skills: Dict[str, list[str]]) -> str:
        """Format Skills als Text (skills is Dict[str, List[str]])"""
        if not skills:
            return "Keine Skills angegeben."
        
        # Format: "Category: skill1, skill2 | Category2: skill3, skill4"
        formatted = []
        for category, skill_list in skills.items():
            if skill_list:
                formatted.append(f"{category.title()}: {', '.join(skill_list)}")
        
        return " | ".join(formatted) if formatted else "Keine Skills angegeben."
    
    def _format_education(self, education: list) -> str:
        """Format Bildung als Text"""
        if not education:
            return "Keine Bildung angegeben."
        
        formatted = []
        for edu in education:
            edu_text = f"{edu.degree} | {edu.institution} | {edu.zeitraum}"
            formatted.append(edu_text)
        
        return "\n".join(formatted)
    
    def _format_projects(self, projects: list) -> str:
        """Format Projekte als Text"""
        if not projects:
            return ""
        
        formatted = []
        for proj in projects:
            proj_text = f"Projekt: {proj.title}\nBeschreibung: {proj.description}"
            if proj.category:
                proj_text += f"\nKategorie: {proj.category}"
            formatted.append(proj_text)
        
        return "\n\n".join(formatted)
    
    def _format_languages(self, languages: list) -> str:
        """Format Sprachkenntnisse als Text"""
        if not languages:
            return ""
        
        formatted = []
        for lang in languages:
            formatted.append(f"{lang.language}: {lang.level}")
        
        return " | ".join(formatted)
    
    def _format_requirements(self, job_ad: JobAdModel) -> str:
        """Format Job Requirements als strukturierte Liste"""
        parts = []
        
        # Hard Skills
        if job_ad.hard_skills:
            parts.append("### Fachliche Anforderungen (Hard Skills):\n")
            
            if job_ad.hard_skills.critical:
                parts.append("**Kritisch (Muss):**")
                parts.append(", ".join(job_ad.hard_skills.critical))
                parts.append("\n")
            
            if job_ad.hard_skills.important:
                parts.append("**Wichtig (Sollte):**")
                parts.append(", ".join(job_ad.hard_skills.important))
                parts.append("\n")
            
            if job_ad.hard_skills.nice_to_have:
                parts.append("**Nice-to-Have (Kann):**")
                parts.append(", ".join(job_ad.hard_skills.nice_to_have))
                parts.append("\n")
        
        # Soft Skills
        if job_ad.soft_skills:
            parts.append("\n### Persönliche Anforderungen (Soft Skills):\n")
            
            if job_ad.soft_skills.critical:
                parts.append("**Kritisch (Muss):**")
                parts.append(", ".join(job_ad.soft_skills.critical))
                parts.append("\n")
            
            if job_ad.soft_skills.important:
                parts.append("**Wichtig (Sollte):**")
                parts.append(", ".join(job_ad.soft_skills.important))
                parts.append("\n")
        
        # Experience (check if field exists)
        if hasattr(job_ad, 'experience') and job_ad.experience:
            parts.append(f"\n### Berufserfahrung:\n{job_ad.experience}")
        
        return "".join(parts)
    
    def _inject_variables(
        self, 
        template: str, 
        variables: Dict[str, str]
    ) -> str:
        """
        Injiziere Variablen in Template (sicher, escaped).
        
        Args:
            template: Template string mit {variable} Platzhaltern
            variables: Dict mit Variablen-Werten
        
        Returns:
            Gefülltes Template
        
        Raises:
            PromptBuildError: Wenn Variablen fehlen
        """
        try:
            # Python format() für Template Injection
            return template.format(**variables)
        except KeyError as e:
            raise PromptBuildError(
                f"Missing template variable: {e}\n"
                f"Available variables: {list(variables.keys())}"
            )
        except Exception as e:
            raise PromptBuildError(
                f"Failed to inject variables: {e}"
            )
    
    def _sanitize(self, text: str) -> str:
        """
        Sanitize User Input gegen Injection Attacks.
        
        Security Measures:
        - Truncate zu lange Texte
        - Escape gefährliche Zeichen
        - Remove Control Characters
        
        Args:
            text: Input text
        
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Truncate if too long
        if len(text) > self.max_text_length:
            text = text[:self.max_text_length] + "... [gekürzt]"
        
        # Escape Code Block Markers (Prompt Injection Protection)
        text = text.replace("```", "'''")
        
        # Escape Template Markers
        text = text.replace("{", "{{").replace("}", "}}")
        
        return text


def create_prompt_builder() -> PromptBuilder:
    """
    Factory function for PromptBuilder.
    
    Returns:
        Configured PromptBuilder instance
    """
    return PromptBuilder()
