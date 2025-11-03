from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.shared_utils import describe_wish_for_confirmation, ensure_active_session, get_storage, send_wish_list
from ui.keyboards import main_menu_keyboard

router = Router()


@router.callback_query(F.data.startswith("delete:"))
@ensure_active_session
async def callback_delete(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    payload = callback.data.split(":", 1)[1]
    try:
        wish_id = int(payload)
    except ValueError:
        await callback.answer("⚠️ Некорректный идентификатор", show_alert=True)
        return

    wish = await storage.find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer("⚠️ Элемент не найден", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Удалить", callback_data=f"delete_confirm:{wish_id}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="cancel"),
    )

    await callback.message.answer(
        "❌ Удалить это желание?\n\n" f"{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
@ensure_active_session
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("↩️ Отмена")


@router.callback_query(F.data.startswith("delete_confirm:"))
@ensure_active_session
async def callback_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    payload = callback.data.split(":", 1)[1]
    try:
        wish_id = int(payload)
    except ValueError:
        await callback.answer("⚠️ Некорректный идентификатор", show_alert=True)
        return

    removed = await storage.delete_wish(callback.from_user.id, wish_id)
    if not removed:
        await callback.answer("⚠️ Не удалось удалить", show_alert=True)
        return

    await callback.message.answer("🗑️ Удалено", reply_markup=main_menu_keyboard())
    wishes = await storage.list_wishes(callback.from_user.id)
    await send_wish_list(
        callback.message,
        wishes,
        "📭 Список пуст. Нажмите «➕ Добавить».",
    )
    await callback.answer()
