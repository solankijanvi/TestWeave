from pydantic import BaseModel
from typing import Optional


class Link(BaseModel):
    text: str
    href: Optional[str] = None


class Button(BaseModel):
    text: str
    type: Optional[str] = None
    name: Optional[str] = None
    id: Optional[str] = None
    aria_label: Optional[str] = None


class InputField(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    placeholder: Optional[str] = None
    id: Optional[str] = None
    aria_label: Optional[str] = None


class SelectOption(BaseModel):
    text: str
    value: Optional[str] = None


class SelectField(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    options: list[SelectOption] = []


class Textarea(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None
    placeholder: Optional[str] = None


class Form(BaseModel):
    action: Optional[str] = None
    method: Optional[str] = None


class Image(BaseModel):
    alt: Optional[str] = None
    src: Optional[str] = None