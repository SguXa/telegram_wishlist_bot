from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()


@router.message(Command("search"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_search(message: Message, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u0437\u0430\u043f\u0440\u043e\u0441: /search <\u0441\u043b\u043e\u0432\u043e>")
        return

    wishes = get_storage().list_wishes(message.from_user.id)
    matched = [
        wish
        for wish in wishes
        if query.lower() in wish.title.lower() or query.lower() in wish.description.lower()
    ]
    if not matched:
        await message.answer("\u0421\u043e\u0432\u043f\u0430\u0434\u0435\u043d\u0438\u0439 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
        return

    await send_wish_list(message, matched, "\u0421\u043e\u0432\u043f\u0430\u0434\u0435\u043d\u0438\u0439 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e.")
