from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Wish:
    id: str
    title: str
    link: str
    category: str
    description: str
    priority: int
    photo_file_id: str = ""


Store = Dict[str, Any]
WishList = List[Wish]
