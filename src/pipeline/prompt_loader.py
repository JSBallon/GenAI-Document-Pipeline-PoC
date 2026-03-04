"""
Prompt Loader Module

Verantwortung: Laden und Validieren von YAML Prompt Templates
Compliance: SOLID Principles, Single Responsibility
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field, ValidationError


class PromptTemplate(BaseModel):
    """Pydantic Model für Prompt Template Data"""
    prompt_id: str
    version: str
    category: str
    description: str
    model_target: list[str]
    system_prompt: str = ""  # Optional for task prompts
    user_prompt_template: str = ""  # Optional for system prompts
    metadata: Dict
    
    class Config:
        frozen = True  # Immutable


class PromptLoadError(Exception):
    """Custom Exception für Prompt Loading Errors"""
    pass


class PromptLoader:
    """
    Lädt versionierte Prompt Templates aus YAML Files.
    
    Design Principles:
    - Single Responsibility: Nur Prompt Loading
    - Dependency Injection: Base path configurable
    - Error Handling: Custom exceptions mit klaren Messages
    """
    
    def __init__(self, prompts_base_path: Optional[Path] = None):
        """
        Initialize PromptLoader.
        
        Args:
            prompts_base_path: Base directory für Prompts (default: ./prompts)
        """
        if prompts_base_path is None:
            # Default: Project root/prompts
            project_root = Path(__file__).parent.parent.parent
            prompts_base_path = project_root / "prompts"
        
        self.prompts_base_path = Path(prompts_base_path)
        
        if not self.prompts_base_path.exists():
            raise PromptLoadError(
                f"Prompts directory not found: {self.prompts_base_path}"
            )
    
    def load_prompt(
        self, 
        prompt_name: str, 
        version: str = "0.1.0"
    ) -> PromptTemplate:
        """
        Lade Prompt Template aus YAML File.
        
        Args:
            prompt_name: Name des Prompts (z.B. "system_prompt")
            version: Semantic Version (z.B. "0.1.0")
        
        Returns:
            PromptTemplate: Validiertes Prompt Template
        
        Raises:
            PromptLoadError: Wenn Prompt nicht gefunden oder invalid
        
        Example:
            >>> loader = PromptLoader()
            >>> prompt = loader.load_prompt("system_prompt", "0.1.0")
            >>> print(prompt.system_prompt)
        """
        # Konstruiere Prompt Path
        version_dir = self.prompts_base_path / f"v{version}"
        prompt_file = version_dir / f"{prompt_name}.yaml"
        
        # Check if file exists
        if not prompt_file.exists():
            raise PromptLoadError(
                f"Prompt file not found: {prompt_file}\n"
                f"Expected: prompts/v{version}/{prompt_name}.yaml"
            )
        
        # Load YAML
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PromptLoadError(
                f"Failed to parse YAML: {prompt_file}\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise PromptLoadError(
                f"Failed to read file: {prompt_file}\n"
                f"Error: {e}"
            )
        
        # Validate with Pydantic
        try:
            prompt_template = PromptTemplate(**prompt_data)
        except ValidationError as e:
            raise PromptLoadError(
                f"Invalid prompt schema: {prompt_file}\n"
                f"Validation errors: {e}"
            )
        
        return prompt_template
    
    def load_all_prompts(self, version: str = "0.1.0") -> Dict[str, PromptTemplate]:
        """
        Lade alle Prompts für eine Version.
        
        Args:
            version: Semantic Version
        
        Returns:
            Dict mit prompt_name -> PromptTemplate
        
        Example:
            >>> loader = PromptLoader()
            >>> prompts = loader.load_all_prompts("0.1.0")
            >>> system = prompts["system_prompt"]
        """
        version_dir = self.prompts_base_path / f"v{version}"
        
        if not version_dir.exists():
            raise PromptLoadError(
                f"Version directory not found: {version_dir}"
            )
        
        prompts = {}
        
        # Finde alle YAML Files
        for prompt_file in version_dir.glob("*.yaml"):
            if prompt_file.name == "README.yaml":
                continue  # Skip README
            
            prompt_name = prompt_file.stem
            
            try:
                prompt_template = self.load_prompt(prompt_name, version)
                prompts[prompt_name] = prompt_template
            except PromptLoadError as e:
                # Log warning but continue
                print(f"Warning: Failed to load {prompt_name}: {e}")
                continue
        
        if not prompts:
            raise PromptLoadError(
                f"No valid prompts found in version {version}"
            )
        
        return prompts
    
    def get_available_versions(self) -> list[str]:
        """
        Liste alle verfügbaren Prompt Versions.
        
        Returns:
            List of version strings (e.g., ["0.1.0", "0.2.0"])
        """
        versions = []
        
        for version_dir in self.prompts_base_path.iterdir():
            if version_dir.is_dir() and version_dir.name.startswith("v"):
                version = version_dir.name[1:]  # Remove "v" prefix
                versions.append(version)
        
        return sorted(versions)


def create_prompt_loader() -> PromptLoader:
    """
    Factory function for PromptLoader.
    
    Returns:
        Configured PromptLoader instance
    """
    return PromptLoader()
