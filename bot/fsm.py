from aiogram.fsm.state import State, StatesGroup


class AddWish(StatesGroup):
    waiting_input = State()


class EditWish(StatesGroup):
    waiting_for_title = State()
    waiting_for_url = State()
    waiting_for_photo = State()
    waiting_for_description = State()


class UserSession(StatesGroup):
    """Состояния пользовательской сессии (активный или неавторизованный)."""

    active = State()
    logged_out = State()
