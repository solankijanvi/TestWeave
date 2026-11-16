async def analyze_page(page):
    application = {
        "url": page.url,
        "title": await page.title(),
        "headings": [],
        "text": "",
        "links": [],
        "buttons": [],
        "inputs": [],
        "selects": [],
        "textareas": [],
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
            "text": text,
            "type": await button.get_attribute("type"),
            "name": await button.get_attribute("name"),
            "id": await button.get_attribute("id"),
            "aria_label": await button.get_attribute("aria-label")
        })

    # Inputs
    inputs = await page.locator("input").all()

    for input_field in inputs:
        application["inputs"].append({
            "type": await input_field.get_attribute("type"),
            "name": await input_field.get_attribute("name"),
            "placeholder": await input_field.get_attribute("placeholder"),
            "id": await input_field.get_attribute("id"),
            "aria_label": await input_field.get_attribute("aria-label")
        })

    # Select elements
    selects = await page.locator("select").all()

    for select in selects:
        options = await select.locator("option").all()

        option_data = []

        for option in options:
            option_data.append({
                "text": (await option.inner_text()).strip(),
                "value": await option.get_attribute("value")
            })

        application["selects"].append({
            "name": await select.get_attribute("name"),
            "id": await select.get_attribute("id"),
            "options": option_data
        })

    # Textareas
    textareas = await page.locator("textarea").all()

    for textarea in textareas:
        application["textareas"].append({
            "name": await textarea.get_attribute("name"),
            "id": await textarea.get_attribute("id"),
            "placeholder": await textarea.get_attribute("placeholder")
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