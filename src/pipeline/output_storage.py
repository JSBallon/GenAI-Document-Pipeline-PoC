"""
[DEPRECATED in M3]
Output Storage Module (temporarily disabled)

Verantwortung: Speichert generierte Outputs mit Metadata und Versioning
Compliance: SOLID Principles, File System Organization

Hinweis: `GeneratedOutput` wurde in M3 entfernt. Dieses Modul wird in M4
auf `GenerationResult` umgestellt und reaktiviert.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
# from src.pipeline.generation_pipeline import GeneratedOutput  # DEPRECATED in M3
from src.pipeline.output_validator import ValidationResult


class StorageError(Exception):
    """Custom Exception für Storage Errors"""
    pass


class OutputStorage:
    """
    Speichert generierte Outputs in strukturiertem File System.
    
    Design Principles:
    - Single Responsibility: Nur File Storage
    - Organized Structure: Timestamp + Trace ID basierte Ordner
    - Metadata Tracking: Alle relevanten Infos in metadata.json
    
    Storage Structure:
    outputs/
      └── YYYY-MM-DD_HH-MM-SS_{trace_id}/
          ├── metadata.json
          ├── cv.md
          ├── cover_letter.md
          ├── validation_results.json
          └── prompts_used.json (optional)
    """
    
    def __init__(self, outputs_base_path: Optional[Path] = None):
        """
        Initialize OutputStorage.
        
        Args:
            outputs_base_path: Base directory für Outputs (default: ./outputs)
        """
        if outputs_base_path is None:
            # Default: Project root/outputs
            project_root = Path(__file__).parent.parent.parent
            outputs_base_path = project_root / "outputs"
        
        self.outputs_base_path = Path(outputs_base_path)
        
        # Create outputs directory if not exists
        self.outputs_base_path.mkdir(parents=True, exist_ok=True)
    
    def save_outputs(
        self,
        generated_output: GeneratedOutput,
        cv_validation: Optional[ValidationResult] = None,
        cover_letter_validation: Optional[ValidationResult] = None
    ) -> Path:
        """
        Speichere generierte Outputs in File System.
        
        Args:
            generated_output: Generated CV + Cover Letter
            cv_validation: Validation Result für CV (optional)
            cover_letter_validation: Validation Result für Cover Letter (optional)
        
        Returns:
            Path zum Output Directory
        
        Raises:
            StorageError: Bei File System Errors
        
        Example:
            >>> storage = OutputStorage()
            >>> output_dir = storage.save_outputs(generated_output)
            >>> print(f"Outputs saved to: {output_dir}")
        """
        try:
            # Create output directory
            output_dir = self._create_output_directory(generated_output)
            
            # Save CV
            cv_path = output_dir / "cv.md"
            self._write_file(cv_path, generated_output.cv_markdown)
            
            # Save Cover Letter
            cover_letter_path = output_dir / "cover_letter.md"
            self._write_file(cover_letter_path, generated_output.cover_letter_markdown)
            
            # Save Metadata
            metadata = self._build_metadata(
                generated_output,
                cv_validation,
                cover_letter_validation
            )
            metadata_path = output_dir / "metadata.json"
            self._write_json(metadata_path, metadata)
            
            # Save Validation Results (if available)
            if cv_validation or cover_letter_validation:
                validation_data = {
                    "cv_validation": cv_validation.dict() if cv_validation else None,
                    "cover_letter_validation": cover_letter_validation.dict() if cover_letter_validation else None
                }
                validation_path = output_dir / "validation_results.json"
                self._write_json(validation_path, validation_data)
            
            return output_dir
            
        except Exception as e:
            raise StorageError(
                f"Failed to save outputs: {e}"
            ) from e
    
    def load_output(self, output_dir: Path) -> Dict:
        """
        Lade gespeicherte Outputs aus Directory.
        
        Args:
            output_dir: Path zum Output Directory
        
        Returns:
            Dict mit cv_markdown, cover_letter_markdown, metadata
        
        Raises:
            StorageError: Wenn Directory nicht existiert oder Files fehlen
        """
        if not output_dir.exists():
            raise StorageError(f"Output directory not found: {output_dir}")
        
        try:
            # Load CV
            cv_path = output_dir / "cv.md"
            cv_markdown = self._read_file(cv_path)
            
            # Load Cover Letter
            cover_letter_path = output_dir / "cover_letter.md"
            cover_letter_markdown = self._read_file(cover_letter_path)
            
            # Load Metadata
            metadata_path = output_dir / "metadata.json"
            metadata = self._read_json(metadata_path)
            
            # Load Validation Results (optional)
            validation_path = output_dir / "validation_results.json"
            validation = None
            if validation_path.exists():
                validation = self._read_json(validation_path)
            
            return {
                "cv_markdown": cv_markdown,
                "cover_letter_markdown": cover_letter_markdown,
                "metadata": metadata,
                "validation": validation
            }
            
        except Exception as e:
            raise StorageError(
                f"Failed to load outputs from {output_dir}: {e}"
            ) from e
    
    def list_outputs(self, limit: int = 10) -> list[Path]:
        """
        Liste die neuesten Output Directories.
        
        Args:
            limit: Max Anzahl Directories (default: 10)
        
        Returns:
            List of Output Directory Paths (sorted by timestamp, newest first)
        """
        output_dirs = []
        
        for entry in self.outputs_base_path.iterdir():
            if entry.is_dir():
                output_dirs.append(entry)
        
        # Sort by directory name (contains timestamp)
        output_dirs.sort(reverse=True)
        
        return output_dirs[:limit]
    
    def _create_output_directory(self, generated_output: GeneratedOutput) -> Path:
        """
        Erstelle Output Directory mit Timestamp + Trace ID.
        
        Args:
            generated_output: Generated Output
        
        Returns:
            Path zum neuen Directory
        """
        # Format: YYYY-MM-DD_HH-MM-SS_{trace_id}
        timestamp = datetime.fromisoformat(generated_output.timestamp)
        dir_name = f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_{generated_output.trace_id[:8]}"
        
        output_dir = self.outputs_base_path / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    def _build_metadata(
        self,
        generated_output: GeneratedOutput,
        cv_validation: Optional[ValidationResult],
        cover_letter_validation: Optional[ValidationResult]
    ) -> Dict:
        """Baue Metadata Dictionary"""
        metadata = {
            "trace_id": generated_output.trace_id,
            "timestamp": generated_output.timestamp,
            "generation_metadata": generated_output.metadata,
            "validation_summary": {
                "cv_valid": cv_validation.is_valid if cv_validation else None,
                "cv_word_count": cv_validation.word_count if cv_validation else None,
                "cover_letter_valid": cover_letter_validation.is_valid if cover_letter_validation else None,
                "cover_letter_word_count": cover_letter_validation.word_count if cover_letter_validation else None
            },
            "files": {
                "cv": "cv.md",
                "cover_letter": "cover_letter.md",
                "validation": "validation_results.json"
            }
        }
        
        return metadata
    
    def _write_file(self, path: Path, content: str):
        """Schreibe Text File"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _write_json(self, path: Path, data: Dict):
        """Schreibe JSON File"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _read_file(self, path: Path) -> str:
        """Lese Text File"""
        if not path.exists():
            raise StorageError(f"File not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _read_json(self, path: Path) -> Dict:
        """Lese JSON File"""
        if not path.exists():
            raise StorageError(f"File not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


def create_output_storage(outputs_base_path: Optional[Path] = None) -> OutputStorage:
    """
    Factory function for OutputStorage.
    
    Args:
        outputs_base_path: Base directory für Outputs
    
    Returns:
        Configured OutputStorage instance
    """
    return OutputStorage(outputs_base_path=outputs_base_path)
