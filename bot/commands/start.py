from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.keyboards import get_active_keyboard, get_logged_out_keyboard
from bot.shared_utils import is_authorized

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user

    await state.clear()
    reply_markup = get_logged_out_keyboard()

    if is_authorized(user):
        await state.set_state(UserSession.active)
        reply_markup = get_active_keyboard()
        greeting = (
            "\u041f\u0440\u0438\u0432\u0435\u0442! \u0412\u044b \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u044b "
            "\u0438 \u043c\u043e\u0436\u0435\u0442\u0435 \u0443\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u0441\u0432\u043e\u0438\u043c "
            "\u0441\u043f\u0438\u0441\u043a\u043e\u043c \u0436\u0435\u043b\u0430\u043d\u0438\u0439.\n"
            "\u0412\u043e\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435\u0441\u044c /help, \u0447\u0442\u043e\u0431\u044b "
            "\u043f\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u044b."
        )
    else:
        await state.set_state(UserSession.logged_out)
        greeting = (
            "\u041f\u0440\u0438\u0432\u0435\u0442! \u041f\u043e\u0445\u043e\u0436\u0435, \u0432\u0430\u0448 \u0430\u043a\u043a\u0430\u0443\u043d\u0442 "
            "\u043f\u043e\u043a\u0430 \u043d\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d \u0432 \u0441\u043f\u0438\u0441\u043e\u043a "
            "\u0440\u0430\u0437\u0440\u0435\u0448\u0435\u043d\u043d\u044b\u0445 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u0435\u0439. "
            "\u041f\u0435\u0440\u0435\u0434\u0430\u0439\u0442\u0435 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0443 "
            "\u0432\u0430\u0448 Telegram ID \u0438\u043b\u0438 username \u0438 \u043f\u043e\u0441\u043b\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f "
            "\u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 /login."
        )

    await message.answer(greeting, reply_markup=reply_markup)
