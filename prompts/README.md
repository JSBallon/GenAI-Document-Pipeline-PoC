# Prompt Registry — CV Governance Agent

## Übersicht

Dieses Verzeichnis enthält alle versionierten LLM-Prompts für den CV Governance Agent. Prompts werden gemäß **Semantic Versioning** verwaltet und durch Git versioniert.

## Verzeichnis-Struktur

```
prompts/
├── README.md                          # Diese Datei
├── v0.1.0/                           # Aktuelle PoC-Version
│   ├── system_prompt.yaml
│   ├── cv_generation_prompt.yaml
│   └── cover_letter_prompt.yaml
└── v0.2.0/                           # Zukünftige Versionen
    └── ...
```

## Versioning-Schema

### Semantic Versioning (MAJOR.MINOR.PATCH)

- **MAJOR** (z.B. 0.x.x → 1.x.x): Breaking Changes
  - Komplette Neustrukturierung des Prompts
  - Änderung des Output-Formats
  - Neue Input-Variablen (non-backwards-compatible)

- **MINOR** (z.B. 0.0.x → 0.1.x): Feature-Additions
  - Neue Instruktionen hinzugefügt
  - Erweiterte Governance-Controls
  - Verbesserte Beispiele oder Guidelines

- **PATCH** (z.B. 0.0.1 → 0.0.2): Bugfixes & Tweaks
  - Typo-Korrekturen
  - Kleine Formulierungsverbesserungen
  - Metadata-Updates

### PoC Versioning (v0.x.x)

Während der PoC-Phase (Milestone 1-4) bleiben wir bei **v0.x.x**, um die experimentelle Natur zu signalisieren.

- **v0.1.0**: Initial PoC Version (M1 - Tag 2) — ✅ AKTIV
- **v0.2.0**: Geplant für M2 (RAG-Integration, erweiterte Source Attribution)
- **v0.3.0**: Geplant für M3 (Quality Gates, Decision Logging)
- **v1.0.0**: Production-Ready (nach M4 Abschluss)

## Prompt-Katalog (v0.1.0)

### 1. System Prompt
**Datei**: `v0.1.0/system_prompt.yaml`
**Zweck**: Definiert die Rolle, Constraints und Governance-Anforderungen des CV Writer Agents  
**Anwendung**: Wird bei JEDEM LLM-Call als System Message verwendet  
**Key Features**:
- Faktentreue-Enforcement
- Source Attribution Requirement
- Confidence Self-Assessment
- Transparenz-Direktiven

### 2. CV Generation Prompt
**Datei**: `v0.1.0/cv_generation_prompt.yaml`
**Zweck**: Generiert zielgerichtete 1-Seiten-CVs basierend auf Job-Requirements  
**Anwendung**: User Prompt für CV-Generierung  
**Input-Variablen**:
- `{job_title}`, `{company_name}`, `{location}`
- `{critical_requirements}`, `{important_requirements}`, `{nice_to_have_requirements}`
- `{candidate_personal_info}`, `{candidate_experience}`, `{candidate_skills}`, etc.

**Output**: JSON mit `tailored_cv_markdown` + Metadata (Source Mapping, Confidence Scores, Coverage)

### 3. Cover Letter Prompt
**Datei**: `v0.1.0/cover_letter_prompt.yaml`
**Zweck**: Generiert professionelle 1-Seiten-Anschreiben  
**Anwendung**: User Prompt für Anschreiben-Generierung  
**Input-Variablen**:
- `{job_title}`, `{company_name}`, `{job_description}`
- `{current_position}`, `{top_qualifications}`, `{relevant_achievements}`

**Output**: JSON mit `cover_letter_markdown` + Metadata (Key Arguments, Confidence, Tone Analysis)

## Nutzung

### Prompt Laden (Python Beispiel)

```python
import yaml

def load_prompt(version: str, prompt_id: str) -> dict:
    """Lädt Prompt aus Registry"""
    path = f"prompts/{version}/{prompt_id}.yaml"
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Beispiel
system_prompt = load_prompt("v0.1.0", "system_prompt")
print(system_prompt['system_prompt'])
```

