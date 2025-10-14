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
            "\u0416\u0435\u043b\u0430\u043d\u0438\u0435 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e. "
            "\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u043e, \u043e\u043d\u043e \u0443\u0436\u0435 \u0443\u0434\u0430\u043b\u0435\u043d\u043e.",
            show_alert=True,
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="\u0414\u0430, \u0443\u0434\u0430\u043b\u0438\u0442\u044c", callback_data=f"delete_confirm:{wish_id}")
    builder.button(text="\u041e\u0442\u043c\u0435\u043d\u0430", callback_data="cancel")
    builder.adjust(2)
    await callback.message.answer(
        "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u044d\u0442\u043e \u0436\u0435\u043b\u0430\u043d\u0438\u0435?\n\n"
        f"{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "cancel")
@ensure_active_session
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("\u041e\u0442\u043c\u0435\u043d\u0435\u043d\u043e.")


@router.callback_query(F.data.startswith("delete_confirm:"))
@ensure_active_session
async def callback_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    wish_id = callback.data.split(":", 1)[1]
    removed = await storage.delete_wish(callback.from_user.id, wish_id)
    if removed:
        await callback.message.answer("\u0416\u0435\u043b\u0430\u043d\u0438\u0435 \u0443\u0434\u0430\u043b\u0435\u043d\u043e.")
        await callback.answer()
    else:
        await callback.answer(
            "\u041d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c \u0443\u0434\u0430\u043b\u0438\u0442\u044c \u0436\u0435\u043b\u0430\u043d\u0438\u0435. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437.",
            show_alert=True,
        )
