from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.fsm import EditWish, UserSession
from bot.shared_utils import (
    describe_wish_for_confirmation,
    ensure_active_session,
    ensure_authorized,
    get_storage,
)

router = Router()


@router.callback_query(F.data.startswith("edit:"))
@ensure_active_session
async def callback_edit(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    wish_id = callback.data.split(":", 1)[1]
    wish = await storage.find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer(
            "Желание не найдено. Возможно, оно было изменено или удалено.",
            show_alert=True,
        )
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_field:{wish_id}:title")
    builder.button(text="Ссылка", callback_data=f"edit_field:{wish_id}:link")
    builder.button(text="Категория", callback_data=f"edit_field:{wish_id}:category")
    builder.button(text="Описание", callback_data=f"edit_field:{wish_id}:description")
    builder.button(text="Приоритет", callback_data=f"edit_field:{wish_id}:priority")
    builder.adjust(2)

    await callback.message.answer(
        "Что нужно изменить?\n\n"
        f"{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
@ensure_active_session
async def callback_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    _, wish_id, field = callback.data.split(":", 2)
    wish = storage.find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer(
            "Желание не найдено. Возможно, оно было изменено или удалено.",
            show_alert=True,
        )
        return

    prompts = {
        "title": "Введите новое название:",
        "link": "Укажите новую ссылку (или \"-\" если ее не будет):",
        "category": "Введите новую категорию:",
        "description": "Введите новое описание (или \"-\" если его не нужно):",
        "priority": "Введите новый приоритет от 1 до 5:",
    }

    await state.set_state(EditWish.waiting_value)
    await state.update_data(wish_id=wish_id, field=field)
    await callback.message.answer(prompts[field])
    await callback.answer()



@router.message(EditWish.waiting_value)
@ensure_authorized(reset_state=True)
async def process_edit_value(message: Message, state: FSMContext) -> None:
    storage = get_storage()
    data = await state.get_data()
    wish_id = data.get("wish_id")
    field = data.get("field")
    if not wish_id or not field:
        await message.answer(
            "Текущее действие устарело. Запустите /edit заново."
        )
        await state.clear()
        await state.set_state(UserSession.active)
        return

    new_value_raw = (message.text or "").strip()
    user_id = message.from_user.id

    if field == "priority":
        if not new_value_raw.isdigit():
            await message.answer(
                "Приоритет должен быть числом от 1 до 5. Попробуйте еще раз."
            )
            return
        priority = int(new_value_raw)
        if priority < 1 or priority > 5:
            await message.answer(
                "Приоритет выбирается в диапазоне от 1 до 5. Попробуйте еще раз."
            )
            return
        updated = await storage.update_wish_field(user_id, wish_id, "priority", priority)
    else:
        if field in {"link", "description"} and new_value_raw == "-":
            new_value = ""
        else:
            new_value = new_value_raw
        updated = await storage.update_wish_field(user_id, wish_id, field, new_value)

    if not updated:
        await message.answer(
            "Не удалось обновить желание. Попробуйте снова запустить /edit."
        )
    else:
        await message.answer(
            "Готово! Обновленная запись:\n\n" + describe_wish_for_confirmation(updated)
        )

    await state.clear()
    await state.set_state(UserSession.active)
