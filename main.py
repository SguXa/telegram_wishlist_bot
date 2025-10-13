import asyncio
import csv
import io
import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4
from html import escape as html_escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    User,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]


logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENV_FILE = Path(__file__).with_name('.env')
ENV_AUTHORIZED_USERS_KEY = 'AUTHORIZED_USER_IDS'


def load_env_file() -> None:
    if load_dotenv:
        load_dotenv(dotenv_path=ENV_FILE)
        return
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()


def canonicalize_identifier(value: str) -> Optional[str]:
    text = value.strip()
    if not text:
        return None
    if text.startswith("@"):
        return text.lower()
    if text.isdigit():
        return text
    return f"@{text.lower()}"


def parse_authorized_identifiers(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    result: Set[str] = set()
    for chunk in re.split(r"[\s,]+", raw):
        identifier = canonicalize_identifier(chunk)
        if identifier:
            result.add(identifier)
    return result


AUTHORIZED_IDENTIFIERS = parse_authorized_identifiers(os.getenv(ENV_AUTHORIZED_USERS_KEY))
AUTHORIZED_NUMERIC_IDS = {identifier for identifier in AUTHORIZED_IDENTIFIERS if identifier.isdigit()}
if not AUTHORIZED_IDENTIFIERS:
    logging.warning(
        'No authorized Telegram user IDs configured. Set %s in %s to allow access.',
        ENV_AUTHORIZED_USERS_KEY,
        ENV_FILE.name,
    )

DATA_FILE = Path(__file__).with_name("wishlist_data.json")
DEFAULT_CATEGORY_TITLE = "Без категории"
DEFAULT_CATEGORY_EMOJI = "🎁"

# Provide a small dictionary of category keywords to emojis so that users get
# a sensible icon automatically. Matching is case-insensitive and uses
# substring matching for flexibility.
CATEGORY_EMOJI_MAP = {
    "книг": "📚",
    "book": "📚",
    "тех": "🎧",
    "электро": "🔌",
    "элек": "🔌",
    "гаджет": "📱",
    "игр": "🎮",
    "game": "🎮",
    "одеж": "👗",
    "одёж": "👗",
    "shoes": "👟",
    "дом": "🏠",
    "home": "🏠",
    "кух": "🍳",
    "travel": "✈️",
    "путеш": "✈️",
    "космет": "💄",
    "спорт": "🏃",
    "дет": "🧸",
}


# ---------------------------------------------------------------------------
# FSM states
# ---------------------------------------------------------------------------


class AddWish(StatesGroup):
    title = State()
    link = State()
    category = State()
    description = State()
    priority = State()


class EditWish(StatesGroup):
    waiting_value = State()


class UserSession(StatesGroup):
    """Состояния для управления сессией (логин/логаут)."""

    # Состояние, когда пользователь активно использует бота
    active = State()
    # Состояние, когда пользователь "вышел" или не авторизован
    logged_out = State()


# ---------------------------------------------------------------------------
# Data storage helpers
# ---------------------------------------------------------------------------


@dataclass
class Wish:
    id: str
    title: str
    link: str
    category: str
    description: str
    priority: int


Store = Dict[str, Any]
store: Store = {"users": {uid: [] for uid in AUTHORIZED_NUMERIC_IDS}}
store_lock = asyncio.Lock()


def ensure_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Please export your bot token before running."
        )
    return token


def load_store() -> None:
    global store
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as fh:
            try:
                loaded = json.load(fh)
            except json.JSONDecodeError:
                logging.warning("Failed to decode storage file, starting fresh.")
                loaded = {}
    else:
        loaded = {}

    users = loaded.get("users", {})
    # Ensure every numeric authorized user has an entry.
    for user_id in AUTHORIZED_NUMERIC_IDS:
        users.setdefault(user_id, [])

    store = {"users": users}
    persist_store()  # Make sure the on-disk file exists.


def persist_store() -> None:
    DATA_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


async def mutate_store(mutator) -> Any:
    async with store_lock:
        result = mutator(store)
        persist_store()
        return result


