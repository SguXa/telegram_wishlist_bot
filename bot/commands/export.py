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
    wishes = get_storage().list_wishes(message.from_user.id)
    if not wishes:
        await message.answer(
            "\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u043d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u0435\u043d: "
            "\u0441\u043f\u0438\u0441\u043e\u043a \u0436\u0435\u043b\u0430\u043d\u0438\u0439 \u043f\u0443\u0441\u0442. "
            "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0447\u0442\u043e-\u043d\u0438\u0431\u0443\u0434\u044c \u0447\u0435\u0440\u0435\u0437 /add."
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="TXT", callback_data="export:txt")
    builder.button(text="CSV", callback_data="export:csv")
    builder.adjust(2)
    await message.answer("\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0444\u043e\u0440\u043c\u0430\u0442 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430:", reply_markup=builder.as_markup())
