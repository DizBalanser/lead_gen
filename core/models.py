# core/models.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class Lead:
    """Модель данных для одной компании (лида)."""
    external_id: str
    name: str
    city: str
    address: str
    district: Optional[str] = None
    category: Optional[str] = None
    search_category: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    instagram: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    url: Optional[str] = None
    scraped_at: str = ""

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь (например, для pandas)."""
        return {
            "external_id": self.external_id,
            "name": self.name,
            "city": self.city,
            "address": self.address,
            "district": self.district,
            "category": self.category,
            "search_category": self.search_category,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "instagram": self.instagram,
            "rating": self.rating,
            "review_count": self.review_count,
            "url": self.url,
            "scraped_at": self.scraped_at
        }
