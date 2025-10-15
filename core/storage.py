import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from core.models import Store, Wish


class Storage:
    def __init__(self, data_file: Path, authorized_numeric_ids: Iterable[str]):
        self._data_file = data_file
        self._authorized_ids = {str(identifier) for identifier in authorized_numeric_ids}
        self._lock = asyncio.Lock()
        self._store: Store = {"users": {identifier: [] for identifier in self._authorized_ids}}

    def load(self) -> None:
        if self._data_file.exists():
            try:
                loaded = json.loads(self._data_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                logging.warning("Failed to decode storage file, starting fresh.")
                loaded = {}
        else:
            loaded = {}

        users = loaded.get("users", {})
        for user_id in self._authorized_ids:
            users.setdefault(user_id, [])

        self._store = {"users": users}
        self.persist()

    def persist(self) -> None:
        self._data_file.write_text(json.dumps(self._store, ensure_ascii=False, indent=2), encoding="utf-8")

    async def mutate(self, mutator: Callable[[Store], Any]) -> Any:
        async with self._lock:
            result = mutator(self._store)
            self.persist()
            return result

    def list_wishes(self, user_id: int) -> List[Wish]:
        return [self._dict_to_wish(raw) for raw in self._store["users"].get(str(user_id), [])]

    def find_wish(self, user_id: int, wish_id: str) -> Optional[Wish]:
        for wish in self.list_wishes(user_id):
            if wish.id == wish_id:
                return wish
        return None

    async def add_wish(self, user_id: int, wish: Wish) -> None:
        user_key = str(user_id)

        def mutator(current: Store) -> None:
            current["users"].setdefault(user_key, [])
            current["users"][user_key].append(self._wish_to_dict(wish))

        await self.mutate(mutator)

    async def update_wish_field(self, user_id: int, wish_id: str, field: str, value: Any) -> Optional[Wish]:
        user_key = str(user_id)
        updated: Optional[Wish] = None

        def mutator(current: Store) -> None:
            nonlocal updated
            for wish in current["users"].setdefault(user_key, []):
                if wish["id"] == wish_id:
                    wish[field] = value
                    updated = self._dict_to_wish(wish)
                    break

        await self.mutate(mutator)
        return updated

    async def delete_wish(self, user_id: int, wish_id: str) -> bool:
        user_key = str(user_id)
        removed = False

        def mutator(current: Store) -> None:
            nonlocal removed
            wishes = current["users"].setdefault(user_key, [])
            original_length = len(wishes)
            wishes[:] = [wish for wish in wishes if wish["id"] != wish_id]
            removed = len(wishes) != original_length

        await self.mutate(mutator)
        return removed

    def collect_categories(self) -> List[str]:
        categories = set()
        for wishes in self._store["users"].values():
            for wish in wishes:
                name = (wish.get("category") or "").strip()
                if name:
                    categories.add(name)
        if not categories:
            return []
        return sorted(categories, key=lambda item: item.casefold())

    @staticmethod
    def _dict_to_wish(raw: Store) -> Wish:
        return Wish(
            id=raw["id"],
            title=raw["title"],
            link=raw.get("link", ""),
            category=raw.get("category", ""),
            description=raw.get("description", ""),
            priority=int(raw.get("priority", 0)),
            photo_file_id=raw.get("photo_file_id", ""),
        )

    @staticmethod
    def _wish_to_dict(wish: Wish) -> Store:
        return {
            "id": wish.id,
            "title": wish.title,
            "link": wish.link,
            "category": wish.category,
            "description": wish.description,
            "priority": wish.priority,
            "photo_file_id": wish.photo_file_id,
        }
