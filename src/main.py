import os
import sys

from dotenv import load_dotenv

from database import DatabaseConnectionError, check_connection
from notifications.telegram import TelegramError, get_chat_ids, send_test_message


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing {name}. Add it to .env.")
    return value


def main() -> None:
    load_dotenv()
    try:
        if sys.argv[1:] == ["--check-db"]:
            check_connection(_required("DATABASE_URL"))
            print("PostgreSQL connection verified.")
            return
        token = _required("TELEGRAM_BOT_TOKEN")
        if sys.argv[1:] == ["--print-chat-id"]:
            chat_ids = get_chat_ids(token)
            print("\n".join(chat_ids) if chat_ids else "No chat ID found. Send /start to the bot, then retry.")
            return
        send_test_message(token, _required("TELEGRAM_CHAT_ID"))
        print("Test Telegram message sent.")
    except (DatabaseConnectionError, TelegramError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()