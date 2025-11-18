import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized
from ui.keyboards import CLEAR_HISTORY_BUTTON, main_menu_keyboard

router = Router()

_MAX_MESSAGES_TO_DELETE = 200


async def _wipe_recent_messages(message: Message, *, limit: int = _MAX_MESSAGES_TO_DELETE) -> int:
    """Best-effort removal of the bot's recent messages in the chat."""
    bot = message.bot
    from_chat = message.chat
    if bot is None or from_chat is None:
        return 0

    deleted = 0
    start_id = message.message_id
    stop_id = max(start_id - limit, 0)

    for message_id in range(start_id, stop_id, -1):
        try:
            await bot.delete_message(from_chat.id, message_id)
            deleted += 1
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if "message to delete not found" in error_text or "message can't be deleted" in error_text:
                continue
            logging.warning("Unexpected error while deleting message %s: %s", message_id, exc)
        except TelegramForbiddenError as exc:
            logging.warning("Bot lost permission to delete messages in chat %s: %s", from_chat.id, exc)
            break

    return deleted


@router.message(Command("clear_history"))
@router.message(F.text == CLEAR_HISTORY_BUTTON)
@ensure_authorized(require_session=True)
async def cmd_clear_history(message: Message, state: FSMContext) -> None:
    deleted = await _wipe_recent_messages(message)
    await message.answer(
        f"История очищена. Удалено {deleted} последних моих сообщений "
        "в пределах ограничений Telegram.",
        reply_markup=main_menu_keyboard(),
    )
