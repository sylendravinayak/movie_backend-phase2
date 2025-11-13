from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Section(BaseModel):
    heading: str
    body: str

class CTA(BaseModel):
    label: str
    url: str

class LandingContent(BaseModel):
    title: str
    subtitle: str
    hero_image: str
    sections: List[Section]
    ctas: List[CTA]
    featured_movies: List[Any]
    seo: Dict[str, Any]
    updated_at: Optional[str] = None
    version: Optional[int] = Field(default=None)

class LandingContentUpdate(BaseModel):
    title: Optional[str]
    subtitle: Optional[str]
    hero_image: Optional[str]
    sections: Optional[List[Section]]
    ctas: Optional[List[CTA]]
    featured_movies: Optional[List[Any]]
    seo: Optional[Dict[str, Any]]