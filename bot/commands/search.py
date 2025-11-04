from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()


@router.message(Command("search"))
@ensure_authorized(require_session=True)
async def cmd_search(message: Message, state: FSMContext, command: CommandObject) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("🔍 Укажите запрос: /search <текст>")
        return

    wishes = await get_storage().list_wishes(message.from_user.id)
    matched = [
        wish
        for wish in wishes
        if query.lower() in wish.title.lower() or (wish.description and query.lower() in wish.description.lower())
    ]
    if not matched:
        await message.answer("⚠️ Совпадений нет.")
        return

    await send_wish_list(message, matched, "⚠️ Совпадений нет.")
