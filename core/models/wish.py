from dataclasses import dataclass
from typing import Optional

@dataclass
class Wish:
    title: str
    link: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None

    def as_tuple(self):
        """Return the Wish object as a tuple for database insertion."""
        return self.title, self.link, self.category, self.description, self.priority
