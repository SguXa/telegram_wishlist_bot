import re
from io import BytesIO
from typing import Optional
from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize

from bot.fsm import AddWish, UserSession
from bot.shared_utils import ensure_authorized, get_storage
from core.models import Wish
from ui.keyboards import ADD_BUTTON, cancel_input_keyboard, main_menu_keyboard

router = Router()

_URL_PATTERN = re.compile(r"(?i)\bhttps?://\S+")
_TRAILING_PUNCTUATION = ".,!?:;\"')]>}"
_DEFAULT_PRIORITY = 3
_UNTITLED_PHOTO_TITLE = "Желание без названия"
_FALLBACK_LINK_TITLE_TEMPLATE = "Ссылка с {source}"
_FALLBACK_LINK_TITLE_GENERIC = "Сохранённая ссылка"
_MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


def _extract_title_and_link(text: Optional[str]) -> tuple[str, str]:
    if not text:
        return "", ""

    match = _URL_PATTERN.search(text)
    if not match:
        return text.strip(), ""

    raw_link = match.group(0)
    link = raw_link.rstrip(_TRAILING_PUNCTUATION)
    before = text[: match.start()].strip()
    after = text[match.end() :].strip()

    if before:
        title = before
    elif after:
        title = after
    else:
        title = _generate_fallback_title(link)

    return title, link


def _generate_fallback_title(link: str) -> str:
    parsed = urlparse(link)
    source = parsed.netloc or parsed.path
    if source:
        source = source.split("/", 1)[0]
        if source.startswith("www."):
            source = source[4:]
        if source:
            return _FALLBACK_LINK_TITLE_TEMPLATE.format(source=source)
    return _FALLBACK_LINK_TITLE_GENERIC


def _is_cancel_command(text: Optional[str]) -> bool:
    if text is None:
        return False
    normalized = text.strip().lower()
    return normalized in {"/cancel", "cancel", "stop", "↩️ отмена", "отмена"}


async def _download_photo_if_needed(message: Message, photo: PhotoSize) -> bytes | None:
    if not photo.file_size or photo.file_size > _MAX_DOWNLOAD_SIZE or message.bot is None:
        return None
    buffer = BytesIO()
    await message.bot.download(photo, destination=buffer)
    return buffer.getvalue()


async def _cancel_addition(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserSession.active)
    await message.answer("↩️ Отменено", reply_markup=main_menu_keyboard())


@router.message(Command("add"))
@router.message(F.text == ADD_BUTTON)
@ensure_authorized(require_session=True)
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWish.waiting_input)
    await message.answer(
        "➕ Отправьте название, ссылку или фото желания",
        reply_markup=cancel_input_keyboard("Опишите желание"),
    )


@router.message(StateFilter(AddWish.waiting_input))
@ensure_authorized(require_session=True)
async def process_add_input(message: Message, state: FSMContext) -> None:
    raw_text = message.text if message.text is not None else message.caption

    if _is_cancel_command(message.text):
        await _cancel_addition(message, state)
        return

    if raw_text is None and not message.photo:
        await message.answer("⚠️ Отправьте текст, ссылку или фото")
        return

    title, link = _extract_title_and_link(raw_text)

    image = None
    image_url = None

    if message.photo:
        largest_photo = max(message.photo, key=lambda item: item.file_size or 0)
        image_url = largest_photo.file_id
        image = await _download_photo_if_needed(message, largest_photo)

    if not title:
        title = _UNTITLED_PHOTO_TITLE if message.photo else "Новое желание"

    wish = Wish(title=title, link=link, priority=_DEFAULT_PRIORITY, image=image, image_url=image_url)
    await get_storage().add_wish(message.from_user.id, wish)

    await state.clear()
    await state.set_state(UserSession.active)
    await message.answer("✅ Желание добавлено", reply_markup=main_menu_keyboard())
