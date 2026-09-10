import json
import pytest
from pydantic import ValidationError
from goodkp.schema import Report, export_schema


def minimal() -> dict:
    reader = lambda kind, name: {
        "name": name, "role": "роль", "kind": kind,
        "matters": "м", "reads": "р", "outcome": "и",
        "feed": [{"step": str(i), "text": "т", "state": "ok"} for i in range(1, 7)],
    }
    block = lambda i: {
        "id": i, "title": "Опора", "summary": "кратко", "state": "crit",
        "quote": "ц", "quote_src": None, "why": "п", "do": "д", "was": "б", "now": "с",
    }
    return {
        "version": "1.0.0", "methodology_version": "1.0", "refusal": None,
        "meta": {"kp_number": "0417", "kp_date": "2026-08-21", "vendor": "Пиксель Лаб",
                 "client": "ООО «СтройМаркет»", "run_date": "2026-09-07T14:24:00+03:00",
                 "title": "До стола директора это КП не дойдет"},
        "intake": [{"k": f"к{i}", "v": "з"} for i in range(6)],
        "readers": [reader("decider", "Сергей"), reader("champion", "Ольга"), reader("executor", "Дмитрий")],
        "chat": [{"side": "me", "text": "а"}] * 6 + [
            {"side": "them", "name": "Сергей", "text": "б", "timer": "start"},
            {"side": "them", "name": "Сергей", "text": "в", "timer": "stop"},
        ],
        "verdict": {"speaker": "Сергей, гендир", "text": " ".join(["слово"] * 40)},
        "blocks": [block(i) for i in range(1, 7)],
        "flags": [{"from": "Сергей", "title": "з", "text": "т"}] * 4,
        "holds": [{"title": "з", "text": "т"}] * 2,
        "fixed_page": {"subject": "т", "from_initials": "ПЛ",
                       "sections": [{"title": "з", "text": "т"}] * 6},
        "plan": [{"title": "з", "text": "т", "minutes": 15}] * 4,
        "source": [{"id": "src-1", "kind": "p", "text": "абзац"}],
    }


def test_minimal_is_valid():
    Report.model_validate(minimal())


def test_seven_blocks_rejected():
    d = minimal(); d["blocks"].append(d["blocks"][0] | {"id": 7})
    with pytest.raises(ValidationError, match="blocks"):
        Report.model_validate(d)


def test_readers_order_enforced():
    d = minimal(); d["readers"][0], d["readers"][1] = d["readers"][1], d["readers"][0]
    with pytest.raises(ValidationError, match="decider, champion, executor"):
        Report.model_validate(d)


def test_timer_start_and_stop_required():
    d = minimal(); d["chat"][-1].pop("timer")
    with pytest.raises(ValidationError, match="timer"):
        Report.model_validate(d)


def test_plan_minutes_total_bounds():
    d = minimal(); d["plan"] = [{"title": "з", "text": "т", "minutes": 5}] * 4
    with pytest.raises(ValidationError, match="45"):
        Report.model_validate(d)


def test_banned_glyphs_rejected():
    d = minimal(); d["verdict"]["text"] = "тире — тут"
    with pytest.raises(ValidationError, match="—"):
        Report.model_validate(d)
    d = minimal(); d["meta"]["title"] = "ёлка"
    with pytest.raises(ValidationError, match="ё"):
        Report.model_validate(d)


def test_source_block_needs_payload():
    d = minimal(); d["source"] = [{"id": "src-1", "kind": "list", "text": "нет items"}]
    with pytest.raises(ValidationError, match="items"):
        Report.model_validate(d)


def test_dangling_quote_src_rejected():
    d = minimal(); d["blocks"][0]["quote_src"] = "src-99"
    with pytest.raises(ValidationError, match="src-99"):
        Report.model_validate(d)


def test_refusal_short_circuits():
    Report.model_validate({"version": "1.0.0", "methodology_version": "1.0",
                           "refusal": {"reason": "Это не КП", "hint": "Пришлите документ с предложением и ценой"}})


def test_export_schema_roundtrip():
    s = export_schema()
    assert s["title"] == "Report" and "blocks" in s["properties"]
    json.dumps(s)
