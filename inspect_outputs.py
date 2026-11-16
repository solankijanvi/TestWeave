
import json
from pathlib import Path

data_dir = Path("data")

files = [
    "application.json",
    "ai_analysis.json",
    "requirements.json",
    "test_scenarios.json",
    "test_cases.json",
]

for filename in files:
    path = data_dir / filename
    print(f"\n--- {filename} ---")

    if not path.exists():
        print("FILE MISSING")
        continue

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    for key, value in data.items():
        if isinstance(value, list):
            print(f"{key}: {len(value)} items")
        elif key in {
            "ai_pages",
            "fallback_pages",
            "pages_with_gemini_generation",
            "pages_using_fallback",
            "total_requirements",
            "total_scenarios",
            "total_test_cases",
            "cases_generated_with_gemini",
            "cases_generated_with_fallback",
        }:
            print(f"{key}: {value}")
