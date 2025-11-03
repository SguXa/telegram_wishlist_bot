from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from bot.fsm import UserSession
from bot.shared_utils import get_storage

router = Router()


@router.message(Command("logout"), StateFilter(UserSession.active))
async def cmd_logout(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserSession.logged_out)
    if message.from_user:
        await get_storage().mark_session_inactive(message.from_user.id)

    await message.answer(
        "Вы вышли из аккаунта. Чтобы снова войти, используйте /login.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("logout"), StateFilter(UserSession.logged_out, None))
async def cmd_logout_inactive(message: Message) -> None:
    await message.answer(
        "Вы еще не авторизованы. Используйте /login.",
        reply_markup=ReplyKeyboardRemove(),
    )
