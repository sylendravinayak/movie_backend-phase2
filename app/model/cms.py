from datetime import datetime
from typing import List, Dict, Any, Optional
from beanie import Document
from pydantic import Field, BaseModel


class Section(BaseModel):
    heading: str
    body: str


class CTA(BaseModel):
    label: str
    url: str


class CMSContent(Document):
    id: str = Field(default="landing", alias="_id")
    title: str = "Welcome"
    subtitle: str = ""
    hero_image: str = ""
    sections: List[Section] = []
    ctas: List[CTA] = []
    featured_movies: List[Any] = []
    seo: Dict[str, Any] = {}
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    class Settings:
        name = "cms_content"
        # Use fixed id => acts like singleton record.

    def to_public_dict(self) -> Dict[str, Any]:
        d = self.dict(by_alias=False)
        # Do not expose internal _id alias confusion; already mapped.
        return d