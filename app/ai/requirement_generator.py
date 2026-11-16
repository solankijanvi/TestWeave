import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.prompts import PAGE_ANALYSIS_PROMPT
from app.ai.schemas import AIPageAnalysis


ROOT_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = ROOT_DIR / "data" / "application.json"
OUTPUT_FILE = ROOT_DIR / "data" / "ai_analysis.json"


def build_observations(page: dict) -> dict:
    """Keep the LLM input focused on observed application behaviour."""
    return {
        "url": page.get("url", ""),
        "title": page.get("title", ""),
        "headings": page.get("headings", []),
        "visible_text": page.get("text", "")[:2500],
        "links": page.get("links", [])[:30],
        "buttons": page.get("buttons", []),
        "inputs": page.get("inputs", []),
        "selects": [
            {
                "name": item.get("name"),
                "id": item.get("id"),
                "options_count": len(item.get("options", [])),
            }
            for item in page.get("selects", [])
        ],
        "textareas": page.get("textareas", []),
        "forms": page.get("forms", []),
    }


def fallback_analysis(observations: dict) -> AIPageAnalysis:
    """Create a transparent, observation-based result if the LLM fails."""
    url = observations["url"].lower()
    title = observations["title"]
    headings = " ".join(observations["headings"])
    heading_lower = headings.lower()

    if "/predict" in url:
        purpose = "Prediction"
    elif "/contact" in url:
        purpose = "Contact"
    elif "/reviews" in url:
        purpose = "Reviews"
    elif "/about" in url:
        purpose = "About"
    elif url.rstrip("/").count("/") <= 2:
        purpose = "Home"
    else:
        purpose = "Unknown"

    actions = []

    for field in observations["inputs"]:
        name = (
            field.get("placeholder")
            or field.get("name")
            or field.get("id")
        )
        if name and field.get("type") not in ("submit", "button", "hidden"):
            actions.append(f"Enter {name}")

    for field in observations["selects"]:
        name = field.get("name") or field.get("id")
        if name:
            actions.append(f"Select an option for {name}")

    for field in observations["textareas"]:
        name = field.get("placeholder") or field.get("name") or field.get("id")
        if name:
            actions.append(f"Enter text in {name}")

    for button in observations["buttons"]:
        name = button.get("text") or button.get("aria_label")
        if name:
            actions.append(f"Click {name}")

    evidence = [
        f"Page URL: {observations['url']}",
        f"Page title: {title}",
    ]
    if headings:
        evidence.append(f"Observed headings: {headings}")

    functionality = (
        f"Fallback analysis based on crawled page evidence. "
        f"Purpose inferred as {purpose}. "
        f"Observed {len(observations['inputs'])} input fields, "
        f"{len(observations['selects'])} dropdowns, and "
        f"{len(observations['forms'])} forms. "
        "Backend behaviour has not been verified."
    )

    return AIPageAnalysis(
        page_purpose=purpose,
        functionality=functionality,
        user_actions=actions,
        evidence=evidence,
        confidence="low",
    )


def analyze_page(llm, page: dict) -> tuple[AIPageAnalysis, str]:
    observations = build_observations(page)

    prompt = (
        PAGE_ANALYSIS_PROMPT
        + "\n\nAnalyze these observed page details:\n"
        + json.dumps(observations, ensure_ascii=False, indent=2)
    )

    try:
        result = llm.with_structured_output(AIPageAnalysis).invoke(prompt)
        return result, "gemini_langchain"
    except Exception as exc:
        print(
            f"LLM analysis failed for {page.get('url', 'unknown URL')}: "
            f"{type(exc).__name__}: {exc}"
        )
        return fallback_analysis(observations), "fallback"


def main():
    load_dotenv(ROOT_DIR / ".env")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Crawl data not found: {INPUT_FILE}\n"
            "Run the crawler first."
        )

    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(
            "GEMINI_API_KEY is missing. Check your .env file."
        )

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        application = json.load(file)

    pages = application.get("pages", [])
    if not pages:
        raise ValueError("No crawled pages found in application.json.")

    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        timeout=30,
        max_retries=0,
    )

    results = []
    for index, page in enumerate(pages, start=1):
        print(f"[{index}/{len(pages)}] Analyzing {page.get('url', '')}")

        analysis, source = analyze_page(llm, page)

        results.append({
            "url": page.get("url", ""),
            "title": page.get("title", ""),
            "analysis_source": source,
            "analysis": analysis.model_dump(),
        })

        print(f"    Analysis source: {source}")

    output = {
        "start_url": application.get("start_url", ""),
        "total_pages": len(results),
        "ai_pages": sum(
            item["analysis_source"] == "gemini_langchain"
            for item in results
        ),
        "fallback_pages": sum(
            item["analysis_source"] == "fallback"
            for item in results
        ),
        "pages": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"\nAnalysis saved to: {OUTPUT_FILE}")
    print(f"Gemini analyses: {output['ai_pages']}")
    print(f"Fallback analyses: {output['fallback_pages']}")


if __name__ == "__main__":
    main()
