import csv
import io
from collections import defaultdict
from html import escape as html_escape
from typing import Dict, List, Tuple

from core.models import Wish


DEFAULT_CATEGORY_TITLE = "Без категории"
DEFAULT_CATEGORY_EMOJI = "✨"

# Provide a small dictionary of category keywords to emojis so that users get
# a sensible icon automatically. Matching is case-insensitive and uses
# substring matching for flexibility.
CATEGORY_EMOJI_MAP = {
    "тех": "💻",
    "tech": "💻",
    "гаджет": "📱",
    "gadget": "📱",
    "book": "📚",
    "книг": "📚",
    "music": "🎧",
    "муз": "🎧",
    "food": "🍽️",
    "еда": "🍽️",
    "коф": "☕",
    "coffee": "☕",
    "спорт": "⚽",
    "sport": "⚽",
    "игр": "🎮",
    "game": "🎮",
    "обув": "👟",
    "shoe": "👟",
    "clothes": "👕",
    "одеж": "👕",
    "home": "🏠",
    "дом": "🏠",
    "travel": "✈️",
    "trip": "✈️",
    "путеше": "✈️",
    "car": "🚗",
    "авто": "🚗",
    "beauty": "💄",
    "космет": "💄",
    "уход": "🧴",
    "здоров": "🩺",
}


def category_to_emoji(category: str) -> str:
    if not category:
        return DEFAULT_CATEGORY_EMOJI
    key = category.strip().lower()
    for needle, emoji in CATEGORY_EMOJI_MAP.items():
        if needle in key:
            return emoji
    return DEFAULT_CATEGORY_EMOJI


def escape_html_text(value: str) -> str:
    return html_escape(value, quote=True) if value else ""


def build_wish_block(wish: Wish) -> str:
    lines = [f"({wish.priority}) {escape_html_text(wish.title)}"]
    if wish.link:
        lines.append(f"   🔗 {escape_html_text(wish.link)}")
    if wish.description:
        lines.append(f"   📝 {escape_html_text(wish.description)}")
    return "\n".join(lines)


def sort_wishes_for_display(wishes: List[Wish]) -> List[Tuple[str, List[Wish]]]:
    grouped: Dict[str, List[Wish]] = defaultdict(list)
    for wish in wishes:
        category = wish.category.strip() if wish.category else ""
        category = category or DEFAULT_CATEGORY_TITLE
        grouped[category].append(wish)

    result: List[Tuple[str, List[Wish]]] = []
    for category, items in grouped.items():
        sorted_items = sorted(items, key=lambda w: w.priority, reverse=True)
        result.append((category, sorted_items))

    result.sort(key=lambda item: item[0].casefold())
    return result


def compose_export_txt(wishes: List[Wish]) -> str:
    if not wishes:
        return "Список желаний пуст."

    lines: List[str] = []
    for category, items in sort_wishes_for_display(wishes):
        emoji = category_to_emoji(category if category != DEFAULT_CATEGORY_TITLE else "")
        lines.append(f"{emoji} {category}")
        for wish in items:
            lines.append(build_wish_block(wish))
            lines.append("")  # extra newline between wishes
        lines.append("")  # extra newline between categories
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def compose_export_csv(wishes: List[Wish]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Название",
        "Ссылка",
        "Категория",
        "Описание",
        "Приоритет",
    ])
    return output.getvalue()

