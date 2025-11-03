from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage

router = Router()


@router.message(Command("export"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_export(message: Message) -> None:
    wishes = await get_storage().list_wishes(message.from_user.id)
    if not wishes:
        await message.answer(
            "Экспорт невозможен: список желаний пуст. Добавьте что-нибудь через /add."
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="TXT", callback_data="export:txt")
    builder.button(text="CSV", callback_data="export:csv")
    builder.adjust(2)
    await message.answer("Выберите формат экспорта:", reply_markup=builder.as_markup())
