from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.formatting import category_to_emoji, escape_html_text, _shorten_link_for_display
from core.models import Wish

MY_LIST_BUTTON = "📋 Мой список"
ADD_BUTTON = "➕ Добавить"
SETTINGS_BUTTON = "⚙️ Настройки"
PARTNER_LIST_BUTTON = "💞 Список партнёра"



def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=MY_LIST_BUTTON), KeyboardButton(text=ADD_BUTTON)],
        [KeyboardButton(text=PARTNER_LIST_BUTTON), KeyboardButton(text=SETTINGS_BUTTON)],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder=None,
        one_time_keyboard=False,
    )


def cancel_input_keyboard(placeholder: str) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text="↩️ Отмена")]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder=placeholder,
        one_time_keyboard=False,
    )


def logged_out_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text="🔐 Войти")]]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Нажмите «🔐 Войти»",
        one_time_keyboard=False,
    )


def build_wish_card(wish: Wish) -> str:
    title = escape_html_text(wish.title) if wish.title else "Без названия"
    emoji = category_to_emoji(wish.category) if wish.category else ""
    title_line = f"{emoji} <b>{title}</b>" if emoji else f"<b>{title}</b>"

    lines = [title_line]

    if wish.description:
        lines.append(escape_html_text(wish.description))

    if wish.link:
        display_link = _shorten_link_for_display(wish.link)
        href = escape_html_text(wish.link)
        display = escape_html_text(display_link)
        lines.append(f"🔗 <a href=\"{href}\">{display}</a>")

    meta_parts: list[str] = []
    if wish.priority is not None:
        meta_parts.append(f"⭐ Приоритет {wish.priority}/5")

    if meta_parts:
        lines.append(" · ".join(meta_parts))

    return "\n".join(lines)


def build_wish_actions_keyboard(wish_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:card:{wish_id}"),
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete:{wish_id}"),
    )
    return builder.as_markup()


def build_edit_menu(item_id: int, *, has_photo: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⭐ Приоритет", callback_data=f"edit:priority:{item_id}"))
    builder.row(InlineKeyboardButton(text="📝 Название", callback_data=f"edit:title:{item_id}"))
    builder.row(
        InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"edit:url:{item_id}"),
        InlineKeyboardButton(text="🗑️ Очистить", callback_data=f"edit:url:{item_id}:clear"),
    )
    photo_buttons = [InlineKeyboardButton(text="🖼️ Фото", callback_data=f"edit:photo:{item_id}")]
    if has_photo:
        photo_buttons.append(InlineKeyboardButton(text="🗑️ Убрать фото", callback_data=f"edit:photo|clear:{item_id}"))
    builder.row(*photo_buttons)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_list"))
    return builder.as_markup()


def build_priority_menu(item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value in range(1, 6):
        builder.button(text=str(value), callback_data=f"edit:priority|set:{item_id}:{value}")
    builder.adjust(5)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"edit:card:{item_id}"))
    return builder.as_markup()


def build_photo_prompt_menu(item_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ К желанию", callback_data=f"edit:card:{item_id}"))
    builder.row(InlineKeyboardButton(text="🗑️ Убрать фото", callback_data=f"edit:photo|clear:{item_id}"))
    return builder.as_markup()
