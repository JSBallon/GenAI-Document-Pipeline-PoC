"""
Requirement Extraction aus Job Advertisements.

Extrahiert strukturierte Requirements aus JobAdModel für RAG-basiertes Skill Matching.
Folgt OOP/SOLID Principles: Single Responsibility, Dependency Injection, Explicit Design.

Design Pattern: Strategy Pattern für verschiedene Extraction-Methoden
- SimpleExtractor: Nutzt strukturierte YAML-Daten aus JobAdModel
- LLMExtractor: Future - LLM-basierte Extraction aus Freitext (M2 optional)
"""

import logging
from typing import List, Optional
from datetime import datetime

from src.models.job_ad import JobAdModel
from src.rag.models import (
    Requirement,
    RequirementExtractionResult
)


logger = logging.getLogger(__name__)


class SimpleRequirementExtractor:
    """
    Einfacher Requirement Extractor für strukturierte JobAds.
    
    Nutzt die bereits strukturierten Daten aus dem JobAdModel
    (YAML Frontmatter) und konvertiert sie in Requirement-Objekte
    für das RAG-System.
    
    Responsibilities:
    - Konvertierung von JobAdModel → List[Requirement]
    - Generierung eindeutiger Requirement IDs
    - Kategorisierung (hard_skill, soft_skill, education)
    - Prioritäts-Mapping (critical, important, nice_to_have)
    
    Attributes:
        _extraction_count: Counter für generierte Requirement IDs
    """
    
    def __init__(self):
        """Initialize SimpleRequirementExtractor."""
        self._extraction_count = 0
        logger.info("SimpleRequirementExtractor initialized")
    
    def extract(
        self,
        job_ad: JobAdModel,
        job_id: Optional[str] = None
    ) -> RequirementExtractionResult:
        """
        Extrahiere Requirements aus strukturiertem JobAdModel.
        
        Args:
            job_ad: Parsed JobAdModel mit strukturierten Requirements
            job_id: Optional Job Advertisement ID für Tracking
        
        Returns:
            RequirementExtractionResult mit extrahierten Requirements
        
        Raises:
            ValueError: Wenn JobAd keine Hard Skills enthält
        
        Example:
            >>> extractor = SimpleRequirementExtractor()
            >>> result = extractor.extract(job_ad)
            >>> print(f"Extracted {result.total_count} requirements")
            >>> print(f"Critical: {len(result.critical_requirements)}")
        """
        logger.info(f"Starting requirement extraction for job: {job_ad.job_title}")
        
        requirements: List[Requirement] = []
        
        # 1. Extract Hard Skills
        requirements.extend(self._extract_hard_skills(job_ad))
        
        # 2. Extract Soft Skills (if present)
        if job_ad.soft_skills:
            requirements.extend(self._extract_soft_skills(job_ad))
        
        # 3. Extract Experience Requirements (if present)
        if job_ad.experience_level:
            requirements.extend(self._extract_experience(job_ad))
        
        # 4. Extract Education Requirements (if present)
        if job_ad.education:
            requirements.extend(self._extract_education(job_ad))
        
        # Create Result
        result = RequirementExtractionResult(
            requirements=requirements,
            source_job_id=job_id or job_ad.job_title,
            extraction_method="simple",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "extractor_version": "1.0.0",
                "job_title": job_ad.job_title,
                "company": job_ad.company
            }
        )
        
        logger.info(
            f"Extraction complete: {result.total_count} requirements "
            f"({len(result.critical_requirements)} critical)"
        )
        
        return result
    
    def _extract_hard_skills(self, job_ad: JobAdModel) -> List[Requirement]:
        """
        Extrahiere Hard Skills aus JobAdModel.
        
        Args:
            job_ad: JobAdModel mit hard_skills Attribut
        
        Returns:
            Liste von Requirement-Objekten für Hard Skills
        """
        requirements = []
        
        # Critical Hard Skills
        for idx, skill in enumerate(job_ad.hard_skills.critical):
            req = Requirement(
                requirement_id=f"req_hard_skill_critical_{idx:03d}",
                text=skill,
                category="hard_skill",
                priority="critical",
                details=f"Critical hard skill for {job_ad.job_title}",
                context=f"Required for {job_ad.job_title} position",
                metadata={
                    "source": "hard_skills.critical",
                    "job_title": job_ad.job_title
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted critical hard skill: {skill}")
        
        # Important Hard Skills
        for idx, skill in enumerate(job_ad.hard_skills.important):
            req = Requirement(
                requirement_id=f"req_hard_skill_important_{idx:03d}",
                text=skill,
                category="hard_skill",
                priority="important",
                details=f"Important hard skill for {job_ad.job_title}",
                context=f"Valuable for {job_ad.job_title} position",
                metadata={
                    "source": "hard_skills.important",
                    "job_title": job_ad.job_title
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted important hard skill: {skill}")
        
        # Nice-to-Have Hard Skills
        for idx, skill in enumerate(job_ad.hard_skills.nice_to_have):
            req = Requirement(
                requirement_id=f"req_hard_skill_nice_{idx:03d}",
                text=skill,
                category="hard_skill",
                priority="nice_to_have",
                details=f"Nice-to-have skill for {job_ad.job_title}",
                context=f"Bonus for {job_ad.job_title} position",
                metadata={
                    "source": "hard_skills.nice_to_have",
                    "job_title": job_ad.job_title
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted nice-to-have hard skill: {skill}")
        
        return requirements
    
    def _extract_soft_skills(self, job_ad: JobAdModel) -> List[Requirement]:
        """
        Extrahiere Soft Skills aus JobAdModel.
        
        Args:
            job_ad: JobAdModel mit soft_skills Attribut
        
        Returns:
            Liste von Requirement-Objekten für Soft Skills
        """
        requirements = []
        
        if not job_ad.soft_skills:
            return requirements
        
        # Critical Soft Skills
        for idx, skill in enumerate(job_ad.soft_skills.critical):
            req = Requirement(
                requirement_id=f"req_soft_skill_critical_{idx:03d}",
                text=skill,
                category="soft_skill",
                priority="critical",
                details=f"Critical soft skill for team fit",
                context=f"Essential for {job_ad.job_title} role",
                metadata={
                    "source": "soft_skills.critical",
                    "job_title": job_ad.job_title
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted critical soft skill: {skill}")
        
        # Important Soft Skills
        for idx, skill in enumerate(job_ad.soft_skills.important):
            req = Requirement(
                requirement_id=f"req_soft_skill_important_{idx:03d}",
                text=skill,
                category="soft_skill",
                priority="important",
                details=f"Important soft skill for collaboration",
                context=f"Valuable for {job_ad.job_title} team",
                metadata={
                    "source": "soft_skills.important",
                    "job_title": job_ad.job_title
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted important soft skill: {skill}")
        
        return requirements
    
    def _extract_experience(self, job_ad: JobAdModel) -> List[Requirement]:
        """
        Extrahiere Experience Requirements aus JobAdModel.
        
        Args:
            job_ad: JobAdModel mit experience_level Attribut
        
        Returns:
            Liste von Requirement-Objekten für Experience
        """
        requirements = []
        
        if not job_ad.experience_level:
            return requirements
        
        # Create Experience Requirement
        req = Requirement(
            requirement_id="req_experience_000",
            text=job_ad.experience_level,
            category="experience",
            priority="critical",  # Experience is usually critical
            details=f"Required experience level for {job_ad.job_title}",
            context=f"{job_ad.job_title} position requirements",
            metadata={
                "source": "experience_level",
                "job_title": job_ad.job_title,
                "raw_value": job_ad.experience_level
            }
        )
        requirements.append(req)
        logger.debug(f"Extracted experience requirement: {job_ad.experience_level}")
        
        return requirements
    
    def _extract_education(self, job_ad: JobAdModel) -> List[Requirement]:
        """
        Extrahiere Education Requirements aus JobAdModel.
        
        Args:
            job_ad: JobAdModel mit education Attribut
        
        Returns:
            Liste von Requirement-Objekten für Education
        """
        requirements = []
        
        if not job_ad.education:
            return requirements
        
        # Preferred Education
        if job_ad.education.preferred:
            req = Requirement(
                requirement_id="req_education_preferred_000",
                text=job_ad.education.preferred,
                category="education",
                priority="important",  # Preferred = important
                details="Preferred educational background",
                context=f"Education requirement for {job_ad.job_title}",
                metadata={
                    "source": "education.preferred",
                    "job_title": job_ad.job_title,
                    "type": "preferred"
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted preferred education: {job_ad.education.preferred}")
        
        # Alternative Education
        if job_ad.education.alternative:
            req = Requirement(
                requirement_id="req_education_alternative_000",
                text=job_ad.education.alternative,
                category="education",
                priority="nice_to_have",  # Alternative = nice-to-have
                details="Alternative educational background",
                context=f"Alternative qualification for {job_ad.job_title}",
                metadata={
                    "source": "education.alternative",
                    "job_title": job_ad.job_title,
                    "type": "alternative"
                }
            )
            requirements.append(req)
            logger.debug(f"Extracted alternative education: {job_ad.education.alternative}")
        
        return requirements
    
    def extract_from_multiple(
        self,
        job_ads: List[JobAdModel]
    ) -> List[RequirementExtractionResult]:
        """
        Batch-Extraktion für mehrere JobAds.
        
        Args:
            job_ads: Liste von JobAdModel-Objekten
        
        Returns:
            Liste von RequirementExtractionResult für jedes JobAd
        
        Example:
            >>> extractor = SimpleRequirementExtractor()
            >>> results = extractor.extract_from_multiple([job1, job2, job3])
            >>> total = sum(r.total_count for r in results)
        """
        logger.info(f"Starting batch extraction for {len(job_ads)} job ads")
        
        results = []
        for idx, job_ad in enumerate(job_ads):
            try:
                result = self.extract(job_ad, job_id=f"job_{idx:03d}")
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to extract requirements from job ad {idx}: {e}")
                # Continue with next job ad
                continue
        
        logger.info(
            f"Batch extraction complete: {len(results)}/{len(job_ads)} successful"
        )
        
        return results
