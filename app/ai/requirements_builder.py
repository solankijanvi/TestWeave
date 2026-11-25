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
OUTPUT_FILE = ROOT_DIR / "data" / "requirements.json"


class Requirement(BaseModel):
    requirement_id: str
    title: str
    description: str
    source_url: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    requirement_type: Literal["observed", "inferred"]
    confidence: Literal["low", "medium", "high"]

class RequirementsDocument(BaseModel):
    requirements: list[Requirement]


def build_fallback_requirements(page: dict, start_id: int) -> list[Requirement]:
    """Build traceable requirements from elements actually found by the crawler."""
    requirements = []
    url = page.get("url", "")
    counter = start_id

    def add(title, description, evidence, kind="observed", confidence="medium"):
        nonlocal counter
        requirements.append(
            Requirement(
                requirement_id=f"REQ-{counter:03d}",
                title=title,
                description=description,
                source_url=url,
                evidence=evidence,
                requirement_type=kind,
                confidence=confidence,
            )
        )
        counter += 1

    # Navigation links are directly observed, but their destination behavior
    # has not necessarily been tested.
    for link in page.get("links", []):
        label = (link.get("text") or "").strip()
        href = link.get("href")
        if label and href:
            add(
                f"Navigation link: {label}",
                f'The page displays a link labelled "{label}" '
                f'with destination "{href}".',
                [f"Observed link text: {label}", f"Observed href: {href}"],
            )

    for field in page.get("inputs", []):
        name = (
            field.get("placeholder")
            or field.get("name")
            or field.get("id")
            or field.get("aria_label")
        )
        if name and field.get("type") not in ("hidden",):
            add(
                f"Input field: {name}",
                f'The page contains an input field identified as "{name}". '
                "Required status and validation behavior have not been verified.",
                [f"Observed input attributes: {json.dumps(field, ensure_ascii=False)}"],
            )

    for field in page.get("selects", []):
        name = field.get("name") or field.get("id") or "unnamed dropdown"
        add(
            f"Dropdown: {name}",
            f'The page contains a dropdown identified as "{name}".',
            [f"Observed dropdown: {json.dumps(field, ensure_ascii=False)}"],
        )

    for field in page.get("textareas", []):
        name = (
            field.get("placeholder")
            or field.get("name")
            or field.get("id")
            or "unnamed text area"
        )
        add(
            f"Text area: {name}",
            f'The page contains a text area identified as "{name}".',
            [f"Observed text area: {json.dumps(field, ensure_ascii=False)}"],
        )

    for button in page.get("buttons", []):
        label = (
            button.get("text")
            or button.get("aria_label")
            or button.get("name")
            or button.get("id")
            or "unlabelled button"
        )
        add(
            f"Button: {label}",
            f'The page contains a button identified as "{label}". '
            "The outcome of clicking it has not been verified.",
            [f"Observed button: {json.dumps(button, ensure_ascii=False)}"],
        )

    for index, form in enumerate(page.get("forms", []), start=1):
        add(
            f"Form {index} is present",
            "The page contains a form. Successful submission and server-side "
            "processing have not been verified.",
            [f"Observed form: {json.dumps(form, ensure_ascii=False)}"],
        )

    # Add a cautious inferred requirement if the page has evidence but
    # no identifiable interactive elements.
    if not requirements and (page.get("title") or page.get("headings")):
        title = page.get("title") or "Untitled page"
        evidence = []
        if page.get("title"):
            evidence.append(f"Observed page title: {page['title']}")
        if page.get("headings"):
            evidence.append(
                "Observed headings: " + "; ".join(page["headings"][:10])
            )
        add(
            f"Informational page: {title}",
            "The page presents informational content. Its complete business "
            "purpose needs further validation.",
            evidence,
            kind="inferred",
            confidence="low",
        )

    return requirements

