import logging
import os
import re
from pathlib import Path
from typing import Optional, Set

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]


ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
ENV_AUTHORIZED_USERS_KEY = "AUTHORIZED_USER_IDS"


def load_env_file() -> None:
    if load_dotenv:
        load_dotenv(dotenv_path=ENV_FILE)
        return

    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
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
        "No authorized Telegram user IDs configured. Set %s in %s to allow access.",
        ENV_AUTHORIZED_USERS_KEY,
        ENV_FILE.name,
    )


def ensure_token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Please export your bot token before running."
        )
    return token

