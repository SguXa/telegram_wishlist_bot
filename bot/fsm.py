from aiogram.fsm.state import State, StatesGroup


class AddWish(StatesGroup):
    waiting_input = State()


class EditWish(StatesGroup):
    waiting_value = State()


class UserSession(StatesGroup):
    """Состояния пользовательской сессии (активный или неавторизованный)."""

    active = State()
    logged_out = State()
