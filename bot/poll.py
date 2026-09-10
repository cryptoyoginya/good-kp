"""Локальный запуск бота через long polling, без Vercel.

Использование:
    uv run python bot/poll.py

Читает .env из корня репозитория, если он есть (простой парсер KEY=VALUE,
без внешних зависимостей). Токен нигде не печатается.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.core import handle_update, tg  # noqa: E402

POLL_TIMEOUT = 30


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def describe_update(update: dict) -> tuple[int | None, str]:
    if "message" in update:
        user_id = update["message"].get("from", {}).get("id")
        return user_id, "message"
    if "callback_query" in update:
        user_id = update["callback_query"].get("from", {}).get("id")
        return user_id, "callback_query"
    return None, "unknown"


def run() -> None:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("BOT_TOKEN"):
        print("BOT_TOKEN не задан (проверьте .env или переменные окружения)")
        return

    offset = None
    print("Бот запущен, ожидаю обновления...")
    while True:
        response = tg("getUpdates", offset=offset, timeout=POLL_TIMEOUT)
        if not response.get("ok"):
            print(f"getUpdates вернул ошибку: {response.get('description')}")
            time.sleep(1)
            continue

        for update in response.get("result", []):
            offset = update["update_id"] + 1
            user_id, kind = describe_update(update)
            try:
                handle_update(update)
                print(f"user={user_id} update={kind} outcome=ok")
            except Exception as error:  # noqa: BLE001
                print(f"user={user_id} update={kind} outcome=error {error}")


if __name__ == "__main__":
    run()
