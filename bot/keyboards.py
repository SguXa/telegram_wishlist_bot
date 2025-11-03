from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.models import Wish


def truncate(text: str, limit: int = 24) -> str:
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def build_list_actions_keyboard(wishes: list[Wish]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for wish in wishes:
        builder.row(
            InlineKeyboardButton(
                text=f"Редактировать",
                callback_data=f"edit:{wish.id}",
            ),
            InlineKeyboardButton(text="Удалить", callback_data=f"delete:{wish.id}"),
        )
    return builder


def get_active_keyboard() -> ReplyKeyboardMarkup:
    builder = [
        [KeyboardButton(text="/add"), KeyboardButton(text="/list"), KeyboardButton(text="/help")],
        [KeyboardButton(text="/edit"), KeyboardButton(text="/delete"), KeyboardButton(text="/others")],
        [KeyboardButton(text="/search"), KeyboardButton(text="/categories"), KeyboardButton(text="/export")],
        [KeyboardButton(text="/logout")],
    ]
    return ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True, one_time_keyboard=False)


def get_logged_out_keyboard() -> ReplyKeyboardMarkup:
    builder = [[KeyboardButton(text="/login")]]
    return ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True, one_time_keyboard=False)
