# Streamlit UI — RAG Pipeline Inspector

## Overview

Interactive visualization and debugging tool for the M2 RAG pipeline components.

**Status:** Infrastructure Ready (Milestone 2, Tag 4)  
**Views:** 4 (Chunking, Retrieval, Evidence, Confidence)  
**Purpose:** Development Tool, Debugging, Demo Preparation

---

## Installation

### 1. Install Dependencies

```bash
# From project root
pip install -r requirements.txt
```

This installs:
- `streamlit==1.31.0` — Web UI framework
- `pandas>=2.0.0` — DataFrame support for tables
- `sentence-transformers==2.2.0` — Embedding model
- `numpy>=1.24.0`, `scipy>=1.11.0` — Vector operations

### 2. Verify Installation

```bash
streamlit --version
# Expected: Streamlit, version 1.31.0
```

---

## Usage

### Start Streamlit App

```bash
# From project root
streamlit run src/streamlit_app.py
```

**Default URL:** http://localhost:8501

### Navigate Views

Use the sidebar radio buttons to switch between:

1. **Chunking** — CV segmentation analysis
2. **Retrieval** — Skill matching & vector search results
3. **Evidence** — Source attribution traceability
4. **Confidence** — Confidence score dashboard

### Select Input Files

Use the sidebar dropdowns to select:
- **CV File:** `samples/sample_cv_001.md`
- **Job Ad File:** `samples/sample_job_ad_001.md`

---

## Implementation Status

### ✅ Completed (Tag 4)

- [x] Streamlit project structure (`src/ui/`)
- [x] Entry point (`src/streamlit_app.py`)
- [x] Navigation & routing
- [x] Chunking View (placeholder structure)

### 🚧 In Progress

- [ ] **Task 2.1a:** Chunking View (real implementation)
  - Depends on: Task 2.1 (HybridChunker)
  - ETA: Tag 4 (parallel to chunking implementation)

### 📋 Planned

- [ ] **Task 2.5a:** Retrieval View
  - Depends on: Task 2.4, 2.5 (RequirementExtractor, VectorRetriever)
  - ETA: Tag 6

- [ ] **Task 2.7a:** Evidence + Confidence Views
  - Depends on: Task 2.6, 2.7 (EvidenceLinker, ConfidenceScorer)
  - ETA: Tag 7

---

## View Details

### 1. Chunking View (`chunking_view.py`)

**Features:**
- Section Overview Table (Chunk ID, Section, Size, Strategy)
- Chunk Details (Expandable with text preview + metadata)
- Chunk Size Distribution Histogram
- Hybrid Strategy Visualization (Section-based vs. Paragraph-split)

**Status:** Placeholder (shows mock data until Task 2.1 completed)

**Implementation Guide:** See code comments in `chunking_view.py`

---

### 2. Retrieval View (`retrieval_view.py`)

**Features:**
- Requirement Selection Dropdown
- Top-K Chunks Display (ID, Section, Score, Text Preview)
- Score Visualization (Bar Chart, Color-Coded)
- Source Text Viewer

**Status:** Planned (Task 2.5a, Tag 6)

---

### 3. Evidence View (`evidence_view.py`)

**Features:**
- Annotated Output Display (Color-Coded Citations)
- Source Mapping Table (Statement → Chunk → Source)
- Interactive Traceability (Click to navigate)

**Status:** Planned (Task 2.7a, Tag 7)

---

### 4. Confidence View (`confidence_view.py`)

**Features:**
- Overall Confidence Metrics (Average, Distribution)
- Low-Confidence Flags Liste (<0.6 threshold)
- Confidence Heatmap

**Status:** Planned (Task 2.7a, Tag 7)

---

## Architecture

### Parallel to CLI

Streamlit UI runs **parallel** to the CLI pipeline (`src/main.py`):

- **CLI:** Production pipeline, automated runs, logging
- **Streamlit:** Development tool, debugging, visualization, demo

### Shared Components

Both CLI and Streamlit use the same core modules:
- `src/rag/*` — Chunking, Embedding, Retrieval
- `src/parsers/*` — CV/JobAd parsing
- `src/models/*` — Data models
- `src/governance/*` — Confidence scoring, validation

**No code duplication** — Streamlit is only a view layer.

---

## Demo Workflow

1. **Run Pipeline (CLI):**
   ```bash
   python -m src.main
   ```

2. **Inspect Results (Streamlit):**
   ```bash
   streamlit run src/streamlit_app.py
   ```

3. **Navigate Views:**
   - Chunking → See how CV was segmented
   - Retrieval → See which chunks matched requirements
   - Evidence → Trace output statements to sources
   - Confidence → Check confidence scores

4. **Screenshot:**
   - Capture key visualizations for roadshow/demo

---

## Development Notes

### Adding New Views

1. Create view module: `src/ui/new_view.py`
2. Implement `show_new_view(cv_path, job_path)` function
3. Add import + routing in `streamlit_app.py`
4. Add navigation option in sidebar radio

### Mock Data Strategy

Views can show mock data before core implementation:
- Helps visualize final UI structure
- Enables early feedback
- Real implementation replaces mock data seamlessly

### Error Handling

Views use try/except for graceful degradation:
```python
try:
    from ui.chunking_view import show_chunking_view
    show_chunking_view(cv_path)
except ImportError:
    st.warning("View not yet implemented...")
```

---

## Troubleshooting

### Streamlit not found

```bash
pip install streamlit==1.31.0
```

### Port already in use

```bash
streamlit run src/streamlit_app.py --server.port=8502
```

### Module import errors

Ensure you're running from project root:
```bash
# Good
cd /path/to/PoC1_CV-Governance-Agent_Dev
streamlit run src/streamlit_app.py

# Bad
cd src/ui
streamlit run ../streamlit_app.py  # Won't find modules
```

---

## Exit Criteria (M2)

Streamlit UI is **Must-Have** for M2 completion:

- [x] Streamlit infrastructure setup
- [ ] Chunking View functional (shows real chunks from HybridChunker)
- [ ] Retrieval View functional (shows real retrieval results)
- [ ] Evidence View functional (shows real source attribution)
- [ ] Confidence View functional (shows real confidence scores)
- [ ] All 4 views tested with sample data
- [ ] Demo-ready (screenshots, walkthrough prepared)

**Target:** Tag 7 (2026-02-21) — Full Demo Readiness

---

## References

- **Active Context:** `.memorybank/activeContext_M2.md`
- **Streamlit Supplement:** `.memorybank/activeContext_M2_streamlit_supplement.md`
- **Milestone Plan:** `.memorybank/milestonePlan.md` (M2 Details)
- **System Patterns:** `.memorybank/systemPatterns.md` (RAG Patterns)

---

**Version:** 0.1.0 (Initial Setup)  
**Last Updated:** 2026-02-17  
**Status:** 🟢 Infrastructure Ready — Views In Progress
