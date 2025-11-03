from typing import Optional
import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.exceptions import TelegramNetworkError

from bot.fsm import UserSession
from bot.keyboards import get_active_keyboard, get_logged_out_keyboard
from bot.shared_utils import get_storage
from core.config import AUTHORIZED_IDENTIFIERS, canonicalize_identifier
from core.formatting import escape_html_text

router = Router()


@router.message(Command("login"))
@router.message(StateFilter(UserSession.logged_out), Command("login"))
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
            await message.answer(
                "Авторизация прошла успешно! Основные команды доступны. Используйте /list или /help.",
                reply_markup=get_active_keyboard(),
            )
            return

        await state.set_state(UserSession.logged_out)
        if user:
            await get_storage().mark_session_inactive(user.id)
        user_id_text = identifiers_to_try[0] if identifiers_to_try else "unknown"
        username_text = next((value for value in identifiers_to_try if value.startswith("@")), None)
        failure_lines = [
            "Авторизация не выполнена. Убедитесь, что ваш Telegram ID или username внесены в список доступа.",
            f"ID: {escape_html_text(user_id_text)}",
        ]
        if username_text:
            failure_lines.append(f"Username: {escape_html_text(username_text)}")
        await message.answer("\n".join(failure_lines), reply_markup=get_logged_out_keyboard())
    except TelegramNetworkError as e:
        logging.error(f"Ошибка сети Telegram: {e}")
        await message.answer("Произошла ошибка сети. Попробуйте позже.")
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")


@router.message(F.text, StateFilter(UserSession.logged_out))
async def handle_logged_out_message(message: Message) -> None:
    if message.text in {"/login"}:
        return

    await message.answer(
        "Вы сейчас не авторизованы для работы с ботом. Выполните /login, чтобы продолжить.",
        reply_markup=get_logged_out_keyboard(),
    )
