
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
REPORT_PATH = ROOT_DIR / "data" / "quality_report.json"


def main():
    if not REPORT_PATH.exists():
        print("Quality report not found. Run the quality analyzer first.")
        return

    with REPORT_PATH.open("r", encoding="utf-8") as file:
        report = json.load(file)

    findings = report.get("findings", [])

    print("\n" + "=" * 60)
    print("TESTWEAVE QUALITY FINDINGS")
    print("=" * 60)

    if not findings:
        print("\nNo quality findings detected.")
        return

    for index, finding in enumerate(findings, start=1):
        print(f"\n{index}. Severity: {finding.get('severity')}")
        print(f"   Test Case: {finding.get('test_case_id')}")
        print(f"   Issue: {finding.get('issue')}")


if __name__ == "__main__":
    main()
