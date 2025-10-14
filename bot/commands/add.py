from uuid import uuid4

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import AddWish, UserSession
from bot.shared_utils import ensure_authorized, get_storage
from core.models import Wish

router = Router()


@router.message(Command("add"), StateFilter(UserSession.active))
@ensure_authorized
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWish.title)
    await message.answer("Введите название желания:")


@router.message(AddWish.title)
@ensure_authorized(reset_state=True)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(
            "Название не может быть пустым. Попробуйте еще раз."
        )
        return
    await state.update_data(title=title)
    await state.set_state(AddWish.link)
    await message.answer("Укажите ссылку (или \"-\" если ее нет):")


@router.message(AddWish.link)
@ensure_authorized(reset_state=True)
async def add_link(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    link = "" if raw in {"", "-"} else raw
    await state.update_data(link=link)
    await state.set_state(AddWish.category)
    await message.answer("Укажите категорию (или \"-\" если ее нет):")


@router.message(AddWish.category)
@ensure_authorized(reset_state=True)
async def add_category(message: Message, state: FSMContext) -> None:
    category = (message.text or "").strip()
    await state.update_data(category=category if category != "-" else "")
    await state.set_state(AddWish.description)
    await message.answer("Добавьте описание (или \"-\" если его нет):")


@router.message(AddWish.description)
@ensure_authorized(reset_state=True)
async def add_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    description = "" if raw in {"", "-"} else raw
    await state.update_data(description=description)
    await state.set_state(AddWish.priority)
    await message.answer("Укажите приоритет от 1 до 5:")


@router.message(AddWish.priority)
@ensure_authorized(reset_state=True)
async def add_priority(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(
            "Приоритет должен быть числом от 1 до 5. Попробуйте еще раз:"
        )
        return
    priority = int(raw)
    if priority < 1 or priority > 5:
        await message.answer(
            "Приоритет выбирается в диапазоне от 1 до 5. Попробуйте еще раз:"
        )
        return

    state_data = await state.get_data()
    wish = Wish(
        id=uuid4().hex,
        title=state_data["title"],
        link=state_data.get("link", ""),
        category=state_data.get("category", ""),
        description=state_data.get("description", ""),
        priority=priority,
    )
    await get_storage().add_wish(message.from_user.id, wish)
    await state.clear()
    await state.set_state(UserSession.active)
    await message.answer("Желание добавлено!")
    await message.answer("Посмотрите все желания через /list.")
