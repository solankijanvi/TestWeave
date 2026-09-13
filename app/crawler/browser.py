from playwright.async_api import async_playwright

async def create_browser(playwright):
    return await playwright.chromium.launch()