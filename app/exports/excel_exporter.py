
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT_DIR / "data" / "test_cases.json"
QUALITY_FILE = ROOT_DIR / "data" / "quality_report.json"
OUTPUT_FILE = ROOT_DIR / "data" / "test_cases.xlsx"


def load_json(file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(f"Required file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def style_header(worksheet, row_number=1):
    for cell in worksheet[row_number]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    worksheet.row_dimensions[row_number].height = 32


def export_test_cases(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    quality_file: Path = QUALITY_FILE,
) -> Path:

    document = load_json(input_file)
    quality_report = load_json(quality_file)

    test_cases = document.get("test_cases", [])

    if not test_cases:
        raise ValueError("No test cases found to export.")

    metrics = quality_report.get("metrics", {})
    findings = quality_report.get("findings", [])

    workbook = Workbook()

    # ==========================================
    # SHEET 1: TEST CASES
    # ==========================================

    worksheet = workbook.active
    worksheet.title = "Test Cases"

    headers = [
        "Test Case ID",
        "Scenario ID",
        "Title",
        "Objective",
        "Source URL",
        "Preconditions",
        "Step Number",
        "Action",
        "Test Data",
        "Step Expected Result",
        "Overall Expected Result",
        "Priority",
        "Test Type",
        "Evidence",
    ]

    worksheet.append(headers)

    for case in test_cases:
        preconditions = "\n".join(case.get("preconditions", []))
        evidence = "\n".join(case.get("evidence", []))

        for step in case.get("test_steps", []):
            worksheet.append([
                case.get("test_case_id", ""),
                case.get("scenario_id", ""),
                case.get("title", ""),
                case.get("objective", ""),
                case.get("source_url", ""),
                preconditions,
                step.get("step_number", ""),
                step.get("action", ""),
                step.get("test_data", ""),
                step.get("expected_result", ""),
                case.get("expected_result", ""),
                case.get("priority", ""),
                case.get("test_type", ""),
                evidence,
            ])

    style_header(worksheet)

    column_widths = {
        1: 16, 2: 15, 3: 36, 4: 40, 5: 42, 6: 32,
        7: 13, 8: 48, 9: 35, 10: 55, 11: 45, 12: 12,
        13: 16, 14: 48,
    }

    for column_number, width in column_widths.items():
        worksheet.column_dimensions[
            get_column_letter(column_number)
        ].width = width

    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions

    # ==========================================
    # SHEET 2: QUALITY REPORT
    # ==========================================

    quality_sheet = workbook.create_sheet("Quality Report")

    quality_sheet.append(["TestWeave - Quality Assessment"])
    quality_sheet.merge_cells("A1:B1")

    quality_sheet["A1"].font = Font(
        bold=True,
        size=16,
        color="FFFFFF",
    )
    quality_sheet["A1"].fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )
    quality_sheet["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    quality_sheet.append([
        "Application URL",
        quality_report.get("application_url", ""),
    ])

    quality_sheet.append(["Metric", "Value"])
    style_header(quality_sheet, 3)

    metric_labels = {
        "pages_crawled": "Pages Crawled",
        "requirements_generated": "Requirements Generated",
        "scenarios_generated": "Scenarios Generated",
        "test_cases_generated": "Test Cases Generated",
        "scenario_mapping_coverage_percent": "Scenario Mapping Coverage (%)",
        "page_scenario_coverage_percent": "Page Scenario Coverage (%)",
        "page_test_case_coverage_percent": "Page Test Case Coverage (%)",
        "cases_with_steps_percent": "Cases With Steps (%)",
        "cases_with_expected_results_percent": "Cases With Expected Results (%)",
        "potential_duplicate_titles": "Potential Duplicate Titles",
        "potential_duplicate_objectives": "Potential Duplicate Objectives",
        "findings_count": "Total Findings",
    }

    for key, label in metric_labels.items():
        quality_sheet.append([
            label,
            metrics.get(key, "N/A"),
        ])

    # Findings section
    findings_header_row = quality_sheet.max_row + 2

    quality_sheet.cell(
        findings_header_row,
        1,
        "Quality Findings",
    )
    quality_sheet.merge_cells(
        start_row=findings_header_row,
        start_column=1,
        end_row=findings_header_row,
        end_column=3,
    )

    title_cell = quality_sheet.cell(findings_header_row, 1)
    title_cell.font = Font(
        bold=True,
        size=14,
        color="FFFFFF",
    )
    title_cell.fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )

    findings_header_row += 1

    quality_sheet.append([
        "Severity",
        "Test Case ID",
        "Issue",
    ])

    style_header(quality_sheet, findings_header_row)

    if findings:
        for finding in findings:
            quality_sheet.append([
                finding.get("severity", ""),
                finding.get("test_case_id", ""),
                finding.get("issue", ""),
            ])
    else:
        quality_sheet.append([
            "None",
            "N/A",
            "No quality findings detected.",
        ])

    quality_sheet.column_dimensions["A"].width = 42
    quality_sheet.column_dimensions["B"].width = 35
    quality_sheet.column_dimensions["C"].width = 85

    for row in quality_sheet.iter_rows():
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

    quality_sheet.freeze_panes = "A4"

    # ==========================================
    # SAVE WORKBOOK
    # ==========================================

    output_file.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_file)

    print(f"Excel export completed: {output_file}")
    print(f"Test cases exported: {len(test_cases)}")
    print(f"Test-step rows exported: {worksheet.max_row - 1}")
    print("Quality Report worksheet added.")
    print(f"Quality findings exported: {len(findings)}")

    return output_file


if __name__ == "__main__":
    export_test_cases()
