from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()


@router.message(Command("list"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_list(message: Message) -> None:
    wishes = await get_storage().list_wishes(message.from_user.id)
    await send_wish_list(
        message,
        wishes,
       "Доступные команды:\n"
"/add - добавить желание в список.\n"
"/list - показать ваши желания.\n"
"/edit - изменить существующее желание.\n"
"/delete - удалить желание.\n"
"/others - посмотреть списки друзей.\n"
"/categories - просмотреть категории.\n"
"/search - выполнить поиск по желаниям.\n"
"/export - выгрузить список в TXT или CSV."
    )