def list_wishes(user_id: int) -> List[Wish]:
    wishes = []
    for raw in store["users"].get(str(user_id), []):
        wishes.append(
            Wish(
                id=raw["id"],
                title=raw["title"],
                link=raw.get("link", ""),
                category=raw.get("category", ""),
                description=raw.get("description", ""),
                priority=int(raw.get("priority", 0)),
            )
        )
    return wishes


def find_wish(user_id: int, wish_id: str) -> Optional[Wish]:
    for wish in list_wishes(user_id):
        if wish.id == wish_id:
            return wish
    return None


async def add_wish(user_id: int, wish: Wish) -> None:
    user_key = str(user_id)

    def mutator(current: Store) -> None:
        current["users"].setdefault(user_key, [])
        current["users"][user_key].append(
            {
                "id": wish.id,
                "title": wish.title,
                "link": wish.link,
                "category": wish.category,
                "description": wish.description,
                "priority": wish.priority,
            }
        )

    await mutate_store(mutator)


async def update_wish_field(user_id: int, wish_id: str, field: str, value: Any) -> Optional[Wish]:
    user_key = str(user_id)
    updated: Optional[Wish] = None

    def mutator(current: Store) -> None:
        nonlocal updated
        for wish in current["users"].setdefault(user_key, []):
            if wish["id"] == wish_id:
                wish[field] = value
                updated = Wish(
                    id=wish["id"],
                    title=wish["title"],
                    link=wish.get("link", ""),
                    category=wish.get("category", ""),
                    description=wish.get("description", ""),
                    priority=int(wish.get("priority", 0)),
                )
                break

    await mutate_store(mutator)
    return updated


async def delete_wish(user_id: int, wish_id: str) -> bool:
    user_key = str(user_id)
    removed = False

    def mutator(current: Store) -> None:
        nonlocal removed
        wishes = current["users"].setdefault(user_key, [])
        original_length = len(wishes)
        wishes[:] = [wish for wish in wishes if wish["id"] != wish_id]
        removed = len(wishes) != original_length

    await mutate_store(mutator)
    return removed


def collect_categories() -> List[str]:
    categories = set()
    for wishes in store["users"].values():
        for wish in wishes:
            name = (wish.get("category") or "").strip()
            if name:
                categories.add(name)
    if not categories:
        return []
    return sorted(categories, key=lambda item: item.casefold())


def select_other_user(current_user_id: int) -> Optional[int]:
    current_key = str(current_user_id)
    for identifier in AUTHORIZED_NUMERIC_IDS:
        if identifier == current_key:
            continue
        return int(identifier)
    return None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def category_to_emoji(category: str) -> str:
    if not category:
        return DEFAULT_CATEGORY_EMOJI
    key = category.strip().lower()
    for needle, emoji in CATEGORY_EMOJI_MAP.items():
        if needle in key:
            return emoji
    return DEFAULT_CATEGORY_EMOJI


def escape_html_text(value: str) -> str:
    return html_escape(value, quote=True) if value else ""


def build_wish_block(wish: Wish) -> str:
    lines = [f"({wish.priority}) {escape_html_text(wish.title)}"]
    if wish.link:
        lines.append(f"   🔗 {escape_html_text(wish.link)}")
    if wish.description:
        lines.append(f"   📝 {escape_html_text(wish.description)}")
    return "\n".join(lines)


def sort_wishes_for_display(wishes: List[Wish]) -> List[Tuple[str, List[Wish]]]:
    grouped: Dict[str, List[Wish]] = defaultdict(list)
    for wish in wishes:
        category = wish.category.strip() if wish.category else ""
        category = category or DEFAULT_CATEGORY_TITLE
        grouped[category].append(wish)

    result: List[Tuple[str, List[Wish]]] = []
    for category, items in grouped.items():
        sorted_items = sorted(items, key=lambda w: w.priority, reverse=True)
        result.append((category, sorted_items))

    result.sort(key=lambda item: item[0].casefold())
    return result


def truncate(text: str, limit: int = 24) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def build_list_actions_keyboard(wishes: List[Wish]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for wish in wishes:
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ {truncate(wish.title, 18)}", callback_data=f"edit:{wish.id}"
            ),
            InlineKeyboardButton(text="❌", callback_data=f"delete:{wish.id}"),
        )
    return builder


