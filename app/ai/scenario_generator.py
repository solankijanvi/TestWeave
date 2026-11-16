import json
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

ROOT_DIR = Path(__file__).resolve().parents[2]
CRAWL_FILE = ROOT_DIR / "data" / "application.json"
ANALYSIS_FILE = ROOT_DIR / "data" / "ai_analysis.json"
REQUIREMENTS_FILE = ROOT_DIR / "data" / "requirements.json"
OUTPUT_FILE = ROOT_DIR / "data" / "test_scenarios.json"


class TestScenario(BaseModel):
    scenario_id: str
    title: str
    objective: str
    source_url: str
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_result: str
    priority: Literal["High", "Medium", "Low"]
    test_type: Literal["UI", "Navigation", "Form", "Validation", "Functional"]
    evidence: list[str] = Field(default_factory=list)


class ScenarioDocument(BaseModel):
    scenarios: list[TestScenario]


    
def fallback_scenarios(page: dict) -> list[TestScenario]:
    """Generate page-specific scenarios using only observed crawl evidence."""
    url = page.get("url", "")
    scenarios = []

    def add(
        title: str,
        objective: str,
        steps: list[str],
        expected: str,
        test_type: str,
        evidence: list[str],
    ) -> None:
        scenarios.append(
            TestScenario(
                scenario_id=f"TEMP-{len(scenarios) + 1:03d}",
                title=title,
                objective=objective,
                source_url=url,
                preconditions=["The application page is accessible."],
                steps=steps,
                expected_result=expected,
                priority="Medium",
                test_type=test_type,
                evidence=evidence,
            )
        )

    title = (page.get("title") or "").strip()
    headings = [
        str(value).strip()
        for value in page.get("headings", [])
        if str(value).strip()
    ]
    links = page.get("links", [])
    inputs = page.get("inputs", [])
    selects = page.get("selects", [])
    textareas = page.get("textareas", [])
    forms = page.get("forms", [])
    buttons = page.get("buttons", [])

    # 1. Verify the page's observed title and headings.
    if title or headings:
        expected_parts = []

        if title:
            expected_parts.append(f'document title "{title}"')

        if headings:
            expected_parts.append(
                "visible heading text: " + ", ".join(f'"{h}"' for h in headings)
            )

        add(
            f"Verify page content: {headings[0] if headings else title}",
            "Check that the page displays the title and headings observed by the crawler.",
            [
                f"Open {url}.",
                "Read the document title and inspect the visible page headings.",
                "Compare the observed values with the values recorded in the evidence.",
            ],
            "Verify that " + " and ".join(expected_parts) + " match the observed crawl evidence.",
            "UI",
            [
                f"Observed title: {title}",
                f"Observed headings: {json.dumps(headings, ensure_ascii=False)}",
            ],
        )

    # 2. Check navigation links individually, grouping only links with the same label.
    link_groups = {}
    for link in links:
        label = (link.get("text") or "").strip()
        href = (link.get("href") or "").strip()

        if label and href:
            link_groups.setdefault(label, set()).add(href)

    for label, hrefs in link_groups.items():
        observed_targets = sorted(hrefs)
        add(
            f"Verify navigation link: {label}",
            f"Verify that the observed link labelled '{label}' is present with its recorded destination.",
            [
                f"Open {url}.",
                f"Locate the link labelled '{label}'.",
                "Check that the link is visible and inspect its destination.",
            ],
            (
                f'The link "{label}" is visible and its destination matches '
                f"one of the observed href values: {', '.join(observed_targets)}. "
                "This check verifies the recorded destination, not successful navigation."
            ),
            "Navigation",
            [
                f"Observed link text: {label}",
                f"Observed href values: {', '.join(observed_targets)}",
            ],
        )

    # 3. Verify discovered form controls without inventing validation rules.
    controls = []

    for item in inputs:
        name = (
            item.get("name")
            or item.get("id")
            or item.get("placeholder")
            or "unnamed input"
        )
        controls.append(f"Input: {name}")

    for item in selects:
        name = item.get("name") or item.get("id") or "unnamed dropdown"
        controls.append(f"Dropdown: {name}")

    for item in textareas:
        name = (
            item.get("name")
            or item.get("id")
            or item.get("placeholder")
            or "unnamed text area"
        )
        controls.append(f"Text area: {name}")

    if controls or forms:
        add(
            f"Verify form controls on {url.rstrip('/').split('/')[-1] or 'home page'}",
            "Check whether the form controls discovered by the crawler are visible and identifiable.",
            [
                f"Open {url}.",
                "Locate each control listed in the evidence.",
                "Record whether each control is visible and can be focused or selected as appropriate.",
            ],
            (
                "Each observed control is present and available for its intended basic interaction. "
                "Record any missing, hidden, or unusable control. "
                "Business rules and required-field behavior are not inferred."
            ),
            "Form",
            controls + [
                f"Observed forms: {json.dumps(forms, ensure_ascii=False)}"
            ],
        )

    # 4. Buttons are checked for presence, not assumed to have a particular outcome.
    for button in buttons:
        label = (
            button.get("text")
            or button.get("aria_label")
            or button.get("name")
            or "unlabelled button"
        ).strip()

        add(
            f"Verify button is available: {label}",
            f"Check that the observed button '{label}' is present and available for interaction.",
            [
                f"Open {url}.",
                f"Locate the button '{label}'.",
                "Check visibility and enabled state. Activate it only when doing so is safe, then record the observed result.",
            ],
            (
                f'The button "{label}" is visible and its enabled state can be determined. '
                "Any post-click behavior must be compared with an independently confirmed requirement."
            ),
            "UI",
            [f"Observed button: {json.dumps(button, ensure_ascii=False)}"],
        )

    # 5. Provide a useful fallback for pages with no other observable elements.
    if not scenarios:
        add(
            "Verify page loads",
            "Check whether the requested page loads and exposes observable content.",
            [
                f"Open {url}.",
                "Check the resulting URL, document title, and visible body content.",
            ],
            (
                "Record whether the page loads and whether a title or body content is present. "
                "Do not assume a successful business operation from page loading alone."
            ),
            "UI",
            [f"Observed title: {title}", f"Observed headings: {headings}"],
        )

    return scenarios

