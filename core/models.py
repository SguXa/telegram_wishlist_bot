from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


@dataclass(slots=True)
class Wish:
    title: str
    link: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    image: Optional[bytes] = None
    image_url: Optional[str] = None
    id: Optional[int] = None

    def as_tuple(self) -> Tuple[Union[str, None], ...]:
        """Порядок соответствует колонкам INSERT в БД."""
        return (
            self.title, self.link, self.category, self.description, self.priority, self.image, self.image_url
        )


Store = Dict[str, Any]
WishList = List[Wish]