def get_active_keyboard() -> ReplyKeyboardMarkup:
    builder = [
        [KeyboardButton(text="/add"), KeyboardButton(text="/list"), KeyboardButton(text="/help")],
        [KeyboardButton(text="/edit"), KeyboardButton(text="/delete"), KeyboardButton(text="/others")],
        [KeyboardButton(text="/search"), KeyboardButton(text="/categories"), KeyboardButton(text="/export")],
        [KeyboardButton(text="/logout")],
    ]
    return ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True, one_time_keyboard=False)


def get_logged_out_keyboard() -> ReplyKeyboardMarkup:
    builder = [[KeyboardButton(text="/login")]]
    return ReplyKeyboardMarkup(keyboard=builder, resize_keyboard=True, one_time_keyboard=False)


def compose_export_txt(wishes: List[Wish]) -> str:
    if not wishes:
        return "Список желаний пуст."

    lines: List[str] = []
    for category, items in sort_wishes_for_display(wishes):
        emoji = category_to_emoji(category if category != DEFAULT_CATEGORY_TITLE else "")
        lines.append(f"{emoji} {category}")
        for wish in items:
            lines.append(build_wish_block(wish))
            lines.append("")  # extra newline between wishes
        lines.append("")  # extra newline between categories
    return "\n".join(line for line in lines if line is not None).strip() + "\n"


def compose_export_csv(wishes: List[Wish]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Название",
        "Ссылка",
        "Категория",
        "Описание",
        "Приоритет",
    ])
    return output.getvalue()


# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------


bot = Bot(token=ensure_token(), default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)


def is_authorized(user: Optional[User]) -> bool:
    if user is None:
        return False
    if str(user.id) in AUTHORIZED_IDENTIFIERS:
        return True
    username = user.username
    if username:
        handle = canonicalize_identifier(f"@{username}")
        if handle and handle in AUTHORIZED_IDENTIFIERS:
            return True
    return False


async def ensure_authorized_message(message: Message) -> bool:
    if not is_authorized(message.from_user):
        await message.answer("Извините, этот бот предназначен только для личного использования.")
        return False
    return True


async def ensure_authorized_callback(callback: CallbackQuery) -> bool:
    if not is_authorized(callback.from_user):
        await callback.answer("Нет доступа.", show_alert=True)
        return False
    return True


async def ensure_active_session_callback(callback: CallbackQuery, state: FSMContext) -> bool:
    if not await ensure_authorized_callback(callback):
        return False

    current_state = await state.get_state()
    if current_state != UserSession.active.state:
        await callback.answer("Сессия не активна. Пожалуйста, используйте /login.", show_alert=True)
        return False
    return True


def describe_wish_for_confirmation(wish: Wish) -> str:
    emoji = category_to_emoji(wish.category)
    category = escape_html_text(wish.category or DEFAULT_CATEGORY_TITLE)
    return f"{emoji} {category}\n{build_wish_block(wish)}"


async def send_wish_list(
    message: Message,
    wishes: List[Wish],
    empty_text: str,
) -> None:
    if not wishes:
        await message.answer(empty_text)
        return

    for category, items in sort_wishes_for_display(wishes):
        emoji = category_to_emoji(category if category != DEFAULT_CATEGORY_TITLE else "")
        text_lines = [f"{emoji} {escape_html_text(category)}"]
        for wish in items:
            text_lines.append(build_wish_block(wish))
            text_lines.append("")  # spacing between wishes
        payload = "\n".join(text_lines).strip()
        keyboard = build_list_actions_keyboard(items)
        await message.answer(payload, reply_markup=keyboard.as_markup())


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    user = message.from_user

    await state.clear()
    reply_markup = get_logged_out_keyboard()

    if is_authorized(user):
        await state.set_state(UserSession.active)
        reply_markup = get_active_keyboard()
        greeting = (
            "Привет! Я ваш личный бот-органайзер желаний.\n"
            "Используйте /help, чтобы посмотреть список доступных команд."
        )
    else:
        await state.set_state(UserSession.logged_out)
        greeting = (
            "Извините, этот бот предназначен только для личного использования. "
            "Ваш ID не найден в списке авторизованных. "
            "Пожалуйста, используйте /login, если вы должны иметь доступ."
        )

    await message.answer(greeting, reply_markup=reply_markup)

