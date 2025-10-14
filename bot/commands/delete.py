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
            "\u0421\u043f\u0438\u0441\u043e\u043a \u0436\u0435\u043b\u0430\u043d\u0438\u0439 \u043f\u0443\u0441\u0442. "
            "\u0423\u0434\u0430\u043b\u044f\u0442\u044c \u043d\u0435\u0447\u0435\u0433\u043e."
        )
        return

    builder = InlineKeyboardBuilder()
    for wish in sorted(wishes, key=lambda w: w.title.casefold()):
        builder.button(text=f"\u0423\u0434\u0430\u043b\u0438\u0442\u044c {truncate(wish.title)}", callback_data=f"delete:{wish.id}")
    builder.adjust(1)
    await message.answer(
        "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0436\u0435\u043b\u0430\u043d\u0438\u0435, \u043a\u043e\u0442\u043e\u0440\u043e\u0435 "
        "\u0445\u043e\u0442\u0438\u0442\u0435 \u0443\u0434\u0430\u043b\u0438\u0442\u044c:",
        reply_markup=builder.as_markup(),
    )
