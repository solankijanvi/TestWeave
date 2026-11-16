from pydantic import BaseModel

from app.models.element import (
    Link,
    Button,
    InputField,
    SelectField,
    Textarea,
    Form,
    Image
)


class Page(BaseModel):
    url: str
    title: str
    headings: list[str]
    text: str
    links: list[Link]
    buttons: list[Button]
    inputs: list[InputField]
    selects: list[SelectField]
    textareas: list[Textarea]
    forms: list[Form]
    images: list[Image]