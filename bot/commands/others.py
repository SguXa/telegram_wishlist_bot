from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage, select_other_user, send_wish_list
from ui.keyboards import PARTNER_LIST_BUTTON

router = Router()

EMPTY_PARTNER_LIST = "📭 У партнёра пока пусто."


@router.message(Command("others"))
@router.message(F.text == PARTNER_LIST_BUTTON)
@ensure_authorized(require_session=True)
async def cmd_partner_list(message: Message, state: FSMContext) -> None:
    other_id = select_other_user(message.from_user.id)
    if other_id is None:
        await message.answer("⚠️ Партнёр не назначен.")
        return

    wishes = await get_storage().list_wishes(other_id)
    await send_wish_list(
        message,
        wishes,
        EMPTY_PARTNER_LIST,
        show_actions=False,
        title="💞 Список партнёра",
    )
