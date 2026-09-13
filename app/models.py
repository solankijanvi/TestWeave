from pydantic import BaseModel
from typing import Optional


class Link(BaseModel):
    text: str
    href: Optional[str] = None
    
class Button(BaseModel):
    text: str
    
class InputField(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    placeholder: Optional[str] = None
    
    
class Application(BaseModel):
    url:str
    title: str
    links: list[Link]
    buttons: list[Button]
    inputs: list[InputField]