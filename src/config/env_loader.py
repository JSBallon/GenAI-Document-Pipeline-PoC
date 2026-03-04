"""
Environment Loader Utility.

Zentraler Loader für .env aus dem Projektroot, um konsistente
Umgebungsvariablen in Streamlit/CLI/Tests sicherzustellen.
"""

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def load_project_env(env_path: Optional[Path] = None) -> bool:
    """
    Lade die .env Datei aus dem Projektroot oder einem übergebenen Pfad.

    Args:
        env_path: Optionaler Pfad zu einer .env Datei. Wenn None, wird der
                  Projektroot automatisch bestimmt.

    Returns:
        True, wenn eine .env Datei gefunden und geladen wurde, sonst False.
    """
    resolved_path = env_path or _resolve_project_root() / ".env"
    if not resolved_path.exists():
        return False

    return load_dotenv(dotenv_path=resolved_path, override=False)


def _resolve_project_root() -> Path:
    """Bestimme den Projektroot relativ zu diesem Modul."""
    return Path(__file__).resolve().parents[2]