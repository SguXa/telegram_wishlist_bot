from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.keyboards import get_active_keyboard, get_logged_out_keyboard
from core.config import AUTHORIZED_IDENTIFIERS, canonicalize_identifier
from core.formatting import escape_html_text

router = Router()


@router.message(Command("login"))
@router.message(StateFilter(UserSession.logged_out), Command("login"))
async def cmd_login(message: Message, state: FSMContext) -> None:
    user = message.from_user
    identifiers_to_try: list[str] = []
    if user:
        identifiers_to_try.append(str(user.id))
        if user.username:
            identifiers_to_try.append(f"@{user.username}")

    matched_identifier: Optional[str] = None
    for raw_identifier in identifiers_to_try:
        normalized = canonicalize_identifier(raw_identifier)
        if normalized and normalized in AUTHORIZED_IDENTIFIERS:
            matched_identifier = normalized
            break

    if matched_identifier:
        await state.clear()
        await state.set_state(UserSession.active)
        await message.answer(
            "\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u0440\u043e\u0448\u043b\u0430 \u0443\u0441\u043f\u0435\u0448\u043d\u043e! "
            "\u041e\u0441\u043d\u043e\u0432\u043d\u044b\u0435 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b. "
            "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 /list \u0438\u043b\u0438 /help.",
            reply_markup=get_active_keyboard(),
        )
        return

    await state.set_state(UserSession.logged_out)
    user_id_text = identifiers_to_try[0] if identifiers_to_try else "unknown"
    username_text = next((value for value in identifiers_to_try if value.startswith("@")), None)
    failure_lines = [
        "\u0410\u0432\u0442\u043e\u0440\u0438\u0437\u0430\u0446\u0438\u044f \u043d\u0435 \u0432\u044b\u043f\u043e\u043b\u043d\u0435\u043d\u0430. "
        "\u0423\u0431\u0435\u0434\u0438\u0442\u0435\u0441\u044c, \u0447\u0442\u043e \u0432\u0430\u0448 Telegram ID \u0438\u043b\u0438 username "
        "\u0432\u043d\u0435\u0441\u0435\u043d\u044b \u0432 \u0441\u043f\u0438\u0441\u043e\u043a \u0434\u043e\u0441\u0442\u0443\u043f\u0430.",
        f"ID: {escape_html_text(user_id_text)}",
    ]
    if username_text:
        failure_lines.append(f"Username: {escape_html_text(username_text)}")
    await message.answer("\n".join(failure_lines), reply_markup=get_logged_out_keyboard())


@router.message(F.text, StateFilter(UserSession.logged_out))
async def handle_logged_out_message(message: Message) -> None:
    if message.text in {"/login"}:
        return

    await message.answer(
        "\u0412\u044b \u0441\u0435\u0439\u0447\u0430\u0441 \u043d\u0435 \u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u044b "
        "\u0434\u043b\u044f \u0440\u0430\u0431\u043e\u0442\u044b \u0441 \u0431\u043e\u0442\u043e\u043c. "
        "\u0412\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 /login, \u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c.",
        reply_markup=get_logged_out_keyboard(),
    )
