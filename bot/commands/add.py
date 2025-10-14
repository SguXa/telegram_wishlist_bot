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
    await message.answer("\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u0436\u0435\u043b\u0430\u043d\u0438\u044f:")


@router.message(AddWish.title)
@ensure_authorized(reset_state=True)
async def add_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(
            "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043d\u0435 \u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c \u043f\u0443\u0441\u0442\u044b\u043c. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437."
        )
        return
    await state.update_data(title=title)
    await state.set_state(AddWish.link)
    await message.answer("\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443 (\u0438\u043b\u0438 \"-\" \u0435\u0441\u043b\u0438 \u0435\u0435 \u043d\u0435\u0442):")


@router.message(AddWish.link)
@ensure_authorized(reset_state=True)
async def add_link(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    link = "" if raw in {"", "-"} else raw
    await state.update_data(link=link)
    await state.set_state(AddWish.category)
    await message.answer("\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u043a\u0430\u0442\u0435\u0433\u043e\u0440\u0438\u044e (\u0438\u043b\u0438 \"-\" \u0435\u0441\u043b\u0438 \u0435\u0435 \u043d\u0435\u0442):")


@router.message(AddWish.category)
@ensure_authorized(reset_state=True)
async def add_category(message: Message, state: FSMContext) -> None:
    category = (message.text or "").strip()
    await state.update_data(category=category if category != "-" else "")
    await state.set_state(AddWish.description)
    await message.answer("\u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u043e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 (\u0438\u043b\u0438 \"-\" \u0435\u0441\u043b\u0438 \u0435\u0433\u043e \u043d\u0435\u0442):")


@router.message(AddWish.description)
@ensure_authorized(reset_state=True)
async def add_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    description = "" if raw in {"", "-"} else raw
    await state.update_data(description=description)
    await state.set_state(AddWish.priority)
    await message.answer("\u0423\u043a\u0430\u0436\u0438\u0442\u0435 \u043f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442 \u043e\u0442 1 \u0434\u043e 5:")


@router.message(AddWish.priority)
@ensure_authorized(reset_state=True)
async def add_priority(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer(
            "\u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c \u0447\u0438\u0441\u043b\u043e\u043c "
            "\u043e\u0442 1 \u0434\u043e 5. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437:"
        )
        return
    priority = int(raw)
    if priority < 1 or priority > 5:
        await message.answer(
            "\u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442 \u0432\u044b\u0431\u0438\u0440\u0430\u0435\u0442\u0441\u044f "
            "\u0432 \u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d\u0435 \u043e\u0442 1 \u0434\u043e 5. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437:"
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
    await message.answer("\u0416\u0435\u043b\u0430\u043d\u0438\u0435 \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u043e!")
    await message.answer("\u041f\u043e\u0441\u043c\u043e\u0442\u0440\u0438\u0442\u0435 \u0432\u0441\u0435 \u0436\u0435\u043b\u0430\u043d\u0438\u044f \u0447\u0435\u0440\u0435\u0437 /list.")
