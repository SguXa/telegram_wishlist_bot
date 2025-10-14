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


Store = Dict[str, Any]
WishList = List[Wish]

