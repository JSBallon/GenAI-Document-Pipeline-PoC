"""
Entry Point für CV Generation Pipeline (Dry-Run)

Verwendung:
    python -m src.main

Voraussetzungen:
    - .env Datei mit OPENROUTER_API_KEY
    - Sample Daten in samples/
    - Dependencies installiert (requirements.txt)
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

from src.llm.openai_client import create_client_from_env
from src.pipeline.generation_pipeline import create_pipeline
from src.pipeline.output_storage import OutputStorage
from src.pipeline.output_validator import OutputValidator


def main():
    """
    Run CV Generation Pipeline mit Sample Daten.
    
    Dry-Run Flow:
    1. Load Environment (.env)
    2. Initialize LLM Client
    3. Create Pipeline
    4. Generate CV + Cover Letter
    5. Validate Output
    6. Save Output to /outputs
    7. Print Summary
    """
    print("=" * 60)
    print("🚀 CV Generation Pipeline — Dry-Run v0.2.0")
    print("=" * 60)
    print()
    
    # Step 1: Initialize LLM Client
    print("📡 Initializing LLM Client (OpenRouter)...")
    try:
        llm_client = create_client_from_env()
        print(f"   ✅ Model: {llm_client.config.model}")
        print(f"   ✅ Max Tokens: {llm_client.config.max_tokens}")
        print(f"   ✅ Temperature: {llm_client.config.temperature}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("\n💡 Hinweis: .env Datei mit OPENROUTER_API_KEY erstellen!")
        print("   Beispiel:")
        print("   OPENROUTER_API_KEY=sk-or-v1-...")
        sys.exit(1)
    
    # Step 2: Create Pipeline
    print("\n🔧 Creating Pipeline...")
    pipeline = create_pipeline(llm_client, prompt_version="0.2.0")
    print("   ✅ Pipeline ready")
    print("   ✅ Prompt Version: 0.2.0 (M2 - Cover Letter RAG)")
    
    # Step 3: Define Input Files
    cv_path = "samples/sample_cv_001.md"
    job_ad_path = "samples/sample_job_ad_001.md"
    
    print(f"\n📄 Input Files:")
    print(f"   • CV: {cv_path}")
    print(f"   • Job Ad: {job_ad_path}")
    
    # Verify input files exist
    if not Path(cv_path).exists():
        print(f"   ❌ Error: CV file not found: {cv_path}")
        sys.exit(1)
    if not Path(job_ad_path).exists():
        print(f"   ❌ Error: Job Ad file not found: {job_ad_path}")
        sys.exit(1)
    print("   ✅ Input files verified")
    
    # Step 4: Generate Documents
    print("\n⚙️  Generating CV + Cover Letter...")
    print("   ⏳ This may take 30-60 seconds...")
    try:
        output = pipeline.generate_application_documents(
            cv_path=cv_path,
            job_ad_path=job_ad_path
        )
        print(f"   ✅ Generated successfully")
        print(f"   ✅ Trace ID: {output.trace_id[:16]}...")
    except Exception as e:
        print(f"   ❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 5: Validate Output
    print("\n🔍 Validating Output...")
    validator = OutputValidator()
    
    cv_validation = validator.validate_cv(output.cv_markdown)
    print(f"   • CV: {'✅ Valid' if cv_validation.is_valid else '⚠️ Invalid'}")
    print(f"     - Word Count: {cv_validation.word_count}")
    if cv_validation.warnings:
        for warning in cv_validation.warnings:
            print(f"     - Warning: {warning}")
    if cv_validation.issues:
        for issue in cv_validation.issues:
            print(f"     - {issue.severity.value.upper()}: {issue.message}")
    
    cover_letter_validation = validator.validate_cover_letter(output.cover_letter_markdown)
    print(f"   • Cover Letter: {'✅ Valid' if cover_letter_validation.is_valid else '⚠️ Invalid'}")
    print(f"     - Word Count: {cover_letter_validation.word_count}")
    if cover_letter_validation.warnings:
        for warning in cover_letter_validation.warnings:
            print(f"     - Warning: {warning}")
    if cover_letter_validation.issues:
        for issue in cover_letter_validation.issues:
            print(f"     - {issue.severity.value.upper()}: {issue.message}")
    
    # Step 6: Save Output
    print("\n💾 Saving Output...")
    storage = OutputStorage()
    output_dir = storage.save_outputs(
        output,
        cv_validation=cv_validation,
        cover_letter_validation=cover_letter_validation
    )
    print(f"   ✅ Saved to: {output_dir}")
    
    # Step 7: Print Summary
    print("\n" + "=" * 60)
    print("✅ DRY-RUN SUCCESSFUL")
    print("=" * 60)
    print(f"📁 Output Directory: {output_dir}")
    print(f"🔍 Trace ID: {output.trace_id}")
    print(f"📝 Prompt Version: {output.metadata['prompt_version']}")
    print(f"🤖 LLM Model: {output.metadata['llm_model']}")
    print()
    print("📊 Generated Files:")
    print(f"   • cv.md ({len(output.cv_markdown)} chars, {cv_validation.word_count} words)")
    print(f"   • cover_letter.md ({len(output.cover_letter_markdown)} chars, {cover_letter_validation.word_count} words)")
    print(f"   • metadata.json")
    print(f"   • validation_results.json")
    print()
    
    # Check for prompt logs
    logs_dir = Path("logs/prompts")
    if logs_dir.exists():
        log_files = list(logs_dir.glob("*.jsonl"))
        if log_files:
            print(f"📝 Prompt Logs: {len(log_files)} log file(s) in logs/prompts/")
        else:
            print("⚠️  No prompt logs found (check LLM client logging)")
    else:
        print("⚠️  Prompt logs directory not found")
    
    print()
    print("💡 Next Steps:")
    print("   1. Review generated documents:")
    print(f"      code {output_dir / 'cv.md'}")
    print(f"      code {output_dir / 'cover_letter.md'}")
    print("   2. Check validation results:")
    print(f"      code {output_dir / 'validation_results.json'}")
    print("   3. Check prompt logs:")
    print("      code logs/prompts/")
    print("   4. Verify M1 Exit Criteria")
    print("=" * 60)


if __name__ == "__main__":
    main()
