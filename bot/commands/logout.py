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
        "\u0412\u044b \u0432\u044b\u0448\u043b\u0438 \u0438\u0437 \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u0430. "
        "\u0427\u0442\u043e\u0431\u044b \u0441\u043d\u043e\u0432\u0430 \u0432\u043e\u0439\u0442\u0438, "
        "\u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 /login."
    )


@router.message(Command("logout"), StateFilter(UserSession.logged_out, None))
async def cmd_logout_inactive(message: Message) -> None:
    await message.answer(
        "\u0412\u044b \u0435\u0449\u0435 \u043d\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u044b. "
        "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 /login."
    )
