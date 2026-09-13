from pydantic import BaseModel
from app.models.page import Page


class Application(BaseModel):
    start_url: str
    total_pages: int
    pages: list[Page]
    
