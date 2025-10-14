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
            "\u0423 \u0432\u0430\u0441 \u043d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430 \u043a \u044d\u0442\u043e\u043c\u0443 \u0431\u043e\u0442\u0443. "
            "\u041f\u043e\u043f\u0440\u043e\u0441\u0438\u0442\u0435 \u0430\u0434\u043c\u0438\u043d\u0438\u0441\u0442\u0440\u0430\u0442\u043e\u0440\u0430 "
            "\u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0432\u0430\u0448 \u0438\u0434\u0435\u043d\u0442\u0438\u0444\u0438\u043a\u0430\u0442\u043e\u0440."
        )
        return False
    return True


async def ensure_authorized_callback(callback: CallbackQuery) -> bool:
    if not is_authorized(callback.from_user):
        await callback.answer("\u041d\u0435\u0442 \u0434\u043e\u0441\u0442\u0443\u043f\u0430.", show_alert=True)
        return False
    return True


async def ensure_active_session_callback(callback: CallbackQuery, state: FSMContext) -> bool:
    if not await ensure_authorized_callback(callback):
        return False

    current_state = await state.get_state()
    if current_state != UserSession.active.state:
        await callback.answer(
            "\u0421\u0435\u0430\u043d\u0441 \u043d\u0435 \u0430\u043a\u0442\u0438\u0432\u0435\u043d. "
            "\u041f\u043e\u0436\u0430\u043b\u0443\u0439\u0441\u0442\u0430, \u0432\u044b\u043f\u043e\u043b\u043d\u0438\u0442\u0435 /login, "
            "\u0447\u0442\u043e\u0431\u044b \u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c.",
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
