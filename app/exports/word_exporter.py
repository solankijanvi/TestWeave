
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT_DIR / "data" / "test_cases.json"
QUALITY_FILE = ROOT_DIR / "data" / "quality_report.json"
OUTPUT_FILE = ROOT_DIR / "data" / "test_cases.docx"


def load_json(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required JSON file not found: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def add_quality_report(document, quality_report):
    """Add quality metrics and findings to the Word document."""

    document.add_heading("Quality Assessment Report", level=1)

    application_url = quality_report.get("application_url", "")

    paragraph = document.add_paragraph()
    paragraph.add_run("Application URL: ").bold = True
    paragraph.add_run(application_url)

    metrics = quality_report.get("metrics", {})

    metric_labels = {
        "pages_crawled": "Pages Crawled",
        "requirements_generated": "Requirements Generated",
        "scenarios_generated": "Test Scenarios Generated",
        "test_cases_generated": "Test Cases Generated",
        "scenario_mapping_coverage_percent": "Scenario Mapping Coverage",
        "page_scenario_coverage_percent": "Page Scenario Coverage",
        "page_test_case_coverage_percent": "Page Test Case Coverage",
        "cases_with_steps_percent": "Cases With Test Steps",
        "cases_with_expected_results_percent": "Cases With Expected Results",
        "potential_duplicate_titles": "Potential Duplicate Titles",
        "potential_duplicate_objectives": "Potential Duplicate Objectives",
        "findings_count": "Total Quality Findings",
    }

    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"

    header_cells = table.rows[0].cells
    header_cells[0].text = "Quality Metric"
    header_cells[1].text = "Result"

    for cell in header_cells:
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)

    for key, label in metric_labels.items():
        value = metrics.get(key, "N/A")

        if key.endswith("_percent") and value != "N/A":
            value = f"{value}%"

        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = str(value)

    document.add_heading("Quality Findings", level=2)

    findings = quality_report.get("findings", [])

    if findings:
        findings_table = document.add_table(rows=1, cols=3)
        findings_table.style = "Table Grid"

        headers = ["Severity", "Test Case ID", "Issue"]

        for cell, header in zip(findings_table.rows[0].cells, headers):
            cell.text = header
            for run in cell.paragraphs[0].runs:
                run.bold = True

        for finding in findings:
            cells = findings_table.add_row().cells
            cells[0].text = str(finding.get("severity", ""))
            cells[1].text = str(finding.get("test_case_id", ""))
            cells[2].text = str(finding.get("issue", ""))

    else:
        paragraph = document.add_paragraph()
        paragraph.add_run("No quality findings detected.").bold = True

    document.add_paragraph(
        "Note: Coverage percentages represent the checks implemented "
        "in the current TestWeave quality analyzer. They do not establish "
        "that every application feature has been tested or that the "
        "application is defect-free."
    )


def export_test_cases(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    quality_file: Path = QUALITY_FILE,
) -> Path:
    """Export test cases and quality assessment to Word."""

    document_data = load_json(input_file)
    quality_report = load_json(quality_file)

    test_cases = document_data.get("test_cases", [])

    if not test_cases:
        raise ValueError("No test cases found to export.")

    document = Document()

    # Page layout
    section = document.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    # Default font
    normal_style = document.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10)

    # Title
    title = document.add_heading("TestWeave", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    subtitle = document.add_paragraph(
        "Application Test Case and Quality Assessment Document"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    application_url = document_data.get("application_url", "")

    if application_url:
        paragraph = document.add_paragraph()
        paragraph.add_run("Application URL: ").bold = True
        paragraph.add_run(application_url)

    paragraph = document.add_paragraph()
    paragraph.add_run("Total test cases: ").bold = True
    paragraph.add_run(str(len(test_cases)))

    total_steps = sum(
        len(case.get("test_steps", []))
        for case in test_cases
    )

    paragraph = document.add_paragraph()
    paragraph.add_run("Total test steps: ").bold = True
    paragraph.add_run(str(total_steps))

    document.add_paragraph(
        "Note: These are generated test cases, not execution results. "
        "Verify expected behavior against the application before execution."
    )

    # Quality report
    add_quality_report(document, quality_report)

    document.add_page_break()

    # Test cases
    document.add_heading("Test Cases", level=1)

    for index, case in enumerate(test_cases, start=1):
        document.add_heading(
            f"{case.get('test_case_id', f'TC-{index:03d}')} - "
            f"{case.get('title', 'Untitled test case')}",
            level=2,
        )

        details = [
            ("Scenario ID", case.get("scenario_id", "")),
            ("Objective", case.get("objective", "")),
            ("Priority", case.get("priority", "")),
            ("Test Type", case.get("test_type", "")),
            ("Source URL", case.get("source_url", "")),
            (
                "Preconditions",
                "\n".join(case.get("preconditions", []))
                or "None specified",
            ),
        ]

        table = document.add_table(rows=0, cols=2)
        table.style = "Table Grid"

        for label, value in details:
            cells = table.add_row().cells
            cells[0].text = label
            cells[1].text = str(value)

            for run in cells[0].paragraphs[0].runs:
                run.bold = True

        document.add_heading("Test Steps", level=3)

        steps = case.get("test_steps", [])

        if steps:
            step_table = document.add_table(rows=1, cols=4)
            step_table.style = "Table Grid"

            headers = [
                "Step",
                "Action",
                "Test Data",
                "Expected Result",
            ]

            for cell, header in zip(step_table.rows[0].cells, headers):
                cell.text = header

                for run in cell.paragraphs[0].runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)

            for step in steps:
                cells = step_table.add_row().cells
                cells[0].text = str(step.get("step_number", ""))
                cells[1].text = str(step.get("action", ""))
                cells[2].text = str(step.get("test_data", ""))
                cells[3].text = str(step.get("expected_result", ""))

        paragraph = document.add_paragraph()
        paragraph.add_run("Overall Expected Result: ").bold = True
        paragraph.add_run(str(case.get("expected_result", "")))

        evidence = case.get("evidence", [])

        if evidence:
            paragraph = document.add_paragraph()
            paragraph.add_run("Evidence:").bold = True

            for item in evidence:
                document.add_paragraph(
                    str(item),
                    style="List Bullet",
                )

        if index < len(test_cases):
            document.add_paragraph()

    output_file.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_file)

    print(f"Word export completed: {output_file}")
    print(f"Test cases exported: {len(test_cases)}")
    print(f"Test steps exported: {total_steps}")
    print("Quality Assessment Report added.")

    return output_file


if __name__ == "__main__":
    export_test_cases()
