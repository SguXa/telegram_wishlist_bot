from aiogram import Router
from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()

EMPTY_WISH_LIST_HELP = (
    "📭 Список пуст. Нажмите «➕ Добавить»."
)


@router.message(Command("list"))
@router.message(F.text == "📋 Мой список")
@ensure_authorized(require_session=True)
async def cmd_list(message: Message, state: FSMContext) -> None:
    wishes = await get_storage().list_wishes(message.from_user.id)
    await send_wish_list(message, wishes, EMPTY_WISH_LIST_HELP)
