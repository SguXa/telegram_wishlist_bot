from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized, get_storage
from core.formatting import category_to_emoji, escape_html_text

router = Router()


@router.message(Command("categories"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_categories(message: Message) -> None:
    categories = get_storage().collect_categories()
    if not categories:
        await message.answer(
            "\u041a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0438 \u043f\u043e\u043a\u0430 \u043d\u0435 \u0441\u043e\u0437\u0434\u0430\u043d\u044b. "
            "\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0436\u0435\u043b\u0430\u043d\u0438\u044f \u0441 \u0443\u043a\u0430\u0437\u0430\u043d\u0438\u0435\u043c "
            "\u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u0439 \u0447\u0435\u0440\u0435\u0437 /add."
        )
        return

    lines = [f"{category_to_emoji(category)} {escape_html_text(category)}" for category in categories]
    await message.answer("\n".join(lines))
