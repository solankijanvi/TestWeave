import json

from app.models import Application
from app.analyzer import analyze_application


with open("data/application.json", "r", encoding="utf-8") as file:
    data = json.load(file)


application = Application.model_validate(data)

print("Application model is valid!")
print("Start URL:", application.start_url)
print("Total pages:", application.total_pages)

analysis = analyze_application(application)

print("\nApplication analysis:")

for page in analysis["pages"]:
    print("\nURL:", page["url"])
    print("Title:", page["title"])
    print("Headings:", page["headings"])
    print("Inputs:", page["inputs"])
    print("Forms:", page["forms"])