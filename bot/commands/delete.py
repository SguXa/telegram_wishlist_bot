from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.fsm import UserSession
from bot.keyboards import truncate
from bot.shared_utils import ensure_authorized, get_storage

router = Router()


@router.message(Command("delete"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_delete(message: Message) -> None:
    wishes = get_storage().list_wishes(message.from_user.id)
    if not wishes:
        await message.answer(
            "Список желаний пуст. Удалять нечего."
        )
        return

    builder = InlineKeyboardBuilder()
    for wish in sorted(wishes, key=lambda w: w.title.casefold()):
        builder.button(text=f"Удалить {truncate(wish.title)}", callback_data=f"delete:{wish.id}")
    builder.adjust(1)
    await message.answer(
        "Выберите желание, которое хотите удалить:",
        reply_markup=builder.as_markup(),
    )