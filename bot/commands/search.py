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
        await message.answer("Укажите запрос: /search <слово>")
        return

    wishes = await get_storage().list_wishes(message.from_user.id)
    matched = [
        wish
        for wish in wishes
        if query.lower() in wish.title.lower() or query.lower() in wish.description.lower()
    ]
    if not matched:
        await message.answer("Совпадений не найдено.")
        return

    await send_wish_list(message, matched, "Совпадений не найдено.")
