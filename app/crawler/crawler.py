import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright
from browser import create_browser
from crawl_manager import crawl_application

async def crawl(url: str):
    async with async_playwright() as playwright:

        browser = await create_browser(playwright)

        page = await browser.new_page()

        pages = await crawl_application(
            page=page,
            start_url=url,
            max_pages=10
        )

        await browser.close()

    application = {
        "start_url": url,
        "total_pages": len(pages),
        "pages": pages
    }

    data_folder = Path("data")
    data_folder.mkdir(exist_ok=True)

    output_file = data_folder / "application.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(application, file, indent=4)

    print()
    print("Crawl completed.")
    print(f"Pages discovered: {len(pages)}")
    print(f"Application data saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(
        crawl("https://bovineguard.onrender.com/")
    )