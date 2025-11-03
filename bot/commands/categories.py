from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.shared_utils import ensure_authorized, get_storage
from core.formatting import category_to_emoji, escape_html_text

router = Router()


@router.message(Command("categories"))
@ensure_authorized(require_session=True)
async def cmd_categories(message: Message, state: FSMContext) -> None:
    categories = get_storage().collect_categories()
    if not categories:
        await message.answer(
            "Категории пока не созданы. Добавьте желания с указанием категорий через /add."
        )
        return

    lines = [f"{category_to_emoji(category)} {escape_html_text(category)}" for category in categories]
    await message.answer("\n".join(lines))
