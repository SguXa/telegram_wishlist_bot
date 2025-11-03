import re
from io import BytesIO
from typing import Optional
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, PhotoSize

from bot.fsm import AddWish, UserSession
from bot.shared_utils import ensure_authorized, get_storage
from core.models import Wish

router = Router()

_URL_PATTERN = re.compile(r"(?i)\bhttps?://\S+")
_TRAILING_PUNCTUATION = ".,!?:;\"')]>}"
_DEFAULT_PRIORITY = 3
_UNTITLED_PHOTO_TITLE = "Photo wish"


def _extract_title_and_link(text: Optional[str]) -> tuple[str, str]:
    if not text:
        return "", ""

    match = _URL_PATTERN.search(text)
    if not match:
        return text, ""

    raw_link = match.group(0)
    link = raw_link.rstrip(_TRAILING_PUNCTUATION)
    before = text[: match.start()].strip()
    after = text[match.end() :].strip()

    if before:
        title = before
    elif after:
        title = after
    else:
        title = link

    return title, link


def _is_cancel_command(text: Optional[str]) -> bool:
    if text is None:
        return False
    return text.strip().lower() in {"/cancel", "cancel", "stop"}


@router.message(Command("add"))
@ensure_authorized(require_session=True)
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWish.waiting_input)
    await message.answer("Send a wish title or link. Use /cancel to abort.")


@router.message(StateFilter(AddWish.waiting_input))
async def process_add_input(message: Message, state: FSMContext) -> None:
    raw_text = message.text if message.text is not None else message.caption

    if _is_cancel_command(raw_text):
        await state.clear()
        await message.answer("Adding wish canceled.")
        return

    title, link = _extract_title_and_link(raw_text)

    image = None
    image_url = None

    if message.photo:
        largest_photo: PhotoSize = message.photo[-1]
        image_url = largest_photo.file_id
        if (
            largest_photo.file_size
            and largest_photo.file_size <= 10 * 1024 * 1024
            and message.bot is not None
        ):
            buffer = BytesIO()
            await message.bot.download(largest_photo, destination=buffer)
            image = buffer.getvalue()

    if not title:
        title = _UNTITLED_PHOTO_TITLE if message.photo else "Untitled wish"

    wish = Wish(title=title, link=link, priority=_DEFAULT_PRIORITY, image=image, image_url=image_url)
    await get_storage().add_wish(message.from_user.id, wish)

    await state.clear()
    await message.answer("Wish added successfully!")
