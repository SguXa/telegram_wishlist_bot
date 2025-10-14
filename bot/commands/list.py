from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()


@router.message(Command("list"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_list(message: Message) -> None:
    wishes = get_storage().list_wishes(message.from_user.id)
    await send_wish_list(
        message,
        wishes,
        "\u0412\u0430\u0448 \u0441\u043f\u0438\u0441\u043e\u043a \u0436\u0435\u043b\u0430\u043d\u0438\u0439 \u043f\u0443\u0441\u0442. "
        "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043d\u043e\u0432\u044b\u0435 \u043f\u043e\u0437\u0438\u0446\u0438\u0438 \u0447\u0435\u0440\u0435\u0437 /add.",
    )
