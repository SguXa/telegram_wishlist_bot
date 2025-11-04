from aiogram import Dispatcher

from bot.shared_utils import set_storage
from core.storage import Storage


def register_routes(dp: Dispatcher, storage: Storage) -> None:
    set_storage(storage)

    from bot.callbacks import delete_callbacks, edit_callbacks, export_callbacks
    from bot.commands import (
        add,
        categories,
        delete,
        edit,
        export,
        help,
        list as list_command,
        login,
        logout,
        others,
        settings,
        search,
        start,
    )

    for module in (
        start,
        help,
        login,
        logout,
        add,
        list_command,
        others,
        categories,
        search,
        edit,
        delete,
        export,
        settings,
        edit_callbacks,
        delete_callbacks,
        export_callbacks,
    ):
        dp.include_router(module.router)
