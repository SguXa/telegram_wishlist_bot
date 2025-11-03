from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized

router = Router()


@router.message(Command("help"))
@ensure_authorized(require_session=True)
async def cmd_help(message: Message, state: FSMContext) -> None:
    help_text = (
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
    await message.answer(help_text)
