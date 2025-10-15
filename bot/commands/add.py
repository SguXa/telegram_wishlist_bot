import re
from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

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


@router.message(AddWish.waiting_input)
@ensure_authorized(reset_state=True)
async def add_wish_simple(message: Message, state: FSMContext) -> None:
    photo_file_id = message.photo[-1].file_id if message.photo else ""
    raw_text = message.caption if photo_file_id else message.text
    text = (raw_text or "").strip()

    if text and _is_cancel_command(text.lower()):
        await state.clear()
        await state.set_state(UserSession.active)
        await message.answer("Got it, cancelled.")
        return

    title = ""
    link = ""
    if text:
        title, link = _extract_title_and_link(text)

    if not title and not link:
        if photo_file_id:
            title = _UNTITLED_PHOTO_TITLE
        else:
            await message.answer("Please send a wish title or a link:")
            return

    if not title and not link:
        title = _UNTITLED_PHOTO_TITLE

    wish = Wish(
        id=uuid4().hex,
        title=title or link,
        link=link,
        category="",
        description="",
        priority=_DEFAULT_PRIORITY,
        photo_file_id=photo_file_id,
    )

    await get_storage().add_wish(message.from_user.id, wish)
    await state.clear()
    await state.set_state(UserSession.active)
    await message.answer("Saved! Check /list to see everything.")
