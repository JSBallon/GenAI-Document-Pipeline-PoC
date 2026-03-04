"""
Output Validator Module

Verantwortung: Validierung generierter Outputs (Länge, Format, Qualität)
Compliance: SOLID Principles, Single Responsibility
"""

import re
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity Levels für Validation Issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Einzelnes Validation Issue"""
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of Output Validation"""
    is_valid: bool
    word_count: int
    issues: List[ValidationIssue] = []
    warnings: List[str] = []
    
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues"""
        return any(
            issue.severity == ValidationSeverity.CRITICAL 
            for issue in self.issues
        )
    
    def has_errors(self) -> bool:
        """Check if there are errors"""
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )


class OutputValidator:
    """
    Validiert generierte CV/Anschreiben Outputs.
    
    Design Principles:
    - Single Responsibility: Nur Validation
    - Configurable Rules: Limits via Constructor
    - Comprehensive Checks: Länge, Format, Content
    
    Validation Checks:
    1. Word Count (min/max bounds)
    2. Section Structure (required headers)
    3. Content Quality (not empty, not too short)
    4. Language Detection (optional)
    """
    
    def __init__(
        self,
        cv_min_words: int = 400,
        cv_max_words: int = 700,
        cover_letter_min_words: int = 250,
        cover_letter_max_words: int = 450
    ):
        """
        Initialize OutputValidator.
        
        Args:
            cv_min_words: Minimum word count for CV
            cv_max_words: Maximum word count for CV
            cover_letter_min_words: Minimum word count for Cover Letter
            cover_letter_max_words: Maximum word count for Cover Letter
        """
        self.cv_min_words = cv_min_words
        self.cv_max_words = cv_max_words
        self.cover_letter_min_words = cover_letter_min_words
        self.cover_letter_max_words = cover_letter_max_words
    
    def validate_cv(self, cv_markdown: str) -> ValidationResult:
        """
        Validate generated CV.
        
        Args:
            cv_markdown: Generated CV (Markdown format)
        
        Returns:
            ValidationResult mit issues und warnings
        
        Example:
            >>> validator = OutputValidator()
            >>> result = validator.validate_cv(cv_text)
            >>> if not result.is_valid:
            ...     print("Validation failed:", result.issues)
        """
        issues = []
        warnings = []
        
        # Count words
        word_count = self._count_words(cv_markdown)
        
        # Check word count bounds
        if word_count < self.cv_min_words:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"CV ist zu kurz ({word_count} Wörter)",
                field="word_count",
                actual_value=str(word_count),
                expected_value=f"mindestens {self.cv_min_words}"
            ))
        elif word_count > self.cv_max_words:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"CV ist sehr lang ({word_count} Wörter)",
                field="word_count",
                actual_value=str(word_count),
                expected_value=f"maximal {self.cv_max_words}"
            ))
        
        # Check for required sections (Markdown headers)
        required_sections = self._check_required_sections(
            cv_markdown,
            expected_sections=["Berufserfahrung", "Skills", "Bildung"]
        )
        
        if required_sections:
            for section in required_sections:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    message=f"Empfohlene Section fehlt: {section}",
                    field="sections"
                ))
        
        # Check for empty content
        if len(cv_markdown.strip()) < 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message="CV ist praktisch leer (< 100 Zeichen)",
                field="content"
            ))
        
        # Check for broken markdown syntax
        broken_syntax = self._check_markdown_syntax(cv_markdown)
        if broken_syntax:
            warnings.extend(broken_syntax)
        
        # Determine overall validity
        is_valid = not any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            word_count=word_count,
            issues=issues,
            warnings=warnings
        )
    
    def validate_cover_letter(self, cover_letter_markdown: str) -> ValidationResult:
        """
        Validate generated Cover Letter.
        
        Args:
            cover_letter_markdown: Generated Cover Letter (Markdown)
        
        Returns:
            ValidationResult
        """
        issues = []
        warnings = []
        
        # Count words
        word_count = self._count_words(cover_letter_markdown)
        
        # Check word count bounds
        if word_count < self.cover_letter_min_words:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Anschreiben ist zu kurz ({word_count} Wörter)",
                field="word_count",
                actual_value=str(word_count),
                expected_value=f"mindestens {self.cover_letter_min_words}"
            ))
        elif word_count > self.cover_letter_max_words:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Anschreiben ist sehr lang ({word_count} Wörter)",
                field="word_count",
                actual_value=str(word_count),
                expected_value=f"maximal {self.cover_letter_max_words}"
            ))
        
        # Check for empty content
        if len(cover_letter_markdown.strip()) < 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message="Anschreiben ist praktisch leer (< 100 Zeichen)",
                field="content"
            ))
        
        # Check for salutation
        if not self._has_salutation(cover_letter_markdown):
            warnings.append("Keine erkennbare Anrede gefunden (z.B. 'Sehr geehrte')")
        
        # Check for closing
        if not self._has_closing(cover_letter_markdown):
            warnings.append("Kein erkennbarer Grußformel gefunden (z.B. 'Mit freundlichen Grüßen')")
        
        # Check markdown syntax
        broken_syntax = self._check_markdown_syntax(cover_letter_markdown)
        if broken_syntax:
            warnings.extend(broken_syntax)
        
        # Determine validity
        is_valid = not any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in issues
        )
        
        return ValidationResult(
            is_valid=is_valid,
            word_count=word_count,
            issues=issues,
            warnings=warnings
        )
    
    def _count_words(self, text: str) -> int:
        """
        Count words in text (German language aware).
        
        Args:
            text: Text to count
        
        Returns:
            Word count
        """
        # Remove Markdown syntax
        clean_text = re.sub(r'[#*_`\[\]()]', ' ', text)
        
        # Split by whitespace
        words = clean_text.split()
        
        # Filter out very short tokens (likely symbols)
        words = [w for w in words if len(w) > 1]
        
        return len(words)
    
    def _check_required_sections(
        self, 
        markdown: str, 
        expected_sections: List[str]
    ) -> List[str]:
        """
        Check if expected sections (headers) are present.
        
        Args:
            markdown: Markdown text
            expected_sections: List of expected section names
        
        Returns:
            List of missing sections
        """
        missing = []
        
        # Find all headers (## Header or # Header)
        headers = re.findall(r'^#{1,3}\s+(.+)$', markdown, re.MULTILINE)
        header_text = ' '.join(headers).lower()
        
        for section in expected_sections:
            # Check if section name appears in any header
            if section.lower() not in header_text:
                missing.append(section)
        
        return missing
    
    def _check_markdown_syntax(self, markdown: str) -> List[str]:
        """
        Check for broken Markdown syntax.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for unmatched code blocks
        code_blocks = markdown.count("```")
        if code_blocks % 2 != 0:
            warnings.append("Unvollständige Code-Blöcke gefunden (``` nicht gepaart)")
        
        # Check for unmatched bold
        bold_markers = markdown.count("**")
        if bold_markers % 2 != 0:
            warnings.append("Unvollständige Bold-Markup gefunden (** nicht gepaart)")
        
        return warnings
    
    def _has_salutation(self, text: str) -> bool:
        """Check if text contains a German salutation"""
        salutations = [
            r"sehr geehrte",
            r"liebe[r]?\s",
            r"hallo\s",
            r"guten tag"
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in salutations)
    
    def _has_closing(self, text: str) -> bool:
        """Check if text contains a German closing formula"""
        closings = [
            r"mit freundlichen grüßen",
            r"freundliche grüße",
            r"hochachtungsvoll",
            r"mit besten grüßen",
            r"beste grüße"
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in closings)


def create_output_validator(
    cv_min_words: int = 400,
    cv_max_words: int = 700,
    cover_letter_min_words: int = 250,
    cover_letter_max_words: int = 450
) -> OutputValidator:
    """
    Factory function for OutputValidator.
    
    Args:
        cv_min_words: Minimum CV word count
        cv_max_words: Maximum CV word count
        cover_letter_min_words: Minimum Cover Letter word count
        cover_letter_max_words: Maximum Cover Letter word count
    
    Returns:
        Configured OutputValidator instance
    """
    return OutputValidator(
        cv_min_words=cv_min_words,
        cv_max_words=cv_max_words,
        cover_letter_min_words=cover_letter_min_words,
        cover_letter_max_words=cover_letter_max_words
    )
