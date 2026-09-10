"""Логика бота доступа Good КП. Только stdlib, без сохранения состояния.

Каждый вызов читает конфигурацию из переменных окружения заново: бот
работает и как вебхук в Vercel, и как локальный long polling процесс.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

TELEGRAM_API = "https://api.telegram.org"

CHANNEL_LABELS = {
    "vintersbrain": "Канал Кристины",
    "ShkolnyiAccount": "Канал Вадима",
}

SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


def _http_api(method: str, params: dict) -> dict:
    """Настоящий вызов Telegram Bot API. Токен нигде не логируется."""
    token = os.environ["BOT_TOKEN"]
    url = f"{TELEGRAM_API}/bot{token}/{method}"
    data = json.dumps(params).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"ok": False, "description": f"HTTP {error.code}"}
    except urllib.error.URLError as error:
        return {"ok": False, "description": str(error.reason)}


# Модульный уровень, чтобы тесты подменяли реальный HTTP на стаб.
API = _http_api


def tg(method: str, **params) -> dict:
    clean = {k: v for k, v in params.items() if v is not None}
    return API(method, clean)


def channel_label(channel: str) -> str:
    return CHANNEL_LABELS.get(channel, f"Канал {channel}")


def get_config() -> tuple[list[str], str]:
    raw_channels = os.environ.get("CHANNELS", "vintersbrain,ShkolnyiAccount")
    channels = [c.strip() for c in raw_channels.split(",") if c.strip()]
    repo_url = os.environ.get("REPO_URL", "")
    return channels, repo_url


def check_subscriptions(user_id: int, channels: list[str]) -> dict:
    """Возвращает для каждого канала 'ok', 'no' или 'unknown'."""
    result = {}
    for channel in channels:
        response = tg("getChatMember", chat_id=f"@{channel}", user_id=user_id)
        if not response.get("ok"):
            result[channel] = "unknown"
            continue
        member = response.get("result") or {}
        status = member.get("status")
        if status in SUBSCRIBED_STATUSES:
            result[channel] = "ok"
        elif status == "restricted" and member.get("is_member"):
            result[channel] = "ok"
        else:
            result[channel] = "no"
    return result


def build_reply(status: dict, repo_url: str, channels: list[str]):
    """Возвращает (текст, reply_markup | None)."""
    if all(status.get(c) == "ok" for c in channels):
        text = (
            f"Доступ открыт. Репозиторий: {repo_url}\n\n"
            "Как начать:\n"
            "1. Откройте README в репозитории.\n"
            "2. Установите зависимости по инструкции.\n"
            "3. Запустите пример из папки examples."
        )
        return text, None

    missing = [c for c in channels if status.get(c) == "no"]
    unknown = [c for c in channels if status.get(c) == "unknown"]

    lines = []
    if missing:
        names = ", ".join(channel_label(c) for c in missing)
        lines.append(f"Не хватает подписки: {names}.")
    if unknown:
        names = ", ".join(channel_label(c) for c in unknown)
        lines.append(
            f"Бот пока не администратор в канале: {names}. "
            "Это нужно исправить владельцу бота."
        )
    lines.append("Подпишитесь на каналы и нажмите «Проверить снова».")
    text = "\n".join(lines)

    buttons = [
        [{"text": channel_label(c), "url": f"https://t.me/{c}"}] for c in channels
    ]
    buttons.append([{"text": "Проверить снова", "callback_data": "recheck"}])
    reply_markup = {"inline_keyboard": buttons}
    return text, reply_markup


def _is_not_modified(response: dict) -> bool:
    description = response.get("description", "")
    return "message is not modified" in description


def handle_update(update: dict) -> None:
    channels, repo_url = get_config()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        status = check_subscriptions(user_id, channels)
        text, reply_markup = build_reply(status, repo_url, channels)
        tg("sendMessage", chat_id=chat_id, text=text, reply_markup=reply_markup)
        return

    if "callback_query" in update:
        callback = update["callback_query"]
        message = callback["message"]
        chat_id = message["chat"]["id"]
        message_id = message["message_id"]
        user_id = callback["from"]["id"]

        status = check_subscriptions(user_id, channels)
        text, reply_markup = build_reply(status, repo_url, channels)

        tg("answerCallbackQuery", callback_query_id=callback["id"])
        response = tg(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        if not response.get("ok") and not _is_not_modified(response):
            # Не роняем обработчик из-за прочих ошибок Telegram: бот
            # без состояния, следующая проверка исправит расхождение.
            pass
        return
