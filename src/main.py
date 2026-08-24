import os
import sys
from collections import Counter

from dotenv import load_dotenv

from adapters.remoteok import RemoteOKAdapter, RemoteOKError
from database import DatabaseConnectionError, check_connection, check_schema
from persistence import SyncError, run_remoteok, sync_remoteok
from hard_filters import apply
from scoring import score
from search_profile import ConfigError, load_search_profile
from validation import validate
from notifications.telegram import TelegramError, get_chat_ids, send_test_message


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing {name}. Add it to .env.")
    return value


def main() -> None:
    load_dotenv()
    try:
        if sys.argv[1:] == ["--check-schema"]:
            check_schema(_required("DATABASE_URL"))
            print("PostgreSQL schema verified.")
            return
        if sys.argv[1:] == ["--check-db"]:
            check_connection(_required("DATABASE_URL"))
            print("PostgreSQL connection verified.")
            return
        if sys.argv[1:] == ["--fetch-remoteok"]:
            jobs = RemoteOKAdapter().fetch()
            print(f"RemoteOK normalized jobs: {len(jobs)}")
            for job in jobs[:3]:
                print(f"- {job.title} | {job.company or 'Unknown company'} | {job.url}")
            return
        if sys.argv[1:] == ["--filter-remoteok"]:
            profile = load_search_profile("config/search-profile.yaml")
            jobs = RemoteOKAdapter().fetch()
            valid = [job for job in jobs if validate(job).passed]
            results = [(job, apply(job, profile)) for job in valid]
            passed = [job for job, result in results if result.passed]
            rejected = [(job, result.reasons) for job, result in results if not result.passed]
            print(f"RemoteOK filter: fetched={len(jobs)}, valid={len(valid)}, passed={len(passed)}, rejected={len(rejected)}")
            for reason, count in Counter(reason for _, reasons in rejected for reason in reasons).most_common(3):
                print(f"- rejected: {reason}={count}")
            for job, reasons in rejected[:3]:
                print(f"- rejected example: {job.title} | {', '.join(reasons)}")
            for job in passed[:3]:
                print(f"- {job.title} | {job.company or 'Unknown company'} | {job.url}")
            return
        if sys.argv[1:] == ["--score-remoteok"]:
            profile = load_search_profile("config/search-profile.yaml")
            jobs = RemoteOKAdapter().fetch()
            valid = [job for job in jobs if validate(job).passed]
            filtered = [job for job in valid if apply(job, profile).passed]
            scored = [(job, score(job, profile)) for job in filtered]
            qualified = [(job, result) for job, result in scored if result.score >= profile.minimum_score]
            scored.sort(key=lambda item: (-item[1].score, item[0].title.casefold(), item[0].source_job_id))
            print(f"RemoteOK score: fetched={len(jobs)}, valid={len(valid)}, filtered={len(filtered)}, scored={len(scored)}, qualified={len(qualified)}")
            for job, result in scored[:5]:
                print(f"- {result.score} | {job.title} | {'; '.join(result.reasons) or 'no_matches'} | {job.url}")
            return
        if sys.argv[1:] == ["--run-remoteok"]:
            stats = run_remoteok(
                _required("DATABASE_URL"), load_search_profile("config/search-profile.yaml"), RemoteOKAdapter().fetch,
            )
            print("RemoteOK run: " + ", ".join(f"{name}={value}" for name, value in vars(stats).items()))
            return
        if sys.argv[1:] == ["--sync-remoteok"]:
            stats = sync_remoteok(_required("DATABASE_URL"), RemoteOKAdapter().fetch())
            print(
                "RemoteOK sync: " + ", ".join(
                    f"{name}={value}" for name, value in vars(stats).items()
                )
            )
            return
        token = _required("TELEGRAM_BOT_TOKEN")
        if sys.argv[1:] == ["--print-chat-id"]:
            chat_ids = get_chat_ids(token)
            print("\n".join(chat_ids) if chat_ids else "No chat ID found. Send /start to the bot, then retry.")
            return
        send_test_message(token, _required("TELEGRAM_CHAT_ID"))
        print("Test Telegram message sent.")
    except (ConfigError, DatabaseConnectionError, RemoteOKError, SyncError, TelegramError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()