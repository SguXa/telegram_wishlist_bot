from aiogram.fsm.state import State, StatesGroup


class AddWish(StatesGroup):
    title = State()
    link = State()
    category = State()
    description = State()
    priority = State()


class EditWish(StatesGroup):
    waiting_value = State()


class UserSession(StatesGroup):
    """Состояния пользовательской сессии (активный или неавторизованный)."""

    active = State()
    logged_out = State()
