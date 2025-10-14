from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.shared_utils import describe_wish_for_confirmation, ensure_active_session, get_storage

router = Router()


@router.callback_query(F.data.startswith("delete:"))
@ensure_active_session
async def callback_delete(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    wish_id = callback.data.split(":", 1)[1]
    wish = storage.find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer(
            "Желание не найдено. Возможно, оно уже удалено.",
            show_alert=True,
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить", callback_data=f"delete_confirm:{wish_id}")
    builder.button(text="Отмена", callback_data="cancel")
    builder.adjust(2)
    await callback.message.answer(
        "Удалить это желание?\n\n"
        f"{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "cancel")
@ensure_active_session
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Отменено.")


@router.callback_query(F.data.startswith("delete_confirm:"))
@ensure_active_session
async def callback_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    wish_id = callback.data.split(":", 1)[1]
    removed = await storage.delete_wish(callback.from_user.id, wish_id)
    if removed:
        await callback.message.answer("Желание удалено.")
        await callback.answer()
    else:
        await callback.answer(
            "Не получилось удалить желание. Попробуйте еще раз.",
            show_alert=True,
        )
