def detect_page_purpose(page):
    url = page.url.lower()
    title = page.title.lower()
    headings = " ".join(page.headings).lower()

    evidence = f"{url} {title} {headings}"

    if "/contact" in url or "get in touch" in headings:
        return "Contact"

    if "/reviews" in url or "review" in headings:
        return "Reviews"

    if "/predict" in url or "predict" in headings:
        return "Prediction"

    if "/about" in url or "about us" in headings:
        return "About"

    if "/login" in url or "login" in headings or "sign in" in headings:
        return "Authentication"

    return "Unknown"

def analyze_application(application):
    analysis = {
        "start_url": application.start_url,
        "total_pages": application.total_pages,
        "pages": []
    }

    for page in application.pages:
        page_analysis = {
            "url": page.url,
            "title": page.title,
            "purpose": detect_page_purpose(page),
            "headings": page.headings,
            "inputs": page.inputs,
            "buttons": page.buttons,
            "forms": page.forms,
            "links": page.links
        }

        analysis["pages"].append(page_analysis)

    return analysis