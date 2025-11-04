import logging
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import get_storage
from core.config import AUTHORIZED_IDENTIFIERS, canonicalize_identifier
from core.formatting import escape_html_text
from ui.keyboards import logged_out_keyboard, main_menu_keyboard

router = Router()


@router.message(Command("login"))
@router.message(StateFilter(UserSession.logged_out), Command("login"))
@router.message(StateFilter(UserSession.logged_out), F.text == "🔐 Войти")
async def cmd_login(message: Message, state: FSMContext) -> None:
    try:
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
            if user:
                await get_storage().mark_session_active(user.id)
            await message.answer("✅ Вход выполнен", reply_markup=main_menu_keyboard())
            return

        await state.set_state(UserSession.logged_out)
        if user:
            await get_storage().mark_session_inactive(user.id)
        user_id_text = identifiers_to_try[0] if identifiers_to_try else "unknown"
        username_text = next((value for value in identifiers_to_try if value.startswith("@")), None)
        lines = [
            "🚫 Нет доступа. Проверьте, что этот аккаунт есть в списке разрешённых.",
            f"ID: {escape_html_text(user_id_text)}",
        ]
        if username_text:
            lines.append(f"Username: {escape_html_text(username_text)}")
        await message.answer("\n".join(lines), reply_markup=logged_out_keyboard())
    except TelegramNetworkError as exc:
        logging.error("Ошибка сети Telegram: %s", exc)
        await message.answer("⚠️ Ошибка соединения. Попробуйте позже.", reply_markup=logged_out_keyboard())
    except Exception as exc:  # pragma: no cover
        logging.error("Неожиданная ошибка входа: %s", exc)
        await message.answer("⚠️ Что-то пошло не так. Попробуйте снова.", reply_markup=logged_out_keyboard())


@router.message(F.text, StateFilter(UserSession.logged_out))
async def handle_logged_out_message(message: Message) -> None:
    if message.text in {"/login", "🔐 Войти"}:
        return

    await message.answer(
        "🔒 Нажмите «🔐 Войти», чтобы авторизоваться.",
        reply_markup=logged_out_keyboard(),
    )
