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
    """\u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u043e\u0439 \u0441\u0435\u0441\u0441\u0438\u0438 (\u0430\u043a\u0442\u0438\u0432\u043d\u044b\u0439 \u0438\u043b\u0438 \u043d\u0435\u0430\u0432\u0442\u043e\u0440\u0438\u0437\u043e\u0432\u0430\u043d\u043d\u044b\u0439)."""

    active = State()
    logged_out = State()
