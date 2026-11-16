
import json
import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urljoin

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parents[2]
SCENARIOS_FILE = ROOT_DIR / "data" / "test_scenarios.json"
OUTPUT_FILE = ROOT_DIR / "data" / "test_cases.json"


class TestStep(BaseModel):
    step_number: int = Field(ge=1)
    action: str
    test_data: str = "Not applicable"
    expected_result: str


class TestCase(BaseModel):
    test_case_id: str
    scenario_id: str
    title: str
    objective: str
    source_url: str
    preconditions: list[str] = Field(default_factory=list)
    test_steps: list[TestStep] = Field(min_length=1)
    expected_result: str
    priority: Literal["High", "Medium", "Low"]
    test_type: Literal[
        "UI", "Navigation", "Form", "Validation", "Functional"
    ]
    evidence: list[str] = Field(default_factory=list)


class TestCaseDocument(BaseModel):
    test_cases: list[TestCase]


def fallback_test_case(scenario: dict, case_number: int) -> TestCase:
    """Build a test case from observed scenario evidence."""

    steps = scenario.get("steps", [])
    if not steps:
        steps = ["Open the source page and inspect its visible content."]

    title = scenario.get("title", "Verify observed page behavior")
    objective = scenario.get("objective", "Verify the observed scenario.")
    source_url = scenario.get("source_url", "")
    evidence = scenario.get("evidence", [])

    observed_title = ""
    observed_headings = []
    observed_links = []
    observed_controls = []

    for item in evidence:
        text = str(item).strip()
        lowered = text.lower()

        if lowered.startswith(("observed title:", "page title:")):
            observed_title = text.split(":", 1)[1].strip()

        elif lowered.startswith("observed headings:"):
            raw = text.split(":", 1)[1].strip()
            try:
                parsed = json.loads(raw)
                values = parsed if isinstance(parsed, list) else [parsed]
                observed_headings.extend(
                    str(value).strip()
                    for value in values
                    if str(value).strip()
                )
            except (json.JSONDecodeError, TypeError):
                observed_headings.extend(
                    part.strip()
                    for part in re.split(r"[,;]", raw)
                    if part.strip()
                )

        elif re.match(
            r"Observed link text:\s*(.*?),\s*href:\s*(.*)",
            text,
            flags=re.IGNORECASE,
        ):
            match = re.match(
                r"Observed link text:\s*(.*?),\s*href:\s*(.*)",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                label = match.group(1).strip().strip("'\"")
                href = match.group(2).strip().strip("'\"")
                if label:
                    observed_links.append((label, href))

        elif lowered.startswith("observed link text:"):
            label = text.split(":", 1)[1].strip().strip("'\"")
            if label and not any(
                existing_label.lower() == label.lower()
                for existing_label, _ in observed_links
            ):
                observed_links.append((label, ""))

        elif lowered.startswith("observed href values:"):
            raw = text.split(":", 1)[1].strip()
            labels = [
                str(entry).split(":", 1)[1].strip().strip("'\"")
                for entry in evidence
                if str(entry).lower().startswith("observed link text:")
            ]
            label = labels[0] if labels else ""
            hrefs = [value.strip().strip("'\"") for value in raw.split(",")]

            for href in hrefs:
                if not label or not href:
                    continue

                empty_index = next(
                    (
                        i
                        for i, (existing_label, existing_href)
                        in enumerate(observed_links)
                        if existing_label.lower() == label.lower()
                        and not existing_href
                    ),
                    None,
                )

                if empty_index is not None:
                    observed_links[empty_index] = (label, href)
                elif not any(
                    existing_label.lower() == label.lower()
                    and existing_href == href
                    for existing_label, existing_href in observed_links
                ):
                    observed_links.append((label, href))

        elif lowered.startswith("observed links:"):
            raw = text.split(":", 1)[1].strip()
            try:
                parsed_links = json.loads(raw)
                if isinstance(parsed_links, list):
                    for link in parsed_links:
                        if not isinstance(link, dict):
                            continue

                        label = str(link.get("text", "")).strip()
                        href = str(link.get("href", "")).strip()
                        if label:
                            observed_links.append((label, href))
            except (json.JSONDecodeError, TypeError):
                pass

        elif lowered.startswith((
            "observed input:",
            "observed control:",
            "observed textarea:",
            "observed select:",
            "observed button:",
            "observed forms:",
        )):
            observed_controls.append(text)

    observed_headings = list(dict.fromkeys(observed_headings))
    observed_controls = list(dict.fromkeys(observed_controls))

    # Merge link records by label and preserve a known href.
    merged_links = []
    for label, href in observed_links:
        existing_index = next(
            (
                i
                for i, (existing_label, _) in enumerate(merged_links)
                if existing_label.casefold() == label.casefold()
            ),
            None,
        )

        if existing_index is None:
            merged_links.append((label, href))
        elif href and not merged_links[existing_index][1]:
            merged_links[existing_index] = (label, href)

    observed_links = merged_links

    previous_link_check = False
    previous_link_label = None

    def link_for_action(action_lower: str):
        """Match an action to the most relevant observed link."""
        for label, href in observed_links:
            if label and label.casefold() in action_lower:
                return label, href

        # Follow-up steps may refer to a link without repeating its label.
        if previous_link_label:
            for label, href in observed_links:
                if (
                    label.casefold() == previous_link_label.casefold()
                    and href != ""
                ):
                    return label, href

        if previous_link_check:
            candidates = [
                (label, href)
                for label, href in observed_links
                if label and href != ""
            ]
            if len(candidates) == 1:
                return candidates[0]

        return None

    test_steps = []

    for index, raw_step in enumerate(steps, start=1):
        action = re.sub(r"\s+", " ", str(raw_step)).strip()
        action_lower = action.casefold()
        test_data = "Not applicable"
        expected = ""

        if action_lower.startswith(("open ", "visit ", "navigate to ")):
            expected = (
                f"The browser opens {source_url}. Verify the resulting URL "
                "and record whether the page loads or displays an error."
            )
            test_data = source_url or "No source URL recorded"

        elif (
            "title" in action_lower
            and any(term in action_lower for term in ("heading", "headings"))
        ):
            checks = []

            if observed_title:
                checks.append(
                    f'The document title equals "{observed_title}".'
                )

            if observed_headings:
                checks.append(
                    "The visible heading(s) include: "
                    + "; ".join(f'"{heading}"' for heading in observed_headings)
                    + ". Record any missing or different heading."
                )

            expected = " ".join(checks) if checks else (
                "Record the document title and visible headings, "
                "then compare them with the captured crawl evidence."
            )

            test_values = []
            if observed_title:
                test_values.append(f"Expected title: {observed_title}")
            if observed_headings:
                test_values.append(
                    "Expected heading(s): " + "; ".join(observed_headings)
                )
            if test_values:
                test_data = "; ".join(test_values)

        elif "title" in action_lower and any(
            term in action_lower for term in ("document", "browser", "page")
        ):
            if observed_title:
                expected = f'The document title equals "{observed_title}".'
                test_data = f"Expected document title: {observed_title}"
            else:
                expected = (
                    "Record the actual document title and compare it with "
                    "the available crawl evidence."
                )

        elif "heading" in action_lower:
            if observed_headings:
                expected = (
                    "The visible heading(s) include: "
                    + "; ".join(f'"{heading}"' for heading in observed_headings)
                    + ". Record any missing or different heading."
                )
                test_data = "; ".join(observed_headings)
            else:
                expected = (
                    "Record the visible headings and compare them with "
                    "the captured evidence."
                )

        elif any(
            term in action_lower
            for term in ("link", "href", "destination", "target")
        ):
            matched_link = link_for_action(action_lower)

            if matched_link:
                label, href = matched_link

                is_locate_only = (
                    any(
                        term in action_lower
                        for term in ("locate", "find", "identify")
                    )
                    and not any(
                        term in action_lower
                        for term in ("href", "destination", "target")
                    )
                )

                if is_locate_only:
                    expected = (
                        f'The page contains a visible link labelled "{label}".'
                    )
                    test_data = f"Link label: {label}"
                    previous_link_check = True
                    previous_link_label = label

                elif href != "":
                    expected_url = urljoin(source_url, href)
                    expected = (
                        f'The "{label}" link has an href attribute exactly '
                        f'equal to "{href}". Its resolved URL is '
                        f'"{expected_url}". Verify the href value; do not '
                        "treat this check alone as proof that navigation works."
                    )
                    test_data = f"Link label: {label}; expected href: {href}"
                    previous_link_check = True
                    previous_link_label = label

                else:
                    expected = (
                        f'The link "{label}" is visible. Record its actual '
                        "href and compare it with the available crawl evidence."
                    )
                    test_data = f"Link label: {label}"
                    previous_link_check = True
                    previous_link_label = label

            else:
                expected = (
                    "Identify the relevant link, verify its visibility, and "
                    "compare its actual href with the captured crawl evidence."
                )

        elif any(
            term in action_lower
            for term in (
                "control", "form", "input", "textarea", "text area",
                "dropdown", "select", "focus",
            )
        ):
            expected = (
                "Record whether each identified control is visible and "
                "available for its basic interaction. Do not assume "
                "undocumented validation or business rules."
            )
            if observed_controls:
                test_data = "; ".join(observed_controls)

        elif "button" in action_lower:
            expected = (
                "Record whether the identified button is visible and enabled. "
                "Only activate it when safe; compare any resulting behavior "
                "with a confirmed requirement."
            )
            if observed_controls:
                test_data = "; ".join(observed_controls)

        elif "compare" in action_lower and (
            "evidence" in action_lower or "recorded" in action_lower
        ):
            details = []
            if observed_title:
                details.append(f'document title "{observed_title}"')
            if observed_headings:
                details.append(
                    "heading(s) "
                    + ", ".join(f'"{heading}"' for heading in observed_headings)
                )

            if details:
                expected = (
                    "The observed "
                    + " and ".join(details)
                    + " match the captured crawl evidence. Record any mismatch."
                )
            else:
                expected = (
                    "Compare the observed page details with the supplied "
                    "scenario evidence and record each mismatch."
                )

        else:
            expected = (
                f"Perform this action: {action} Record the actual result "
                "and compare it with the scenario's stated expected behavior."
            )

        # Collapse repeated whitespace only; never alter observed labels.
        expected = re.sub(r"\s+", " ", expected).strip()

        test_steps.append(
            TestStep(
                step_number=index,
                action=action,
                test_data=test_data,
                expected_result=expected,
            )
        )

    overall_expected = str(scenario.get("expected_result", "")).strip()
    if not overall_expected:
        overall_expected = (
            "The observed behavior matches the scenario objective and "
            "available evidence. Record any discrepancy."
        )

    return TestCase(
        test_case_id=f"TC-{case_number:03d}",
        scenario_id=scenario.get("scenario_id", "UNKNOWN"),
        title=title,
        objective=objective,
        source_url=source_url,
        preconditions=scenario.get("preconditions", []),
        test_steps=test_steps,
        expected_result=overall_expected,
        priority=scenario.get("priority", "Medium"),
        test_type=scenario.get("test_type", "UI"),
        evidence=evidence,
    )


def main():
    load_dotenv(ROOT_DIR / ".env")

    if not SCENARIOS_FILE.exists():
        raise FileNotFoundError(
            f"Scenario file not found: {SCENARIOS_FILE}. "
            "Run the scenario generator first."
        )

    with SCENARIOS_FILE.open(encoding="utf-8") as file:
        scenario_doc = json.load(file)

    scenarios = scenario_doc.get("scenarios", [])
    if not scenarios:
        raise ValueError(
            "No test scenarios found. Generate scenarios first."
        )

    llm = None
    if os.getenv("GEMINI_API_KEY"):
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            timeout=30,
            max_retries=0,
        )

    all_cases = []
    gemini_count = 0
    fallback_count = 0

    for scenario in scenarios:
        print(f"Generating test case for {scenario.get('scenario_id')}")
        generated = None

        if llm:
            prompt = f"""
You are a senior software test engineer.
Convert the supplied scenario into ONE detailed executable test case.

Rules:
- Use only the supplied scenario and evidence.
- Preserve its scenario ID and source URL.
- Preserve observed labels, headings, and titles exactly.
- Provide numbered, actionable execution steps.
- Every step must have an observable expected result.
- Use test data only when supported by evidence.
- Do not invent required fields, validation rules, or business behavior.
- Keep priority and test type consistent with the scenario.
- Do not claim the test has actually been executed.
- Return one TestCaseDocument containing exactly one test case.

Scenario:
{json.dumps(scenario, ensure_ascii=False, indent=2)}
"""
            try:
                result = llm.with_structured_output(
                    TestCaseDocument
                ).invoke(prompt)

                if result.test_cases:
                    generated = result.test_cases[0]
                    gemini_count += 1
                    print("  Source: Gemini + LangChain")

            except Exception as exc:
                print(
                    f"  LLM unavailable ({type(exc).__name__}); "
                    "using fallback."
                )

        if generated is None:
            generated = fallback_test_case(scenario, len(all_cases) + 1)
            fallback_count += 1

        generated.test_case_id = f"TC-{len(all_cases) + 1:03d}"
        generated.scenario_id = scenario.get(
            "scenario_id", generated.scenario_id
        )
        generated.source_url = scenario.get(
            "source_url", generated.source_url
        )

        for number, step in enumerate(generated.test_steps, start=1):
            step.step_number = number

        all_cases.append(generated)

    result = {
        "application_url": scenario_doc.get("application_url", ""),
        "total_scenarios": len(scenarios),
        "total_test_cases": len(all_cases),
        "cases_generated_with_gemini": gemini_count,
        "cases_generated_with_fallback": fallback_count,
        "test_cases": [case.model_dump() for case in all_cases],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"\nSaved: {OUTPUT_FILE}")
    print(f"Total test cases: {len(all_cases)}")
    print(f"Generated with Gemini: {gemini_count}")
    print(f"Generated with fallback: {fallback_count}")


if __name__ == "__main__":
    main()