@router.message(Command("logout"), StateFilter(UserSession.active))
async def cmd_logout(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserSession.logged_out)

    await message.answer(
        "Вы вышли из системы. Ваши данные скрыты. "
        "Для повторного входа используйте команду /login."
    )
@router.message(Command("logout"), StateFilter(UserSession.logged_out, None))
async def cmd_logout_inactive(message: Message) -> None:
    await message.answer("Вы уже вышли из системы или не были активны. Используйте /login.")


@router.message(Command("login"))
@router.message(StateFilter(UserSession.logged_out), Command("login"))
async def cmd_login(message: Message, state: FSMContext) -> None:
    user = message.from_user
    identifiers_to_try: List[str] = []
    if user:
        identifiers_to_try.append(str(user.id))
        if user.username:
            identifiers_to_try.append(f"@{user.username}")

    matched_identifier: Optional[str] = None
    for raw_identifier in identifiers_to_try:
        normalized = canonicalize_identifier(raw_identifier)
        if normalized and normalized in AUTHORIZED_IDENTIFIERS:
            matched_identifier = normalized
            break

    if matched_identifier:
        await state.clear()
        await state.set_state(UserSession.active)
        await message.answer(
            "Login successful! Main features are now available. Use /list or /help.",
            reply_markup=get_active_keyboard()
        )
        return

    await state.set_state(UserSession.logged_out)
    user_id_text = identifiers_to_try[0] if identifiers_to_try else "unknown"
    username_text = next((value for value in identifiers_to_try if value.startswith("@")), None)
    failure_lines = [
        "Login failed. Please make sure your Telegram ID or username is allowed.",
        f"ID: {escape_html_text(user_id_text)}",
    ]
    if username_text:
        failure_lines.append(f"Username: {escape_html_text(username_text)}")
    await message.answer("\n".join(failure_lines), reply_markup=get_logged_out_keyboard())


@router.message(F.text, StateFilter(UserSession.logged_out))
async def handle_logged_out_message(message: Message) -> None:
    if message.text in {"/login"}:
        return

    await message.answer(
        "Бот доступен только после авторизации. Отправьте /login, чтобы войти.",
        reply_markup=get_logged_out_keyboard(),
    )