### Template-Variablen Ersetzen

```python
from string import Template

prompt_template = load_prompt("v0.1.0", "cv_generation_prompt")
user_prompt = Template(prompt_template['user_prompt_template'])

filled_prompt = user_prompt.safe_substitute(
    job_title="Senior Backend Developer",
    company_name="Tech Startup GmbH",
    critical_requirements="Python, Django, PostgreSQL",
    # ... weitere Variablen
)
```

## Governance-Integration

### Prompt Logging

Jeder LLM-Call MUSS geloggt werden mit:
- Prompt ID (aus YAML `prompt_id`)
- Version (aus YAML `version`)
- Full Prompt Text (System + User Prompt)
- Model, Timestamp, Trace ID

**Log-Format** (siehe `techContext.md` §3.3.2):
```json
{
  "trace_id": "trace_abc123",
  "prompt_id": "cv_generation_prompt",
  "version": "0.1.0",
  "timestamp": "2026-02-16T15:55:00+01:00",
  "model": "openai/gpt-4-turbo",
  "full_text": "...",
  "metadata": { ... }
}
```

### Version-Tracking

Alle Prompt-Änderungen werden durch Git getrackt:

```bash
# Neue Version erstellen
git add prompts/v0.0.2/
git commit -m "feat(prompts): Add enhanced source attribution to v0.0.2"
git tag prompts-v0.0.2

# Changelog automatisch generieren
git log --oneline prompts/
```

## Entwicklungs-Workflow

### 1. Neue Prompt-Version erstellen

```bash
# Kopiere aktuelle Version
cp -r prompts/v0.1.0 prompts/v0.2.0

# Bearbeite Prompts
# Aktualisiere version: "0.2.0" in allen YAML-Dateien

# Commit + Tag
git add prompts/v0.2.0
git commit -m "chore(prompts): Release v0.2.0"
git tag prompts-v0.2.0
```

### 2. Prompt testen

```bash
# Unit-Test für Prompt-Variablen
pytest tests/test_prompts.py

# Integration-Test mit echtem LLM
python tests/integration/test_prompt_v0_2_0.py
```

### 3. Rollback (falls nötig)

```bash
# Zu alter Version zurück
git checkout prompts-v0.1.0

# In Code: Version-Switch
PROMPT_VERSION = "v0.1.0"  # Fallback zu stabiler Version
```

## Best Practices

### ✅ DO

- **Teste neue Versionen** vor Production-Einsatz
- **Dokumentiere Änderungen** in Git Commit Messages
- **Verwende explizite Versionen** im Code (kein "latest")
- **Behalte alte Versionen** für Reproducibility
- **Logge Prompt Version** bei jedem LLM-Call

### ❌ DON'T

- Keine Prompts direkt im Code hardcoden
- Keine PII (Personenbezogene Daten) in Prompts committen
- Keine Breaking Changes ohne Major Version Bump
- Keine undokumentierten Prompt-Änderungen

## Compliance

### DSGVO / AI Act

- Prompts enthalten **keine personenbezogenen Daten** (nur Templates)
- Input-Variablen werden zur Laufzeit eingefügt
- Logs mit Full Prompts unterliegen Retention Policy (90 Tage PoC)

### Auditability

- Git History = Prompt Change Log
- Jedes LLM-Ergebnis ist auf Prompt-Version zurückführbar
- Reproduzierbarkeit: `git checkout <tag>` + Replay

## Roadmap

### v0.2.0 (M2 - RAG Integration)
- [ ] Erweiterte Source Attribution (Chunk IDs)
- [ ] Confidence Scoring Integration
- [ ] Retrieval-Context Injection

### v0.3.0 (M3 - Governance Core)
- [ ] Decision Logging Templates
- [ ] Quality Gates Integration
- [ ] Low-Confidence Handling

### v1.0.0 (M4 - Production Ready)
- [ ] Finalized Governance Controls
- [ ] Multi-Language Support
- [ ] Optimized Token Usage

---

**Maintainer**: Coding Agent  
**Last Updated**: 2026-02-16  
**Status**: ✅ Active (v0.1.0)
