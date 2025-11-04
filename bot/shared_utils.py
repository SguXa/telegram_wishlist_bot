from __future__ import annotations

import asyncio
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User
from aiogram.types.input_file import BufferedInputFile

from bot.fsm import UserSession
from core.config import (
    AUTHORIZED_IDENTIFIERS,
    AUTHORIZED_NUMERIC_IDS,
    canonicalize_identifier,
)
from core.formatting import DEFAULT_CATEGORY_TITLE, category_to_emoji, escape_html_text, sort_wishes_for_display
from core.models import Wish
from core.storage import Storage
from ui.keyboards import (
    build_wish_actions_keyboard,
    build_wish_card,
    main_menu_keyboard,
)

_storage: Optional[Storage] = None


def set_storage(instance: Storage) -> None:
    global _storage
    _storage = instance


def get_storage() -> Storage:
    if _storage is None:
        raise RuntimeError("Storage instance is not configured.")
    return _storage

SESSION_EXPIRED_MESSAGE = "⚠️ Ваша сессия истекла. Войдите снова через /login."


async def user_has_active_session(user_id: int) -> bool:
    return await get_storage().is_session_active(user_id)


async def _restore_active_state(state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None or current_state == UserSession.logged_out.state:
        await state.set_state(UserSession.active)


async def ensure_active_session_message(message: Message, state: FSMContext) -> bool:
    user = message.from_user
    if user is None:
        await message.answer(SESSION_EXPIRED_MESSAGE)
        return False

    if not await user_has_active_session(user.id):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        await get_storage().mark_session_inactive(user.id)
        await message.answer(SESSION_EXPIRED_MESSAGE)
        return False

    await _restore_active_state(state)
    return True




def is_authorized(user: Optional[User]) -> bool:
    if user is None:
        return False
    if str(user.id) in AUTHORIZED_IDENTIFIERS:
        return True
    username = user.username
    if username:
        handle = canonicalize_identifier(f"@{username}")
        if handle and handle in AUTHORIZED_IDENTIFIERS:
            return True
    return False


async def ensure_authorized_message(message: Message) -> bool:
    if not is_authorized(message.from_user):
        await message.answer(
            "У вас нет доступа к этому боту. "
            "Попросите администратора добавить ваш идентификатор."
        )
        return False
    return True


async def ensure_authorized_callback(callback: CallbackQuery) -> bool:
    if not is_authorized(callback.from_user):
        await callback.answer("Нет доступа.", show_alert=True)
        return False
    return True


async def ensure_active_session_callback(callback: CallbackQuery, state: FSMContext) -> bool:
    if not await ensure_authorized_callback(callback):
        return False

    user = callback.from_user
    if user is None:
        if callback.message:
            await callback.message.answer(SESSION_EXPIRED_MESSAGE)
        await callback.answer(SESSION_EXPIRED_MESSAGE, show_alert=True)
        return False

    if not await user_has_active_session(user.id):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        await get_storage().mark_session_inactive(user.id)
        if callback.message:
            await callback.message.answer(SESSION_EXPIRED_MESSAGE)
        await callback.answer(SESSION_EXPIRED_MESSAGE, show_alert=True)
        return False

    await _restore_active_state(state)
    return True


Handler = TypeVar("Handler", bound=Callable[..., Awaitable[Any]])


def ensure_authorized(
    _handler: Optional[Handler] = None,
    *,
    reset_state: bool = False,
    require_session: bool = False,
) -> Callable[..., Any]:
    def decorator(handler: Handler) -> Handler:
        @wraps(handler)
        async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
            state = _extract_state(args, kwargs)
            if not await ensure_authorized_message(message):
                if reset_state and state:
                    await state.clear()
                    await state.set_state(UserSession.logged_out)
                return None

            if require_session:
                if state is None:
                    raise RuntimeError('FSMContext is required when require_session=True.')
                if not await ensure_active_session_message(message, state):
                    return None

            return await handler(message, *args, **kwargs)

        return cast(Handler, wrapper)

    if _handler is not None:
        return decorator(_handler)
    return decorator


def ensure_active_session(handler: Handler) -> Handler:
    @wraps(handler)
    async def wrapper(callback: CallbackQuery, *args: Any, **kwargs: Any) -> Any:
        state = _extract_state(args, kwargs)
        if state is None:
            raise RuntimeError("FSMContext is required for ensure_active_session decorator.")
        if not await ensure_active_session_callback(callback, state):
            return None
        return await handler(callback, *args, **kwargs)

    return cast(Handler, wrapper)


def _extract_state(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Optional[FSMContext]:
    for value in (*args, *kwargs.values()):
        if isinstance(value, FSMContext):
            return value
    return None


def describe_wish_for_confirmation(wish: Wish) -> str:
    emoji = category_to_emoji(wish.category)
    category = escape_html_text(wish.category or DEFAULT_CATEGORY_TITLE)
    return f"{emoji} {category}\n{build_wish_card(wish)}"


MAX_CAPTION_LENGTH = 1024
MAX_MESSAGE_LENGTH = 4096


async def _send_with_retry(
    sender: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> Any:
    try:
        return await sender(*args, **kwargs)
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after)
        return await sender(*args, **kwargs)


def _chunk_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines():
        line_length = len(line)
        # ensure blank lines are preserved
        candidate_len = line_length + (1 if current else 0)

        if candidate_len > limit:
            # line itself is longer than limit -- hard split
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            for start in range(0, line_length, limit):
                slice_ = line[start : start + limit]
                if len(slice_) == limit:
                    chunks.append(slice_)
                else:
                    current = [slice_]
                    current_len = len(slice_)
            continue

        if current_len + candidate_len > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_length
        else:
            current.append(line)
            current_len += candidate_len

    if current:
        chunks.append("\n".join(current))

    return chunks or [text[:limit]]


async def _send_text(message: Message, text: str, *, reply_markup: Any = None) -> None:
    chunks = _chunk_text(text, MAX_MESSAGE_LENGTH)
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == 0 else None
        await _send_with_retry(message.answer, chunk, reply_markup=markup)


async def _send_photo_with_optional_text(
    message: Message,
    wish: Wish,
    caption: str,
    reply_markup: Any,
) -> None:
    photo_source: Any
    if wish.image_url:
        photo_source = wish.image_url
    elif wish.image:
        photo_source = BufferedInputFile(bytes(wish.image), filename=f"wish-{wish.id or 'image'}.jpg")
    else:
        await _send_text(message, caption, reply_markup=reply_markup)
        return

    caption_to_send = caption if len(caption) <= MAX_CAPTION_LENGTH else None

    try:
        await _send_with_retry(
            message.answer_photo,
            photo_source,
            caption=caption_to_send,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        logging.warning("Failed to send photo for wish %s: %s. Falling back to text output.", wish.id, exc)
        await _send_text(message, caption, reply_markup=reply_markup)
        return

    if caption_to_send is None:
        await _send_text(message, caption)


async def send_wish_list(
    message: Message,
    wishes: list[Wish],
    empty_text: str,
    *,
    show_actions: bool = True,
    title: str = "📋 Ваш список",
) -> None:
    if not wishes:
        await message.answer(empty_text, reply_markup=main_menu_keyboard())
        return

    await message.answer(title, reply_markup=main_menu_keyboard())
    for category, items in sort_wishes_for_display(wishes):
        for wish in items:
            caption = describe_wish_for_confirmation(wish)
            keyboard_markup = (
                build_wish_actions_keyboard(int(wish.id)) if show_actions and wish.id is not None else None
            )
            if wish.image_url or wish.image:
                await _send_photo_with_optional_text(message, wish, caption, keyboard_markup)
            else:
                await _send_text(message, caption, reply_markup=keyboard_markup)


def select_other_user(current_user_id: int) -> Optional[int]:
    current_key = str(current_user_id)
    for identifier in AUTHORIZED_NUMERIC_IDS:
        if identifier == current_key:
            continue
        return int(identifier)
    return None
