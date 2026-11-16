
import json
from pathlib import Path

DATA_DIR = Path("data")


def inspect_file(filename, list_key, limit=2):
    path = DATA_DIR / filename

    print(f"\n{'=' * 65}")
    print(f"FILE: {filename}")
    print("=" * 65)

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    items = data.get(list_key, [])
    print(f"Total items: {len(items)}")

    for index, item in enumerate(items[:limit], start=1):
        print(f"\n--- Item {index} ---")
        print(json.dumps(item, indent=2, ensure_ascii=False))


inspect_file("requirements.json", "requirements")
inspect_file("test_scenarios.json", "scenarios")
inspect_file("test_cases.json", "test_cases")
