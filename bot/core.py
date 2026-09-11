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


WELCOME = (
    "Привет. Я бот Good КП.\n\n"
    "Обычная история: КП уходит клиенту, там его открывает маркетолог, листает две страницы "
    "про агентство, доходит до цены и закрывает. До директора файл не доезжает, а вы узнаете "
    "об этом через неделю молчания.\n\n"
    "Good КП прогоняет ваше КП через трех синтетических читателей на стороне клиента до отправки. "
    "Показывает, на какой странице каждый закрыл файл, где из шести опор документ держится, "
    "а где нет, и собирает исправленную первую страницу.\n\n"
    "Методика Вадима Школьного, @ShkolnyiAccount. Сборка Кристины Винтер, @vintersbrain.\n\n"
    "Инструмент бесплатный и открытый. Чтобы получить ссылку, подпишитесь на оба канала "
    "и нажмите «Получить ссылку» 🚀"
)

ACCESS_PHOTO_CAPTION = (
    "Так выглядит прогон. Это разбор синтетического КП «Пиксель Лаб» "
    "для сети строительных гипермаркетов."
)

ACCESS_FILE_CAPTION = (
    "Пример отчета. Откройте файл в браузере на компьютере: внутри переписка "
    "у клиента, голосовой вердикт гендира, три читателя, шесть опор, "
    "экран с флагами, исправленная первая страница и таймер на час правок."
)


def access_text(repo_url: str) -> str:
    return (
        f"Доступ открыт. Репозиторий: {repo_url}\n\n"
        "Что внутри отчета\n"
        "Переписка внутри клиента, как обсуждали ваше КП. Вердикт гендира голосом. "
        "Три читателя: кто платит, кто продвигает, кто будет с этим жить, и что подумал каждый. "
        "Прогон по шести опорам с цитатами из КП и переписанными фрагментами. "
        "Флаги на экране блокировки. Исправленная первая страница, скачивается в Word и PDF. "
        "План правок на час с таймером. Методика со ссылками на посты.\n\n"
        "Как посмотреть пример\n"
        "1. Скачайте файл выше и откройте в браузере на компьютере.\n"
        "2. Пройдите сверху вниз: чат проигрывается сам, диктофон и таймер запускаются кнопками, "
        "опоры раскрываются, экран телефона раскрывается по тапу.\n"
        "3. В разделе «Исправленная первая страница» нажмите «Развернуть», ниже появятся Word и PDF.\n\n"
        "Как прогнать свое КП через агента\n"
        "1. Откройте Claude Code, Cursor или другого агента с доступом к файлам.\n"
        "2. Дайте ему ссылку на репозиторий: " + repo_url + "\n"
        "3. Приложите текст или файл вашего КП.\n"
        "4. Ответьте на шесть вопросов: клиент, проект, кто получит КП, стадия сделки, "
        "цель клиента, бюджет.\n"
        "5. Скажите: прогони КП по prompt.md из репозитория и собери report.html.\n"
        "6. Агент заполнит данные по схеме, проверит их и отдаст файл отчета. "
        "Откройте его в браузере.\n\n"
        "Как прогнать свое КП из терминала\n"
        "1. Клонируйте репозиторий: git clone " + repo_url + "\n"
        "2. Поставьте uv, инструкция на docs.astral.sh/uv.\n"
        "3. В папке репозитория выполните uv sync.\n"
        "4. Положите ключ модели в переменную окружения ANTHROPIC_API_KEY.\n"
        "5. Запустите: uv run goodkp run kp.pdf --answers answers.yaml. "
        "Без файла answers.yaml команда задаст шесть вопросов сама.\n"
        "6. Готовый report.html появится рядом с КП.\n"
        "Команда в работе, появится в ближайшем обновлении. Путь через агента работает уже сейчас.\n\n"
        "Методика\n"
        "В README раздел «Методика»: шесть опор с вопросом клиента и тем, что проверяется, "
        "и десять принципов Вадима со ссылками на посты.\n\n"
        "Вопросы и баги: @vintersbrain. Если разбор оказался полезным, расскажите о нем."
    )


def raw_url(repo_url: str, path: str) -> str:
    base = repo_url.rstrip("/").replace("github.com", "raw.githubusercontent.com")
    return f"{base}/main/{path}"


def welcome_markup(channels: list[str]) -> dict:
    buttons = [[{"text": channel_label(c), "url": f"https://t.me/{c}"}] for c in channels]
    buttons.append([{"text": "Получить ссылку", "callback_data": "recheck"}])
    return {"inline_keyboard": buttons}


def send_access(chat_id: int, repo_url: str) -> None:
    """Три сообщения: скриншот, файл примера, подробная инструкция."""
    tg("sendPhoto", chat_id=chat_id, photo=raw_url(repo_url, "docs/preview.png"),
       caption=ACCESS_PHOTO_CAPTION)
    tg("sendDocument", chat_id=chat_id, document=raw_url(repo_url, "examples/stroymarket.html"),
       caption=ACCESS_FILE_CAPTION)
    tg("sendMessage", chat_id=chat_id, text=access_text(repo_url),
       disable_web_page_preview=True)


def build_reply(status: dict, repo_url: str, channels: list[str]):
    """Текст и клавиатура для случая, когда доступ пока закрыт.
    Для открытого доступа возвращает короткий текст без клавиатуры,
    сами материалы шлет send_access."""
    if all(status.get(c) == "ok" for c in channels):
        return f"Готово, подписки на месте. Репозиторий: {repo_url}", None

    missing = [c for c in channels if status.get(c) == "no"]
    unknown = [c for c in channels if status.get(c) == "unknown"]

    lines = []
    if missing:
        names = ", ".join(f"@{c}" for c in missing)
        lines.append(f"Пока не вижу подписки на {names}.")
        lines.append("Подпишитесь и нажмите «Проверить снова». Проверка занимает секунду.")
    if unknown:
        names = ", ".join(f"@{c}" for c in unknown)
        lines.append(
            f"В канале {names} бот еще не администратор, проверить подписку не могу. "
            "Это на стороне авторов, скоро починим. Нажмите «Проверить снова» позже."
        )
    text = "\n".join(lines)

    buttons = [
        [{"text": channel_label(c), "url": f"https://t.me/{c}"}]
        for c in channels if status.get(c) != "ok"
    ]
    buttons.append([{"text": "Проверить снова", "callback_data": "recheck"}])
    return text, {"inline_keyboard": buttons}


def _is_not_modified(response: dict) -> bool:
    description = response.get("description", "")
    return "message is not modified" in description


def handle_update(update: dict) -> None:
    channels, repo_url = get_config()

    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        if (message.get("text") or "").strip().startswith("/start"):
            tg("sendMessage", chat_id=chat_id, text=WELCOME,
               reply_markup=welcome_markup(channels), disable_web_page_preview=True)
            return
        status = check_subscriptions(user_id, channels)
        if all(status.get(c) == "ok" for c in channels):
            send_access(chat_id, repo_url)
            return
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
        if all(status.get(c) == "ok" for c in channels):
            send_access(chat_id, repo_url)
        return
