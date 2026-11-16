from urllib.parse import urlparse
def detect_page_purpose(page):
    url = page.url.lower()
    scores = {
        "Home": 0,
        "About": 0,
        "Prediction": 0,
        "Reviews": 0,
        "Contact": 0,
        "Authentication": 0
    }
    title = page.title.lower()
    headings = " ".join(page.headings).lower()
    # Home
    evidence = []

    parsed_url = urlparse(page.url)

    if parsed_url.path in ("", "/"):
        evidence.append("URL represents the application root")

    if evidence:
        return {
            "purpose": "Home",
            "evidence": evidence,
            "confidence": "Medium"
        }
    # Contact
    evidence = []

    if "/contact" in url:
        evidence.append("URL contains '/contact'")

    if "get in touch" in headings:
        evidence.append("Heading contains 'get in touch'")

    if evidence:
        return {
            "purpose": "Contact",
            "evidence": evidence,
            "confidence": "High"
        }

    # Reviews
    evidence = []

    if "/reviews" in url:
        evidence.append("URL contains '/reviews'")

    if "review" in headings:
        evidence.append("Heading contains 'review'")

    if evidence:
        return {
            "purpose": "Reviews",
            "evidence": evidence,
            "confidence": "High"
        }

    # Prediction
    evidence = []

    if "/predict" in url:
        evidence.append("URL contains '/predict'")

    if "predict" in headings:
        evidence.append("Heading contains 'predict'")

    if evidence:
        return {
            "purpose": "Prediction",
            "evidence": evidence,
            "confidence": "High"
        }

    # About
    evidence = []

    if "/about" in url:
        evidence.append("URL contains '/about'")

    if "about us" in headings:
        evidence.append("Heading contains 'about us'")

    if evidence:
        return {
            "purpose": "About",
            "evidence": evidence,
            "confidence": "High"
        }

    # Authentication
    evidence = []

    if "/login" in url:
        evidence.append("URL contains '/login'")

    if "login" in headings:
        evidence.append("Heading contains 'login'")

    if "sign in" in headings:
        evidence.append("Heading contains 'sign in'")

    if evidence:
        return {
            "purpose": "Authentication",
            "evidence": evidence,
            "confidence": "High"
        }

    # Unknown
    return {
        "purpose": "Unknown",
        "evidence": [],
        "confidence": "Low"
    }


def analyze_application(application):
    analysis = {
        "start_url": application.start_url,
        "total_pages": application.total_pages,
        "pages": []
    }

    for page in application.pages:

        purpose_analysis = detect_page_purpose(page)

        page_analysis = {
            "url": page.url,
            "title": page.title,

            "purpose": purpose_analysis["purpose"],
            "purpose_evidence": purpose_analysis["evidence"],
            "purpose_confidence": purpose_analysis["confidence"],

            "functionality": detect_functionality(page),

            "headings": page.headings,
            "inputs": page.inputs,
            "buttons": page.buttons,
            "forms": page.forms,
            "links": page.links
        }

        analysis["pages"].append(page_analysis)

    return analysis


def detect_functionality(page):
    functionality = {
        "inputs": [],
        "selects": [],
        "textareas": [],
        "actions": [],
        "forms": []
    }
    # Inputs
    for input_field in page.inputs:
        input_info = {
            "type": input_field.type,
            "name": input_field.name,
            "placeholder": input_field.placeholder,
            "id": input_field.id,
            "aria_label": input_field.aria_label
        }

        functionality["inputs"].append(input_info)

        # Identify user actions
        if input_field.type in ("submit", "button"):
            action_name = (
                input_field.aria_label
                or input_field.name
                or input_field.placeholder
                or input_field.type
            )

            functionality["actions"].append(action_name)

    # Buttons
    for button in page.buttons:
        action_name = (
            button.aria_label
            or button.text
            or button.name
            or button.id
        )

        if action_name:
            functionality["actions"].append(action_name)

    # Select fields
    for select in page.selects:
        functionality["selects"].append({
            "name": select.name,
            "id": select.id,
            "options_count": len(select.options)
        })
    # Textareas
    for textarea in page.textareas:
        functionality["textareas"].append({
            "name": textarea.name,
            "id": textarea.id,
            "placeholder": textarea.placeholder
        })

    # Forms
    for form in page.forms:
        functionality["forms"].append({
            "action": form.action,
            "method": form.method
        })

    # User flow inference
    user_flow = []

    for input_field in functionality["inputs"]:
        field_name = (
            input_field["placeholder"]
            or input_field["name"]
            or input_field["id"]
        )

        if input_field["type"] != "submit":
            if field_name:
                user_flow.append(f"Enter {field_name}")

    for select in functionality["selects"]:
        field_name = select["name"] or select["id"]

        if field_name:
            user_flow.append(f"Select {field_name}")

    for textarea in functionality["textareas"]:
        field_name = (
            textarea["placeholder"]
            or textarea["name"]
            or textarea["id"]
        )

        if field_name:
            user_flow.append(f"Enter {field_name}")

    if functionality["actions"]:
        user_flow.append("Submit the form")

    functionality["user_flow"] = user_flow

    return functionality