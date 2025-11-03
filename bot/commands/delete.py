from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage, send_wish_list
from ui.keyboards import main_menu_keyboard

router = Router()

EMPTY_PROMPT = "📭 Список пуст. Нажмите «➕ Добавить»."


@router.message(Command("delete"))
@ensure_authorized(require_session=True)
async def cmd_delete(message: Message, state: FSMContext) -> None:
    wishes = await get_storage().list_wishes(message.from_user.id)
    if not wishes:
        await message.answer(EMPTY_PROMPT, reply_markup=main_menu_keyboard())
        return

    await message.answer("❌ Выберите, что удалить")
    await send_wish_list(message, wishes, EMPTY_PROMPT)
