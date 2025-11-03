from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass(slots=True)
class Wish:
    title: str
    link: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    photo_file_id: Optional[str] = None

    def as_tuple(self) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[int]]:
        """Порядок соответствует колонкам INSERT в БД."""
        return (self.title, self.link, self.category, self.description, self.priority)


Store = Dict[str, Any]
WishList = List[Wish]
