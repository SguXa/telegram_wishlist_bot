import csv
import io
from collections import defaultdict
from html import escape as html_escape
from typing import Dict, List, Tuple

from aiogram.types import InputFile, Message

from core.models import Wish


DEFAULT_CATEGORY_TITLE = "Без категории"
DEFAULT_CATEGORY_EMOJI = "📌"

# Mapping of category keywords to emojis (case-insensitive substring match).
CATEGORY_EMOJI_MAP = {
    "tech": "💻",
    "тех": "💻",
    "gadget": "📱",
    "гаджет": "📱",
    "book": "📚",
    "книга": "📚",
    "music": "🎵",
    "муз": "🎵",
    "food": "🍽",
    "еда": "🍽",
    "coffee": "☕",
    "кофе": "☕",
    "sport": "🏃",
    "спорт": "🏃",
    "game": "🎮",
    "игр": "🎮",
    "shoe": "👟",
    "обув": "👟",
    "clothes": "👕",
    "одеж": "👕",
    "home": "🏠",
    "дом": "🏠",
    "travel": "✈",
    "trip": "✈",
    "путеше": "✈",
    "car": "🚗",
    "авто": "🚗",
    "beauty": "💄",
    "красот": "💄",
    "hobby": "🎨",
    "хобби": "🎨",
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


def _shorten_link_for_display(link: str, max_length: int = 40) -> str:
    """Вернуть укороченную версию ссылки для отображения в карточке.

    Показываем домен и начало пути, чтобы ссылка выглядела аккуратно, но
    оставалась узнаваемой. Полный URL остаётся в самом href.
    """
    if not link:
        return ""

    link = link.strip()

    # Удаляем схему для красоты отображения: https://example.com/... → example.com/...
    display = link
    for prefix in ("https://", "http://"):
        if display.startswith(prefix):
            display = display[len(prefix) :]
            break

    if len(display) <= max_length:
        return display

    # Если очень длинно — обрезаем и добавляем многоточие.
    return display[: max_length - 1] + "…"


def build_wish_block(wish: Wish) -> str:
    lines = [f"({wish.priority}) {escape_html_text(wish.title)}"]
    if wish.link:
        display_link = _shorten_link_for_display(wish.link)
        # Для HTML parse_mode безопаснее использовать <a>, экранируя и текст, и href.
        href = escape_html_text(wish.link)
        display = escape_html_text(display_link)
        lines.append(f"   🔗 <a href=\"{href}\">{display}</a>")
    if wish.description:
        lines.append(f"   💬 {escape_html_text(wish.description)}")
    if wish.image_url:
        image_url = escape_html_text(wish.image_url)
        lines.append(f"   🖼️ <a href=\"https://t.me/{image_url}\">Image URL</a>")
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
        return "Список желаний пуст.\n"

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
          "Название",
          "Ссылка",
          "Категория",
          "Описание",
          "Приоритет",
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


async def send_wish_list(message: Message, wishes: List[Wish], footer: str) -> None:
    for wish in wishes:
        if wish.image_url:
            await message.answer_photo(photo=wish.image_url, caption=build_wish_block(wish))
        elif wish.image:
            await message.answer_photo(photo=InputFile(wish.image), caption=build_wish_block(wish))
        else:
            await message.answer(build_wish_block(wish))
    if footer:
        await message.answer(footer)
