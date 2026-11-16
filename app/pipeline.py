
import argparse
import asyncio
import json
from pathlib import Path

from app.crawler.crawler import crawl

from app.ai import requirement_generator
from app.ai import requirements_builder
from app.ai import scenario_generator
from app.ai import test_case_generator

from app.analyzer import quality_analyzer

from app.exports.excel_exporter import export_test_cases as export_excel
from app.exports.word_exporter import export_test_cases as export_word


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


def validate_json_file(file_path: Path, required_key: str) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(f"Missing output file: {file_path}")

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON structure in {file_path}")

    # Quality report stores its metrics inside the "metrics" object.
    if required_key in ("pages_crawled", "findings_count"):
        metrics = data.get("metrics", {})

        if not isinstance(metrics, dict) or required_key not in metrics:
            raise ValueError(
                f"Missing metric '{required_key}' in {file_path}"
            )

        if required_key == "pages_crawled" and metrics[required_key] <= 0:
            raise ValueError("No pages were crawled.")

    elif required_key not in data:
        raise ValueError(f"Missing key '{required_key}' in {file_path}")

    elif not data[required_key]:
        raise ValueError(f"Empty value for '{required_key}' in {file_path}")

    return data

def run_pipeline(url: str) -> None:
    """Run the complete TestWeave workflow from URL to reports."""

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        raise ValueError(
            "Enter a valid URL beginning with http:// or https://."
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("TESTWEAVE — END-TO-END PIPELINE")
    print(f"Application URL: {url}")
    print("=" * 60)

    # Remove previous outputs to prevent stale data from being reused.
    output_files = [
        "application.json",
        "ai_analysis.json",
        "requirements.json",
        "test_scenarios.json",
        "test_cases.json",
        "quality_report.json",
        "test_cases.xlsx",
        "test_cases.docx",
    ]

    for filename in output_files:
        path = DATA_DIR / filename

        if path.exists():
            path.unlink()

    # STEP 1: Crawl application
    print("\n[1/8] Crawling application...")

    asyncio.run(
        crawl(
            url,
            output_file=str(DATA_DIR / "application.json")
        )
    )

    validate_json_file(
        DATA_DIR / "application.json",
        "pages"
    )

    # STEP 2: Analyze application
    print("\n[2/8] Analyzing application pages...")

    requirement_generator.main()

    validate_json_file(
        DATA_DIR / "ai_analysis.json",
        "pages"
    )

    # STEP 3: Generate requirements
    print("\n[3/8] Generating requirements...")

    requirements_builder.main()

    validate_json_file(
        DATA_DIR / "requirements.json",
        "requirements"
    )

    # STEP 4: Generate scenarios
    print("\n[4/8] Generating test scenarios...")

    scenario_generator.main()

    validate_json_file(
        DATA_DIR / "test_scenarios.json",
        "scenarios"
    )

    # STEP 5: Generate test cases
    print("\n[5/8] Generating test cases...")

    test_case_generator.main()

    validate_json_file(
        DATA_DIR / "test_cases.json",
        "test_cases"
    )

    # STEP 6: Run quality analysis
    print("\n[6/8] Running quality analysis...")

    quality_analyzer.main()

    validate_json_file(
        DATA_DIR / "quality_report.json",
        "pages_crawled"
    )

    # STEP 7: Export Excel
    print("\n[7/8] Exporting Excel...")

    export_excel()

    # STEP 8: Export Word
    print("\n[8/8] Exporting Word...")

    export_word()

    # Final summary
    print("\n" + "=" * 60)
    print("TESTWEAVE PIPELINE COMPLETED")
    print(f"JSON outputs: {DATA_DIR}")
    print(f"Quality report: {DATA_DIR / 'quality_report.json'}")
    print(f"Excel report: {DATA_DIR / 'test_cases.xlsx'}")
    print(f"Word report:  {DATA_DIR / 'test_cases.docx'}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl a website and generate TestWeave reports."
    )

    parser.add_argument(
        "--url",
        required=True,
        help="Website URL to analyze, e.g. https://example.com",
    )

    args = parser.parse_args()

    run_pipeline(args.url)


if __name__ == "__main__":
    main()
