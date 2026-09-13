async def analyze_page(page):
    application = {
        "url": page.url,
        "title": await page.title(),
        "headings": [],
        "text": "",
        "links": [],
        "buttons": [],
        "inputs": [],
        "forms": [],
        "images": []
    }

    # Headings
    headings = await page.locator("h1, h2, h3, h4, h5, h6").all()

    for heading in headings:
        text = (await heading.inner_text()).strip()

        if text:
            application["headings"].append(text)

    # Visible page text
    body = page.locator("body")

    if await body.count() > 0:
        application["text"] = (await body.inner_text()).strip()

    # Links
    links = await page.locator("a").all()

    for link in links:
        text = (await link.inner_text()).strip()
        href = await link.get_attribute("href")

        application["links"].append({
            "text": text,
            "href": href
        })

    # Buttons
    buttons = await page.locator("button").all()

    for button in buttons:
        text = (await button.inner_text()).strip()

        application["buttons"].append({
            "text": text
        })

    # Inputs
    inputs = await page.locator("input").all()

    for input_field in inputs:
        application["inputs"].append({
            "type": await input_field.get_attribute("type"),
            "name": await input_field.get_attribute("name"),
            "placeholder": await input_field.get_attribute("placeholder")
        })

    # Forms
    forms = await page.locator("form").all()

    for form in forms:
        application["forms"].append({
            "action": await form.get_attribute("action"),
            "method": await form.get_attribute("method")
        })

    # Images
    images = await page.locator("img").all()

    for image in images:
        application["images"].append({
            "alt": await image.get_attribute("alt"),
            "src": await image.get_attribute("src")
        })

    return application