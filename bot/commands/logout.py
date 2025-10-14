from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession

router = Router()


@router.message(Command("logout"), StateFilter(UserSession.active))
async def cmd_logout(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserSession.logged_out)

    await message.answer(
        "Вы вышли из аккаунта. Чтобы снова войти, используйте /login."
    )


@router.message(Command("logout"), StateFilter(UserSession.logged_out, None))
async def cmd_logout_inactive(message: Message) -> None:
    await message.answer(
        "Вы еще не авторизованы. Используйте /login."
    )