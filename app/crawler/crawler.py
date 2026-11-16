
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

from app.crawler.browser import create_browser
from app.crawler.crawl_manager import crawl_application


async def crawl(url: str, output_file: str = "data/application.json") -> dict:
    """Crawl a website, save the results, and return the application data."""

    async with async_playwright() as playwright:
        browser = await create_browser(playwright)

        try:
            page = await browser.new_page()

            pages = await crawl_application(
                page=page,
                start_url=url,
                max_pages=10,
            )
        finally:
            await browser.close()

    application = {
        "start_url": url,
        "total_pages": len(pages),
        "pages": pages,
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(application, file, indent=4, ensure_ascii=False)

    print("\nCrawl completed.")
    print(f"Pages discovered: {len(pages)}")
    print(f"Application data saved to: {output_path}")

    return application


if __name__ == "__main__":
    asyncio.run(crawl("https://bovineguard.onrender.com/"))
