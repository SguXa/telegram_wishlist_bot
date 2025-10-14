from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery

from bot.shared_utils import ensure_active_session, get_storage
from core.formatting import compose_export_csv, compose_export_txt

router = Router()


@router.callback_query(F.data.startswith("export:"))
@ensure_active_session
async def callback_export(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    format_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    wishes = storage.list_wishes(user_id)

    if format_name == "txt":
        content = compose_export_txt(wishes)
        file = BufferedInputFile(content.encode("utf-8"), filename="wishlist.txt")
    elif format_name == "csv":
        content = compose_export_csv(wishes)
        file = BufferedInputFile(content.encode("utf-8"), filename="wishlist.csv")
    else:
        await callback.answer("Неизвестный формат экспорта.", show_alert=True)
        return

    await callback.message.answer_document(file)
    await callback.answer("Экспорт готов!")
