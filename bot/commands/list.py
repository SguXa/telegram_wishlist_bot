from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage, send_wish_list

router = Router()

EMPTY_WISH_LIST_HELP = (
    "Your wishlist is empty.\n"
    "Use /add to save the first item.\n\n"
    "Other useful commands:\n"
    "/list - show all wishes\n"
    "/edit - edit a wish\n"
    "/delete - remove a wish\n"
    "/others - view another user's list\n"
    "/categories - show category stats\n"
    "/search - search by text\n"
    "/export - download as TXT or CSV"
)


@router.message(Command("list"))
@ensure_authorized(require_session=True)
async def cmd_list(message: Message, state: FSMContext) -> None:
    wishes = await get_storage().list_wishes(message.from_user.id)
    await send_wish_list(message, wishes, EMPTY_WISH_LIST_HELP)
