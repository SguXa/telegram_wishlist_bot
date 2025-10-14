from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar, cast

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from bot.fsm import UserSession
from bot.keyboards import build_list_actions_keyboard
from core.config import (
    AUTHORIZED_IDENTIFIERS,
    AUTHORIZED_NUMERIC_IDS,
    canonicalize_identifier,
)
from core.formatting import (
    DEFAULT_CATEGORY_TITLE,
    build_wish_block,
    category_to_emoji,
    escape_html_text,
    sort_wishes_for_display,
)
from core.models import Wish
from core.storage import Storage

_storage: Optional[Storage] = None


def set_storage(instance: Storage) -> None:
    global _storage
    _storage = instance


def get_storage() -> Storage:
    if _storage is None:
        raise RuntimeError("Storage instance is not configured.")
    return _storage


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

    current_state = await state.get_state()
    if current_state != UserSession.active.state:
        await callback.answer(
            "Сеанс не активен. Пожалуйста, выполните /login, чтобы продолжить.",
            show_alert=True,
        )
        return False
    return True


Handler = TypeVar("Handler", bound=Callable[..., Awaitable[Any]])


def ensure_authorized(_handler: Optional[Handler] = None, *, reset_state: bool = False) -> Callable[..., Any]:
    def decorator(handler: Handler) -> Handler:
        @wraps(handler)
        async def wrapper(message: Message, *args: Any, **kwargs: Any) -> Any:
            state = _extract_state(args, kwargs)
            if not await ensure_authorized_message(message):
                if reset_state and state:
                    await state.clear()
                    await state.set_state(UserSession.logged_out)
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
    return f"{emoji} {category}\n{build_wish_block(wish)}"


async def send_wish_list(message: Message, wishes: list[Wish], empty_text: str) -> None:
    if not wishes:
        await message.answer(empty_text)
        return

    for category, items in sort_wishes_for_display(wishes):
        emoji = category_to_emoji(category if category != DEFAULT_CATEGORY_TITLE else "")
        text_lines = [f"{emoji} {escape_html_text(category)}"]
        for wish in items:
            text_lines.append(build_wish_block(wish))
            text_lines.append("")
        payload = "\n".join(text_lines).strip()
        keyboard = build_list_actions_keyboard(items)
        await message.answer(payload, reply_markup=keyboard.as_markup())


def select_other_user(current_user_id: int) -> Optional[int]:
    current_key = str(current_user_id)
    for identifier in AUTHORIZED_NUMERIC_IDS:
        if identifier == current_key:
            continue
        return int(identifier)
    return None
