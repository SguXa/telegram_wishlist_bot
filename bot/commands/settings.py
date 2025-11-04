from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.fsm import UserSession
from bot.shared_utils import ensure_authorized
from core.formatting import escape_html_text
from ui.keyboards import SETTINGS_BUTTON, logged_out_keyboard, main_menu_keyboard

router = Router()


@router.message(StateFilter(UserSession.logged_out), Command("settings"))
async def cmd_settings_logged_out(message: Message, state: FSMContext) -> None:
    await message.answer(
        "⚙️ Настройки станут доступны после входа. Нажмите «🔐 Войти» ниже.",
        reply_markup=logged_out_keyboard(),
    )


@router.message(Command("settings"), StateFilter(UserSession.active))
@router.message(StateFilter(UserSession.active), F.text == SETTINGS_BUTTON)
@ensure_authorized(require_session=True)
async def cmd_settings(message: Message, state: FSMContext) -> None:
    user = message.from_user
    display_name = escape_html_text(user.full_name or user.username or "—") if user else "—"

    lines: list[str] = ["⚙️ Настройки", ""]
    lines.append(f"Вы вошли как: {display_name}")
    if user and user.username:
        lines.append(f"Имя пользователя: @{escape_html_text(user.username)}")
    if user:
        lines.append(f"ID: <code>{user.id}</code>")
    else:
        lines.append("ID: —")

    lines.append("")
    lines.extend(
        [
            "Доступные действия:",
            "- /export — выгрузить список желаний в файл.",
            "- /logout — завершить текущий сеанс.",
            "- /help — подсказки по командам.",
        ]
    )

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())
