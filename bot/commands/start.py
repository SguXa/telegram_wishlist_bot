from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import get_storage, is_authorized
from ui.keyboards import logged_out_keyboard, main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user

    await state.clear()

    if is_authorized(user):
        await state.set_state(UserSession.active)
        if user:
            await get_storage().mark_session_active(user.id)
        await message.answer("👋 Привет! Главное меню всегда под полем ввода.", reply_markup=main_menu_keyboard())
    else:
        await state.set_state(UserSession.logged_out)
        if user:
            await get_storage().mark_session_inactive(user.id)
        await message.answer("🔒 Доступ ограничен. Нажмите «🔐 Войти».", reply_markup=logged_out_keyboard())
