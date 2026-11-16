
import json
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"


def load_json(filename: str) -> dict:
    """Load a JSON file from the project's data directory."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def percentage(numerator: int, denominator: int) -> float:
    """Return a percentage safely."""
    if denominator == 0:
        return 0.0

    return round(numerator / denominator * 100, 2)


def analyze_quality() -> dict:
    """Analyze coverage, completeness, and potential duplicates."""

    application = load_json("application.json")
    requirements_data = load_json("requirements.json")
    scenarios_data = load_json("test_scenarios.json")
    cases_data = load_json("test_cases.json")

    pages = application.get("pages", [])
    requirements = requirements_data.get("requirements", [])
    scenarios = scenarios_data.get("scenarios", [])
    cases = cases_data.get("test_cases", [])

    page_urls = {
        page.get("url")
        for page in pages
        if page.get("url")
    }

    scenario_urls = {
        scenario.get("source_url")
        for scenario in scenarios
        if scenario.get("source_url")
    }

    case_urls = {
        case.get("source_url")
        for case in cases
        if case.get("source_url")
    }

    scenario_ids = {
        scenario.get("scenario_id")
        for scenario in scenarios
        if scenario.get("scenario_id")
    }

    case_scenario_ids = [
        case.get("scenario_id")
        for case in cases
        if case.get("scenario_id")
    ]

    mapped_scenario_ids = set(case_scenario_ids)

    missing_scenario_ids = sorted(scenario_ids - mapped_scenario_ids)
    orphan_case_ids = sorted(mapped_scenario_ids - scenario_ids)

    findings = []

    # Check test case completeness
    for case in cases:
        case_id = case.get("test_case_id", "UNKNOWN")

        required_fields = [
            "title",
            "objective",
            "expected_result",
        ]

        for field in required_fields:
            if not str(case.get(field, "")).strip():
                findings.append({
                    "severity": "High",
                    "test_case_id": case_id,
                    "issue": f"Missing required field: {field}",
                })

        steps = case.get("test_steps", [])

        if not steps:
            findings.append({
                "severity": "High",
                "test_case_id": case_id,
                "issue": "Test case has no steps",
            })

        for index, step in enumerate(steps, start=1):
            if not str(step.get("action", "")).strip():
                findings.append({
                    "severity": "High",
                    "test_case_id": case_id,
                    "issue": f"Step {index} has no action",
                })

            if not str(step.get("expected_result", "")).strip():
                findings.append({
                    "severity": "Medium",
                    "test_case_id": case_id,
                    "issue": f"Step {index} has no expected result",
                })

    # Detect repeated titles and objectives on the same page
    title_groups = defaultdict(list)
    objective_groups = defaultdict(list)

    for case in cases:
        case_id = case.get("test_case_id", "UNKNOWN")
        source_url = (
            str(case.get("source_url", "")).strip() or "UNKNOWN_URL"
        )

        title = " ".join(
            str(case.get("title", "")).casefold().split()
        )

        objective = " ".join(
            str(case.get("objective", "")).casefold().split()
        )

        if title:
            title_groups[(source_url, title)].append(case_id)

        if objective:
            objective_groups[(source_url, objective)].append(case_id)

    duplicate_titles = {
        key: ids
        for key, ids in title_groups.items()
        if len(ids) > 1
    }

    duplicate_objectives = {
        key: ids
        for key, ids in objective_groups.items()
        if len(ids) > 1
    }

    for (source_url, title), case_ids in duplicate_titles.items():
        findings.append({
            "severity": "Medium",
            "test_case_id": ", ".join(case_ids),
            "issue": (
                f"Potential duplicate title on {source_url}: {title}"
            ),
        })

    for (source_url, objective), case_ids in duplicate_objectives.items():
        findings.append({
            "severity": "Low",
            "test_case_id": ", ".join(case_ids),
            "issue": (
                f"Potential duplicate objective on {source_url}: {objective}"
            ),
        })

    # Build quality report
    report = {
        "application_url": application.get("start_url", ""),

        "metrics": {
            "pages_crawled": len(pages),
            "requirements_generated": len(requirements),
            "scenarios_generated": len(scenarios),
            "test_cases_generated": len(cases),

            "scenario_mapping_coverage_percent": percentage(
                len(scenario_ids & mapped_scenario_ids),
                len(scenario_ids),
            ),

            "page_scenario_coverage_percent": percentage(
                len(page_urls & scenario_urls),
                len(page_urls),
            ),

            "page_test_case_coverage_percent": percentage(
                len(page_urls & case_urls),
                len(page_urls),
            ),

            "cases_with_steps_percent": percentage(
                sum(bool(case.get("test_steps")) for case in cases),
                len(cases),
            ),

            "cases_with_expected_results_percent": percentage(
                sum(
                    bool(str(case.get("expected_result", "")).strip())
                    for case in cases
                ),
                len(cases),
            ),

            "potential_duplicate_titles": len(duplicate_titles),
            "potential_duplicate_objectives": len(duplicate_objectives),
            "findings_count": len(findings),
        },

        "unmapped_scenarios": missing_scenario_ids,
        "orphan_test_case_scenario_ids": orphan_case_ids,
        "findings": findings,
    }

    return report


def main():
    report = analyze_quality()

    output_path = DATA_DIR / "quality_report.json"

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("TestWeave quality analysis completed.")
    print(f"Report saved to: {output_path}")
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
