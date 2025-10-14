import csv
import io
from collections import defaultdict
from html import escape as html_escape
from typing import Dict, List, Tuple

from core.models import Wish


DEFAULT_CATEGORY_TITLE = "\u0411\u0435\u0437 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438"
DEFAULT_CATEGORY_EMOJI = "\U0001F4CC"

# Mapping of category keywords to emojis (case-insensitive substring match).
CATEGORY_EMOJI_MAP = {
    "tech": "\U0001F4BB",
    "\u0442\u0435\u0445": "\U0001F4BB",
    "gadget": "\U0001F4F1",
    "\u0433\u0430\u0434\u0436\u0435\u0442": "\U0001F4F1",
    "book": "\U0001F4DA",
    "\u043a\u043d\u0438\u0433\u0430": "\U0001F4DA",
    "music": "\U0001F3B5",
    "\u043c\u0443\u0437": "\U0001F3B5",
    "food": "\U0001F37D",
    "\u0435\u0434\u0430": "\U0001F37D",
    "coffee": "\u2615",
    "\u043a\u043e\u0444\u0435": "\u2615",
    "sport": "\U0001F3C3",
    "\u0441\u043f\u043e\u0440\u0442": "\U0001F3C3",
    "game": "\U0001F3AE",
    "\u0438\u0433\u0440": "\U0001F3AE",
    "shoe": "\U0001F45F",
    "\u043e\u0431\u0443\u0432": "\U0001F45F",
    "clothes": "\U0001F455",
    "\u043e\u0434\u0435\u0436": "\U0001F455",
    "home": "\U0001F3E0",
    "\u0434\u043e\u043c": "\U0001F3E0",
    "travel": "\u2708",
    "trip": "\u2708",
    "\u043f\u0443\u0442\u0435\u0448\u0435": "\u2708",
    "car": "\U0001F697",
    "\u0430\u0432\u0442\u043e": "\U0001F697",
    "beauty": "\U0001F484",
    "\u043a\u0440\u0430\u0441\u043e\u0442": "\U0001F484",
    "hobby": "\U0001F3A8",
    "\u0445\u043e\u0431\u0431\u0438": "\U0001F3A8",
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
        lines.append(f"   \U0001F517 {escape_html_text(wish.link)}")
    if wish.description:
        lines.append(f"   \U0001F4AC {escape_html_text(wish.description)}")
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
        return "\u0421\u043f\u0438\u0441\u043e\u043a \u0436\u0435\u043b\u0430\u043d\u0438\u0439 \u043f\u0443\u0441\u0442.\n"

    lines: List[str] = []
    for category, items in sort_wishes_for_display(wishes):
        emoji = category_to_emoji(category if category != DEFAULT_CATEGORY_TITLE else "")
        lines.append(f"{emoji} {category}")
        for wish in items:
            lines.append(build_wish_block(wish))
            lines.append("")  # blank line between wishes
        lines.append("")  # blank line between categories
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def compose_export_csv(wishes: List[Wish]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435",
            "\u0421\u0441\u044b\u043b\u043a\u0430",
            "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044f",
            "\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435",
            "\u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442",
        ]
    )
    for wish in wishes:
        writer.writerow(
            [
                wish.title,
                wish.link,
                wish.category,
                wish.description,
                wish.priority,
            ]
        )
    return output.getvalue()
