from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage, select_other_user, send_wish_list

router = Router()


@router.message(Command("others"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_others(message: Message) -> None:
    other_id = select_other_user(message.from_user.id)
    if other_id is None:
        await message.answer(
            "Не удалось определить другого доступного пользователя. "
            "Проверьте список AUTHORIZED_USER_IDS."
        )
        return

    wishes = await get_storage().list_wishes(other_id)
    await send_wish_list(
        message,
        wishes,
        "У этого пользователя пока нет желаний. "
        "Попросите его добавить их через /add.",
    )
