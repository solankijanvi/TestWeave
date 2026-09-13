from pydantic import BaseModel
from typing import Optional

class Link(BaseModel):
    text:str
    href: Optional[str] = None
    
    
class Button(BaseModel):
    text: str
    
class InputField(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    placeholder: Optional[str] = None
    
    
class Form(BaseModel):
    action: Optional[str] = None
    method: Optional[str] = None
    
    
class Image(BaseModel):
    alt: Optional[str] = None
    src: Optional[str] = None
    
