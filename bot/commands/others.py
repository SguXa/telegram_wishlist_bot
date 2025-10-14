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
            "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u044c "
            "\u0434\u0440\u0443\u0433\u043e\u0433\u043e \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u043e\u0433\u043e "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 "
            "\u0441\u043f\u0438\u0441\u043e\u043a AUTHORIZED_USER_IDS."
        )
        return

    wishes = get_storage().list_wishes(other_id)
    await send_wish_list(
        message,
        wishes,
        "\u0423 \u044d\u0442\u043e\u0433\u043e \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f "
        "\u043f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0436\u0435\u043b\u0430\u043d\u0438\u0439. "
        "\u041f\u043e\u043f\u0440\u043e\u0441\u0438\u0442\u0435 \u0435\u0433\u043e \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c "
        "\u0438\u0445 \u0447\u0435\u0440\u0435\u0437 /add.",
    )