@router.message(Command("help"), StateFilter(UserSession.active))
async def cmd_help(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    help_text = (
        "Доступные команды:\n"
        "/add — добавить новое желание.\n"
        "/list — показать ваш список желаний.\n"
        "/edit — выбрать желание для редактирования.\n"
        "/delete — выбрать желание для удаления.\n"
        "/others — посмотреть список желаний другого человека.\n"
        "/categories — показать все доступные категории.\n"
        "/search слово — поиск по вашим желаниям.\n"
        "/export — выгрузить список в TXT или CSV."
    )
    await message.answer(help_text)


@router.message(Command("add"), StateFilter(UserSession.active))
async def cmd_add(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        return

    await state.set_state(AddWish.title)
    await message.answer("Введите название желания:")


@router.message(AddWish.title)
async def add_title(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Введите другое значение.")
        return
    await state.update_data(title=title)
    await state.set_state(AddWish.link)
    await message.answer("Введите ссылку (или "-" если её нет):")


@router.message(AddWish.link)
async def add_link(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    raw = (message.text or "").strip()
    link = "" if raw in {"", "-"} else raw
    await state.update_data(link=link)
    await state.set_state(AddWish.category)
    await message.answer("Введите категорию:")


@router.message(AddWish.category)
async def add_category(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    category = (message.text or "").strip()
    await state.update_data(category=category)
    await state.set_state(AddWish.description)
    await message.answer("Введите описание (или \"-\" если нет):")


@router.message(AddWish.description)
async def add_description(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    raw = (message.text or "").strip()
    description = "" if raw in {"", "-"} else raw
    await state.update_data(description=description)
    await state.set_state(AddWish.priority)
    await message.answer("Введите приоритет (1-5):")


@router.message(AddWish.priority)
async def add_priority(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Приоритет должен быть числом от 1 до 5. Попробуйте снова:")
        return
    priority = int(raw)
    if priority < 1 or priority > 5:
        await message.answer("Приоритет должен быть в диапазоне от 1 до 5. Отправьте значение ещё раз:")
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
    await add_wish(message.from_user.id, wish)
    await state.clear()
    await state.set_state(UserSession.active)
    await message.answer("Желание добавлено!")
    await message.answer("🎉 Желание сохранено!")

@router.message(Command("list"), StateFilter(UserSession.active))
async def cmd_list(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    wishes = list_wishes(message.from_user.id)
    await send_wish_list(
        message,
        wishes,
        "Ваш список желаний пока пуст. Добавьте новое через /add.",
    )


@router.message(Command("others"), StateFilter(UserSession.active))
async def cmd_others(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    other_id = select_other_user(message.from_user.id)
    if other_id is None:
        await message.answer("Нет других пользователей с доступом к боту. Добавьте их ID в переменную AUTHORIZED_USER_IDS.")
        return

    wishes = list_wishes(other_id)
    await send_wish_list(
        message,
        wishes,
        "У выбранного пользователя пока нет сохранённых желаний.",
    )


@router.message(Command("categories"), StateFilter(UserSession.active))
async def cmd_categories(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    categories = collect_categories()
    if not categories:
        await message.answer("Категорий пока нет. Добавьте желание с категорией через /add.")
        return

    lines = []
    for category in categories:
        lines.append(f"{category_to_emoji(category)} {escape_html_text(category)}")
    await message.answer("\n".join(lines))


@router.message(Command("search"), StateFilter(UserSession.active))
async def cmd_search(message: Message, command: CommandObject) -> None:
    if not await ensure_authorized_message(message):
        return

    query = (command.args or "").strip()
    if not query:
        await message.answer("Используйте формат: /search <запрос>")
        return

    wishes = list_wishes(message.from_user.id)
    matched = [
        wish
        for wish in wishes
        if query.lower() in wish.title.lower() or query.lower() in wish.description.lower()
    ]
    if not matched:
        await message.answer("Ничего не найдено.")
        return

    await send_wish_list(message, matched, "Ничего не найдено.")


@router.message(Command("edit"), StateFilter(UserSession.active))
async def cmd_edit(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    wishes = list_wishes(message.from_user.id)
    if not wishes:
        await message.answer("Список желаний пуст. Сначала добавьте что-нибудь через /add.")
        return

    builder = InlineKeyboardBuilder()
    for wish in sorted(wishes, key=lambda w: w.title.casefold()):
        builder.button(text=truncate(wish.title), callback_data=f"edit:{wish.id}")
    builder.adjust(1)
    await message.answer("Выберите желание для редактирования:", reply_markup=builder.as_markup())


@router.message(Command("delete"), StateFilter(UserSession.active))
async def cmd_delete(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    wishes = list_wishes(message.from_user.id)
    if not wishes:
        await message.answer("Список желаний пуст. Удалять пока нечего.")
        return

    builder = InlineKeyboardBuilder()
    for wish in sorted(wishes, key=lambda w: w.title.casefold()):
        builder.button(text=f"Удалить {truncate(wish.title)}", callback_data=f"delete:{wish.id}")
    builder.adjust(1)
    await message.answer("Выберите желание, которое нужно удалить:", reply_markup=builder.as_markup())


@router.message(Command("export"), StateFilter(UserSession.active))
async def cmd_export(message: Message) -> None:
    if not await ensure_authorized_message(message):
        return

    wishes = list_wishes(message.from_user.id)
    if not wishes:
        await message.answer("Нет желаний для экспорта. Добавьте хотя бы одно через /add.")
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="TXT", callback_data="export:txt")
    builder.button(text="CSV", callback_data="export:csv")
    builder.adjust(2)
    await message.answer("Выберите формат экспорта:", reply_markup=builder.as_markup())


# ---------------------------------------------------------------------------
# Callback handlers
# ---------------------------------------------------------------------------


@router.callback_query(F.data.startswith("edit:"))
async def callback_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return

    wish_id = callback.data.split(":", 1)[1]
    wish = find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer("Не удалось найти желание.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data=f"edit_field:{wish_id}:title")
    builder.button(text="Ссылка", callback_data=f"edit_field:{wish_id}:link")
    builder.button(text="Категория", callback_data=f"edit_field:{wish_id}:category")
    builder.button(text="Описание", callback_data=f"edit_field:{wish_id}:description")
    builder.button(text="Приоритет", callback_data=f"edit_field:{wish_id}:priority")
    builder.adjust(2)

    await callback.message.answer(
        f"Что изменить?\n\n{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
async def callback_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return

    _, wish_id, field = callback.data.split(":", 2)
    wish = find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer("Не удалось найти желание.", show_alert=True)
        return

    prompts = {
        "title": "Введите новое название:",
        "link": "Введите новую ссылку (или "-" если её нет):",
        "category": "Введите новую категорию:",
        "description": "Введите новое описание (или "-" если его нет):",
        "priority": "Введите новый приоритет от 1 до 5:",
    }
    await state.set_state(EditWish.waiting_value)
    await state.update_data(wish_id=wish_id, field=field)
    await callback.message.answer(prompts[field])
    await callback.answer()


@router.message(EditWish.waiting_value)
async def process_edit_value(message: Message, state: FSMContext) -> None:
    if not await ensure_authorized_message(message):
        await state.clear()
        await state.set_state(UserSession.logged_out)
        return

    data = await state.get_data()
    wish_id = data.get("wish_id")
    field = data.get("field")
    if not wish_id or not field:
        await message.answer("Сессия потеряна. Повторите команду /edit.")
        await state.clear()
        await state.set_state(UserSession.active)
        return

    new_value_raw = (message.text or "").strip()
    user_id = message.from_user.id

    if field == "priority":
        if not new_value_raw.isdigit():
            await message.answer("Приоритет должен быть числом от 1 до 5. Попробуйте снова:")
            return
        priority = int(new_value_raw)
        if priority < 1 or priority > 5:
            await message.answer("Приоритет должен быть в диапазоне от 1 до 5. Отправьте значение ещё раз:")
            return
        updated = await update_wish_field(user_id, wish_id, "priority", priority)
    else:
        if field in {"link", "description"} and new_value_raw == "-":
            new_value = ""
        else:
            new_value = new_value_raw
        updated = await update_wish_field(user_id, wish_id, field, new_value)

    if not updated:
        await message.answer("Не удалось обновить желание. Попробуйте ещё раз через /edit.")
        await message.answer("Не удалось обновить желание. Попробуйте ещё раз через /edit.")
        await message.answer("Желание обновлено: \n\n" + describe_wish_for_confirmation(updated))

    await state.clear()
    await state.set_state(UserSession.active)


@router.callback_query(F.data.startswith("delete:"))
async def callback_delete(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return

    wish_id = callback.data.split(":", 1)[1]
    wish = find_wish(callback.from_user.id, wish_id)
    if not wish:
        await callback.answer("Не удалось найти желание.", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить", callback_data=f"delete_confirm:{wish_id}")
    builder.button(text="Отмена", callback_data="cancel")
    builder.adjust(2)
    await callback.message.answer(
        f"Удалить это желание?\n\n{describe_wish_for_confirmation(wish)}",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return
    await callback.answer("Отменено.")


@router.callback_query(F.data.startswith("delete_confirm:"))
async def callback_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return

    wish_id = callback.data.split(":", 1)[1]
    removed = await delete_wish(callback.from_user.id, wish_id)
    if removed:
        await callback.message.answer("Желание удалено.")
        await callback.answer()
    else:
        await callback.answer("Не удалось удалить желание.", show_alert=True)


@router.callback_query(F.data.startswith("export:"))
async def callback_export(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_active_session_callback(callback, state):
        return

    format_name = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    wishes = list_wishes(user_id)

    if format_name == "txt":
        content = compose_export_txt(wishes)
        file = BufferedInputFile(content.encode("utf-8"), filename="wishlist.txt")
    elif format_name == "csv":
        content = compose_export_csv(wishes)
        file = BufferedInputFile(content.encode("utf-8"), filename="wishlist.csv")
    else:
        await callback.answer("Неизвестный формат.", show_alert=True)
        return

    await callback.message.answer_document(file)
    await callback.answer("Экспорт завершён!")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    load_store()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

