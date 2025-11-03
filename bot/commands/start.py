from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.keyboards import get_active_keyboard, get_logged_out_keyboard
from bot.shared_utils import get_storage, is_authorized

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user

    await state.clear()
    reply_markup = get_logged_out_keyboard()

    if is_authorized(user):
        await state.set_state(UserSession.active)
        if user:
            await get_storage().mark_session_active(user.id)
        reply_markup = get_active_keyboard()
        greeting = (
            "Привет! Вы авторизованы и можете управлять своим списком желаний.\n"
        "Воспользуйтесь /help, чтобы посмотреть доступные команды."
        )
    else:
        await state.set_state(UserSession.logged_out)
        if user:
            await get_storage().mark_session_inactive(user.id)
        greeting = (
            "Привет! Похоже, ваш аккаунт пока не добавлен в список разрешённых пользователей. "
        "Передайте администратору ваш Telegram ID или username и после подключения выполните /login."
        )

    await message.answer(greeting, reply_markup=reply_markup)
