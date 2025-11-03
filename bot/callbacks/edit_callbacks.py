from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize
from aiogram.types.input_file import BufferedInputFile

from bot.fsm import EditWish, UserSession
from bot.shared_utils import (
    describe_wish_for_confirmation,
    ensure_active_session,
    ensure_authorized,
    get_storage,
    send_wish_list,
)
from core.models import Wish
from ui.keyboards import (
    build_edit_menu,
    build_photo_prompt_menu,
    build_priority_menu,
    cancel_input_keyboard,
    main_menu_keyboard,
)

router = Router()

MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024


@dataclass(frozen=True)
class EditCallbackData:
    action: str
    item_id: int
    value: Optional[str] = None


def _parse_edit_data(payload: str) -> Optional[EditCallbackData]:
    if not payload.startswith("edit:"):
        return None
    parts = payload.split(":")[1:]
    if not parts:
        return None

    if parts[0].isdigit():
        try:
            item_id = int(parts[0])
        except ValueError:
            return None
        value = parts[1] if len(parts) > 1 else None
        return EditCallbackData(action="card", item_id=item_id, value=value)

    action = parts[0]
    if len(parts) < 2:
        return None
    try:
        item_id = int(parts[1])
    except ValueError:
        return None
    value = parts[2] if len(parts) > 2 else None
    return EditCallbackData(action=action, item_id=item_id, value=value)


async def _load_wish_or_warn(callback: CallbackQuery, wish_id: int) -> Optional[Wish]:
    storage = get_storage()
    wish = await storage.find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer("⚠️ Элемент не найден", show_alert=True)
        return None
    return wish


async def _show_edit_card(message: Message, wish: Wish) -> None:
    caption = describe_wish_for_confirmation(wish)
    has_photo = bool(wish.image_url or wish.image)
    markup = build_edit_menu(int(wish.id), has_photo=has_photo)
    if wish.image_url:
        try:
            await message.answer_photo(wish.image_url, caption=caption, reply_markup=markup)
            return
        except TelegramBadRequest:
            pass
    if wish.image:
        try:
            await message.answer_photo(
                BufferedInputFile(bytes(wish.image), filename=f"wish-{wish.id}.jpg"),
                caption=caption,
                reply_markup=markup,
            )
            return
        except TelegramBadRequest:
            pass
    await message.answer(caption, reply_markup=markup)


def _largest_photo(photos: list[PhotoSize]) -> PhotoSize:
    return max(photos, key=lambda item: item.file_size or 0)


async def _download_photo_if_needed(message: Message, photo: PhotoSize) -> bytes | None:
    if not photo.file_size or photo.file_size > MAX_DOWNLOAD_SIZE or message.bot is None:
        return None
    buffer = await message.bot.download(photo)
    return buffer.getvalue()


@router.callback_query(F.data == "back_to_list")
@ensure_active_session
async def handle_back_to_list(callback: CallbackQuery, state: FSMContext) -> None:
    storage = get_storage()
    wishes = await storage.list_wishes(callback.from_user.id)
    await send_wish_list(callback.message, wishes, "📭 Список пуст. Нажмите «➕ Добавить».")
    await callback.answer()


@router.callback_query(F.data.startswith("edit:"))
@ensure_active_session
async def handle_edit_callback(callback: CallbackQuery, state: FSMContext) -> None:
    parsed = _parse_edit_data(callback.data or "")
    if parsed is None:
        await callback.answer("⚠️ Неизвестное действие", show_alert=True)
        return

    wish = await _load_wish_or_warn(callback, parsed.item_id)
    if wish is None:
        return

    if parsed.action == "card":
        await _show_edit_card(callback.message, wish)
        await callback.answer()
        return

    if parsed.action == "priority":
        await callback.message.answer("⭐ Выберите приоритет:", reply_markup=build_priority_menu(parsed.item_id))
        await callback.answer()
        return

    if parsed.action == "priority|set":
        if parsed.value is None or not parsed.value.isdigit():
            await callback.answer("⚠️ Некорректное значение", show_alert=True)
            return
        priority = int(parsed.value)
        if priority < 1 or priority > 5:
            await callback.answer("⚠️ Диапазон 1–5", show_alert=True)
            return
        updated = await get_storage().update_wish_priority(callback.from_user.id, parsed.item_id, priority)
        if updated is None:
            await callback.answer("⚠️ Не удалось обновить", show_alert=True)
            return
        await callback.message.answer("✅ Приоритет обновлён", reply_markup=main_menu_keyboard())
        await _show_edit_card(callback.message, updated)
        await callback.answer()
        return

    if parsed.action == "title":
        await state.set_state(EditWish.waiting_for_title)
        await state.update_data(wish_id=parsed.item_id)
        await callback.message.answer(
            "📝 Введите новое название",
            reply_markup=cancel_input_keyboard("Введите новое название"),
        )
        await callback.answer()
        return

    if parsed.action == "url":
        if parsed.value == "clear":
            updated = await get_storage().clear_wish_url(callback.from_user.id, parsed.item_id)
            if updated is None:
                await callback.answer("⚠️ Не удалось обновить", show_alert=True)
                return
            await callback.message.answer("🗑️ Ссылка очищена", reply_markup=main_menu_keyboard())
            await _show_edit_card(callback.message, updated)
            await callback.answer()
            return
        await state.set_state(EditWish.waiting_for_url)
        await state.update_data(wish_id=parsed.item_id)
        await callback.message.answer(
            "🔗 Отправьте новую ссылку",
            reply_markup=cancel_input_keyboard("Отправьте ссылку"),
        )
        await callback.answer()
        return

    if parsed.action == "photo":
        await state.set_state(EditWish.waiting_for_photo)
        await state.update_data(wish_id=parsed.item_id)
        await callback.message.answer(
            "🖼️ Отправьте новое изображение",
            reply_markup=cancel_input_keyboard("Отправьте фото"),
        )
        await callback.message.answer(
            "Вы можете убрать фото кнопкой ниже.",
            reply_markup=build_photo_prompt_menu(parsed.item_id),
        )
        await callback.answer()
        return

    if parsed.action == "photo|clear":
        updated = await get_storage().clear_wish_photo(callback.from_user.id, parsed.item_id)
        if updated is None:
            await callback.answer("⚠️ Не удалось удалить фото", show_alert=True)
            return
        await callback.message.answer("🗑️ Фото убрано", reply_markup=main_menu_keyboard())
        await _show_edit_card(callback.message, updated)
        await callback.answer()
        return

    await callback.answer("⚠️ Неизвестное действие", show_alert=True)


