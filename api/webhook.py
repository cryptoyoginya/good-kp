"""Вебхук Telegram как одна Vercel Python функция."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.core import handle_update  # noqa: E402


def process(body: bytes, secret_header: str | None) -> tuple[int, dict]:
    """Обрабатывает тело запроса, возвращает (статус, json-ответ)."""
    expected_secret = os.environ.get("WEBHOOK_SECRET")
    if expected_secret and secret_header != expected_secret:
        return 403, {"ok": False}

    try:
        update = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, {"ok": False}

    handle_update(update)
    return 200, {"ok": True}


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length) if length else b""
        secret_header = self.headers.get("X-Telegram-Bot-Api-Secret-Token")

        status, payload = process(body, secret_header)

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        # Тише по умолчанию: не печатать тело запроса (там id пользователей).
        pass
