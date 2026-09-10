import json

import pytest

import bot.core as core
from api.webhook import process


class FakeAPI:
    """Стаб вместо реального HTTP вызова Telegram."""

    def __init__(self, member_status=None):
        self.member_status = member_status or {}
        self.calls = []
        self.edit_response = {"ok": True, "result": True}

    def __call__(self, method, params):
        self.calls.append((method, dict(params)))
        if method == "getChatMember":
            channel = params["chat_id"].lstrip("@")
            return self.member_status.get(
                channel, {"ok": True, "result": {"status": "member"}}
            )
        if method == "editMessageText":
            return self.edit_response
        return {"ok": True, "result": True}

    def calls_for(self, method):
        return [p for m, p in self.calls if m == method]


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("CHANNELS", "vintersbrain,ShkolnyiAccount")
    monkeypatch.setenv("REPO_URL", "https://github.com/vinter/good-kp")
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)


@pytest.fixture
def api(monkeypatch):
    fake = FakeAPI()
    monkeypatch.setattr(core, "API", fake)
    return fake


def message_update(user_id=1, chat_id=1, text="/start"):
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "chat": {"id": chat_id, "type": "private"},
            "date": 0,
            "text": text,
        },
    }


def callback_update(user_id=1, chat_id=1, message_id=10, callback_id="cb1"):
    return {
        "update_id": 2,
        "callback_query": {
            "id": callback_id,
            "from": {"id": user_id, "is_bot": False, "first_name": "T"},
            "message": {
                "message_id": message_id,
                "chat": {"id": chat_id, "type": "private"},
                "date": 0,
                "text": "старый текст",
            },
            "data": "recheck",
        },
    }


def test_all_subscribed_replies_with_repo_link(api):
    core.handle_update(message_update())

    sent = api.calls_for("sendMessage")
    assert len(sent) == 1
    text = sent[0]["text"]
    assert "https://github.com/vinter/good-kp" in text
    assert "reply_markup" not in sent[0] or sent[0]["reply_markup"] is None
    assert text.count("\n") >= 2


def test_one_channel_missing_lists_it_and_shows_keyboard(api):
    api.member_status["ShkolnyiAccount"] = {"ok": True, "result": {"status": "left"}}

    core.handle_update(message_update())

    sent = api.calls_for("sendMessage")
    assert len(sent) == 1
    text = sent[0]["text"]
    assert "Вадима" in text or "ShkolnyiAccount" in text

    markup = sent[0]["reply_markup"]
    rows = markup["inline_keyboard"]
    url_buttons = [b for row in rows for b in row if "url" in b]
    callback_buttons = [b for row in rows for b in row if b.get("callback_data") == "recheck"]
    assert len(url_buttons) == 2
    assert len(callback_buttons) == 1


def test_unknown_channel_reports_bot_not_admin(api):
    api.member_status["vintersbrain"] = {
        "ok": False,
        "description": "Bad Request: member list is inaccessible",
    }

    core.handle_update(message_update())

    text = api.calls_for("sendMessage")[0]["text"]
    assert "vintersbrain" in text or "Кристины" in text
    assert "админ" in text.lower()


def test_callback_recheck_answers_and_edits_message(api):
    core.handle_update(callback_update())

    answered = api.calls_for("answerCallbackQuery")
    edited = api.calls_for("editMessageText")
    assert len(answered) == 1
    assert answered[0]["callback_query_id"] == "cb1"
    assert len(edited) == 1
    assert edited[0]["chat_id"] == 1
    assert edited[0]["message_id"] == 10


def test_callback_message_not_modified_is_swallowed(api):
    api.edit_response = {
        "ok": False,
        "description": "Bad Request: message is not modified",
    }

    core.handle_update(callback_update())  # не должно бросать исключение


def test_check_subscriptions_maps_statuses(api):
    api.member_status["vintersbrain"] = {"ok": True, "result": {"status": "administrator"}}
    api.member_status["ShkolnyiAccount"] = {
        "ok": True,
        "result": {"status": "restricted", "is_member": False},
    }

    status = core.check_subscriptions(1, ["vintersbrain", "ShkolnyiAccount"])

    assert status == {"vintersbrain": "ok", "ShkolnyiAccount": "no"}


def test_build_reply_all_ok_has_no_keyboard():
    text, markup = core.build_reply(
        {"a": "ok", "b": "ok"}, "https://repo", ["a", "b"]
    )
    assert "https://repo" in text
    assert markup is None


# --- webhook ---


def test_webhook_rejects_wrong_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    status, payload = process(b"{}", "wrong")
    assert status == 403


def test_webhook_accepts_correct_secret(monkeypatch, api):
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")
    body = json.dumps(message_update()).encode("utf-8")

    status, payload = process(body, "s3cret")

    assert status == 200
    assert payload == {"ok": True}
    assert api.calls_for("sendMessage")


def test_webhook_no_secret_configured_allows_any_header(monkeypatch, api):
    body = json.dumps({"update_id": 1}).encode("utf-8")

    status, payload = process(body, None)

    assert status == 200


def test_webhook_invalid_json_returns_400():
    status, payload = process(b"not json", None)
    assert status == 400