def _state_requires_edit(state_name: Optional[str]) -> bool:
    return state_name in {
        EditWish.waiting_for_title.state,
        EditWish.waiting_for_url.state,
        EditWish.waiting_for_photo.state,
    }


async def _return_to_card(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    wish_id = data.get("wish_id")
    await state.clear()
    await state.set_state(UserSession.active)
    if not wish_id:
        await message.answer("⚠️ Элемент не найден", reply_markup=main_menu_keyboard())
        return
    storage = get_storage()
    wish = await storage.find_wish(message.from_user.id, int(wish_id))
    if wish is None:
        await message.answer("⚠️ Элемент не найден", reply_markup=main_menu_keyboard())
        return
    await _show_edit_card(message, wish)


@router.message(F.text == "↩️ Отмена")
@ensure_authorized(require_session=True)
async def handle_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if not _state_requires_edit(current_state):
        return
    await message.answer("↩️ Отмена", reply_markup=main_menu_keyboard())
    await _return_to_card(message, state)


@router.message(EditWish.waiting_for_title)
@ensure_authorized(require_session=True)
async def handle_new_title(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw:
        await message.answer("⚠️ Название не может быть пустым")
        return
    if len(raw) > 120:
        await message.answer("⚠️ Слишком длинно, максимум 120 символов")
        return
    data = await state.get_data()
    wish_id = data.get("wish_id")
    if not wish_id:
        await message.answer("⚠️ Элемент не найден", reply_markup=main_menu_keyboard())
        await state.clear()
        await state.set_state(UserSession.active)
        return
    storage = get_storage()
    updated = await storage.update_wish_title(message.from_user.id, int(wish_id), raw)
    if updated is None:
        await message.answer("⚠️ Не удалось обновить", reply_markup=main_menu_keyboard())
    else:
        await message.answer("✅ Название обновлено", reply_markup=main_menu_keyboard())
        await _show_edit_card(message, updated)
    await state.clear()
    await state.set_state(UserSession.active)


def _is_valid_url(url: str) -> bool:
    if len(url) > 2048:
        return False
    if any(ch.isspace() for ch in url):
        return False
    lowered = url.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


@router.message(EditWish.waiting_for_url)
@ensure_authorized(require_session=True)
async def handle_new_url(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    data = await state.get_data()
    wish_id = data.get("wish_id")
    if not wish_id:
        await message.answer("⚠️ Элемент не найден", reply_markup=main_menu_keyboard())
        await state.clear()
        await state.set_state(UserSession.active)
        return
    storage = get_storage()
    if not raw:
        updated = await storage.clear_wish_url(message.from_user.id, int(wish_id))
        if updated is None:
            await message.answer("⚠️ Не удалось обновить", reply_markup=main_menu_keyboard())
        else:
            await message.answer("🗑️ Ссылка очищена", reply_markup=main_menu_keyboard())
            await _show_edit_card(message, updated)
        await state.clear()
        await state.set_state(UserSession.active)
        return
    if not _is_valid_url(raw):
        await message.answer("⚠️ Некорректная ссылка, попробуйте снова")
        return
    updated = await storage.update_wish_url(message.from_user.id, int(wish_id), raw)
    if updated is None:
        await message.answer("⚠️ Не удалось обновить", reply_markup=main_menu_keyboard())
    else:
        await message.answer("✅ Ссылка обновлена", reply_markup=main_menu_keyboard())
        await _show_edit_card(message, updated)
    await state.clear()
    await state.set_state(UserSession.active)


@router.message(EditWish.waiting_for_photo)
@ensure_authorized(require_session=True)
async def handle_new_photo(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("⚠️ Ожидалось фото, попробуйте ещё раз")
        return
    data = await state.get_data()
    wish_id = data.get("wish_id")
    if not wish_id:
        await message.answer("⚠️ Элемент не найден", reply_markup=main_menu_keyboard())
        await state.clear()
        await state.set_state(UserSession.active)
        return
    photo = _largest_photo(message.photo)
    file_id = photo.file_id
    image_bytes = await _download_photo_if_needed(message, photo)
    storage = get_storage()
    updated = await storage.update_wish_photo(
        message.from_user.id,
        int(wish_id),
        file_id=file_id,
        image_bytes=image_bytes,
    )
    if updated is None:
        await message.answer("⚠️ Не удалось обновить", reply_markup=main_menu_keyboard())
    else:
        await message.answer("✅ Фото обновлено", reply_markup=main_menu_keyboard())
        await _show_edit_card(message, updated)
    await state.clear()
    await state.set_state(UserSession.active)
