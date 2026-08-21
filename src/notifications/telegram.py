"""Minimal Telegram Bot API helpers."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_API_URL = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(RuntimeError):
    """Raised when a Telegram request cannot be completed."""


def _request(token: str, method: str, data: dict[str, str] | None = None) -> dict:
    url = _API_URL.format(token=token, method=method)
    request = Request(url, data=urlencode(data or {}).encode() if data else None)
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except HTTPError as error:
        raise TelegramError(f"Telegram rejected the request (HTTP {error.code}).") from error
    except URLError as error:
        raise TelegramError("Could not reach Telegram.") from error

    if not payload.get("ok"):
        raise TelegramError("Telegram rejected the request.")
    return payload


def send_test_message(token: str, chat_id: str) -> None:
    """Send the first Smart Job Radar notification."""
    _request(token, "sendMessage", {"chat_id": chat_id, "text": "Smart Job Radar is running!"})


def get_chat_ids(token: str) -> list[str]:
    """Return unique chat IDs from updates after the user sends /start to the bot."""
    updates = _request(token, "getUpdates").get("result", [])
    return list(
        dict.fromkeys(
            str(update["message"]["chat"]["id"])
            for update in updates
            if "message" in update and "chat" in update["message"]
        )
    )
