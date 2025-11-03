import re
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


def _extract_title_and_link(text: str) -> tuple[str, str]:
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


def _is_cancel_command(text: str) -> bool:
    return text in {"/cancel", "cancel", "stop"}


@router.message(Command("add"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWish.waiting_input)
    await message.answer("Send a wish title or link. Use /cancel to abort.")


@router.message(StateFilter(AddWish.waiting_input))
async def process_add_input(message: Message, state: FSMContext) -> None:
    if _is_cancel_command(message.text):
        await state.clear()
        await message.answer("Adding wish canceled.")
        return

    title, link = _extract_title_and_link(message.text)

    image = None
    image_url = None

    if message.photo:
        largest_photo: PhotoSize = message.photo[-1]
        image_url = largest_photo.file_id
        if largest_photo.file_size <= 10 * 1024 * 1024:  # Ограничение 10 МБ
            image = await largest_photo.download(destination=bytes)

    wish = Wish(title=title, link=link, priority=_DEFAULT_PRIORITY, image=image, image_url=image_url)
    await get_storage().add_wish(message.from_user.id, wish)

    await state.clear()
    await message.answer("Wish added successfully!")