def main():
    load_dotenv(ROOT_DIR / ".env")

    for path in (CRAWL_FILE, ANALYSIS_FILE, REQUIREMENTS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    with CRAWL_FILE.open(encoding="utf-8") as f:
        crawl = json.load(f)
    with ANALYSIS_FILE.open(encoding="utf-8") as f:
        analysis = json.load(f)
    with REQUIREMENTS_FILE.open(encoding="utf-8") as f:
        requirements_doc = json.load(f)

    analysis_by_url = {
        p["url"]: p for p in analysis.get("pages", [])
    }
    requirements_by_url = {}
    for req in requirements_doc.get("requirements", []):
        requirements_by_url.setdefault(req["source_url"], []).append(req)

    llm = None
    if os.getenv("GEMINI_API_KEY"):
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            timeout=30,
            max_retries=0,
        )

    all_scenarios = []
    gemini_pages = 0
    fallback_pages = 0

    for page in crawl.get("pages", []):
        url = page.get("url", "")
        print(f"Generating scenarios for {url}")

        context = {
            "page": {
                "url": url,
                "title": page.get("title", ""),
                "headings": page.get("headings", []),
                "text": page.get("text", "")[:1500],
                "links": page.get("links", [])[:30],
                "inputs": page.get("inputs", []),
                "selects": page.get("selects", []),
                "textareas": page.get("textareas", []),
                "forms": page.get("forms", []),
                "buttons": page.get("buttons", []),
            },
            "analysis": analysis_by_url.get(url, {}),
            "requirements": requirements_by_url.get(url, []),
        }

        generated = None
        if llm:
            prompt = f"""
You are a senior software test analyst.
Generate a concise, non-duplicative set of test scenarios for this page.

Rules:
- Use only supplied crawl observations and analysis.
- Cover meaningful navigation, visible UI, forms, and input controls.
- Do not claim backend behavior is proven by a crawl.
- Include positive and negative scenarios only where evidence supports them.
- Each scenario must have actionable steps and an observable expected result.
- Do not invent required fields, validation rules, or business rules.
- Include source URL and evidence for each scenario.
- Use priority High, Medium, or Low.
- Use test_type UI, Navigation, Form, Validation, or Functional.
- Return ScenarioDocument with a scenarios list.
- Use temporary IDs; the program assigns final IDs.

Application evidence:
{json.dumps(context, ensure_ascii=False, indent=2)}
"""
            try:
                generated = llm.with_structured_output(
                    ScenarioDocument
                ).invoke(prompt)
                gemini_pages += 1
                print("  Source: Gemini + LangChain")
            except Exception as exc:
                fallback_pages += 1
                print(f"  LLM unavailable ({type(exc).__name__}); using fallback.")
        else:
            fallback_pages += 1
            print("  API key missing; using fallback.")

        if generated is not None and generated.scenarios:
            page_scenarios = generated.scenarios
        else:
            page_scenarios = fallback_scenarios(page)

        for scenario in page_scenarios:
            scenario.scenario_id = f"TS-{len(all_scenarios) + 1:03d}"
            all_scenarios.append(scenario)

    result = {
        "application_url": crawl.get("start_url", ""),
        "total_pages": len(crawl.get("pages", [])),
        "total_scenarios": len(all_scenarios),
        "pages_with_gemini_generation": gemini_pages,
        "pages_using_fallback": fallback_pages,
        "scenarios": [s.model_dump() for s in all_scenarios],
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total scenarios: {len(all_scenarios)}")
    print(f"Gemini pages: {gemini_pages}")
    print(f"Fallback pages: {fallback_pages}")


if __name__ == "__main__":
    main()