def build_requirement_prompt(page: dict, page_analysis: dict) -> str:
    """Build a grounded prompt from one page and its analysis."""

    observations = {
        "url": page.get("url", ""),
        "title": page.get("title", ""),
        "headings": page.get("headings", []),
        "text": page.get("text", "")[:1500],
        "links": page.get("links", [])[:30],
        "inputs": page.get("inputs", []),
        "selects": page.get("selects", []),
        "textareas": page.get("textareas", []),
        "buttons": page.get("buttons", []),
        "forms": page.get("forms", []),
        "page_analysis": page_analysis.get("analysis", {}),
        "analysis_source": page_analysis.get("analysis_source", "unknown"),
    }

    return f"""
You are a software business analyst generating traceable requirements.

Use only the supplied crawl observations and page analysis.
Do not invent features, validation rules, successful outcomes, or backend behavior.
Separate directly observed UI facts from inferred user or business needs.
Use requirement_type="observed" only for facts explicitly supported by evidence.
Use requirement_type="inferred" for interpretations.
Every requirement must have a source_url and specific evidence.
Keep descriptions clear, testable where possible, and concise.
Do not duplicate the same requirement.

Return a RequirementsDocument with a list of requirements.
Assign temporary IDs such as TEMP-001; final IDs will be assigned by the program.

Observations:
{json.dumps(observations, ensure_ascii=False, indent=2)}
"""

def generate_page_requirements(
    page: dict,
    page_analysis: dict,
    llm=None,
) -> tuple[list[Requirement], str]:
    """Generate requirements for one page, using fallback when necessary."""

    if llm is None:
        return build_fallback_requirements(page, start_id=1), "fallback"

    prompt = build_requirement_prompt(page, page_analysis)

    try:
        structured_llm = llm.with_structured_output(RequirementsDocument)
        generated = structured_llm.invoke(prompt)

        validated = RequirementsDocument.model_validate(generated)

        return validated.requirements, "gemini"

    except Exception as exc:
        print(
            f"LLM unavailable for {page.get('url', 'unknown URL')}: "
            f"{type(exc).__name__}. Using evidence-based fallback."
        )

        return build_fallback_requirements(page, start_id=1), "fallback"

def main():
    load_dotenv(ROOT_DIR / ".env")

    for path in (CRAWL_FILE, ANALYSIS_FILE):
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

    with CRAWL_FILE.open(encoding="utf-8") as file:
        crawl = json.load(file)

    with ANALYSIS_FILE.open(encoding="utf-8") as file:
        analysis = json.load(file)

    analysis_by_url = {
        item["url"]: item for item in analysis.get("pages", [])
    }

    pages = crawl.get("pages", [])
    if not pages:
        raise ValueError("No crawled pages found.")

    llm = None
    if os.getenv("GEMINI_API_KEY"):
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            google_api_key=os.getenv("GEMINI_API_KEY"),
            timeout=30,
            max_retries=0,
        )

    all_requirements = []
    llm_successes = 0
    fallback_pages = 0

    for page in pages:
        url = page.get("url", "")
        page_analysis = analysis_by_url.get(url, {})
        page_requirements, source = generate_page_requirements(
            page=page,
            page_analysis=page_analysis,
            llm=llm,
        )
        if source == "gemini":
            llm_successes += 1
            print(f"Gemini requirements generated: {url}")
        else:
            fallback_pages += 1
            print(f"Using fallback requirements: {url}")

        for requirement in page_requirements:
            requirement.requirement_id = f"REQ-{len(all_requirements) + 1:03d}"
            all_requirements.append(requirement)

    result = {
        "application_url": crawl.get("start_url", ""),
        "total_pages": len(pages),
        "total_requirements": len(all_requirements),
        "pages_with_gemini_generation": llm_successes,
        "pages_using_fallback": fallback_pages,
        "requirements": [
            requirement.model_dump() for requirement in all_requirements
        ],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print(f"\nRequirements saved to: {OUTPUT_FILE}")
    print(f"Total requirements: {len(all_requirements)}")
    print(f"Pages with Gemini generation: {llm_successes}")
    print(f"Pages using fallback: {fallback_pages}")

if __name__ == "__main__":
    main()