from dataclasses import dataclass
from datetime import datetime

@dataclass
class NewsArticle:
    """Class for storing news article information"""
    title: str
    subtitle: str
    url: str
    publication_date: datetime
    update_date: datetime = None
    image_url: str = None
    image_description: str = None
    image_author: str = None
    author: str = None
    breadcrumbs: list = None
    intro_text: str = None  # Article introduction text (before paywall)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON"""
        return {
            'title': self.title,
            'subtitle': self.subtitle,
            'url': self.url,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'update_date': self.update_date.isoformat() if self.update_date else None,
            'image_url': self.image_url,
            'image_description': self.image_description,
            'image_author': self.image_author,
            'author': self.author,
            'breadcrumbs': self.breadcrumbs,
            'intro_text': self.intro_text
        }
