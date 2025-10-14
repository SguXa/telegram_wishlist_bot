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
        await callback.answer("\u041d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442 \u044d\u043a\u0441\u043f\u043e\u0440\u0442\u0430.", show_alert=True)
        return

    await callback.message.answer_document(file)
    await callback.answer("\u042d\u043a\u0441\u043f\u043e\u0440\u0442 \u0433\u043e\u0442\u043e\u0432!")
