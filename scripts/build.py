"""Собирает отчет Good КП из report.json. Только стандартная библиотека.

  python3 scripts/build.py report.json                 -> рядом с JSON появится .html
  python3 scripts/build.py report.json out.html
  python3 scripts/build.py report.json --check         -> только проверка, без файла

Проверяет то, на чем чаще всего ломается отчет, чинит мелочи (е вместо ё,
убирает точку-разделитель) и вставляет данные в шаблон assets/template.html.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "assets" / "template.html"
DATA_TAG = '<script type="application/json" id="data"></script>'
NEED = ["meta", "intake", "readers", "chat", "verdict", "blocks", "flags", "holds", "fixed_page", "plan", "source"]
STEPS = ["1", "2", "3", "4", "5", "6"]


def fix_strings(node):
    """е вместо ё, без точки-разделителя, во всех строках рекурсивно."""
    if isinstance(node, str):
        return node.replace("ё", "е").replace("Ё", "Е").replace("·", "").replace("  ", " ")
    if isinstance(node, list):
        return [fix_strings(x) for x in node]
    if isinstance(node, dict):
        return {k: fix_strings(v) for k, v in node.items()}
    return node


def dashes(node, path="", found=None):
    found = [] if found is None else found
    if isinstance(node, str):
        if "—" in node:
            found.append(path)
    elif isinstance(node, list):
        for i, x in enumerate(node):
            dashes(x, f"{path}[{i}]", found)
    elif isinstance(node, dict):
        for k, v in node.items():
            dashes(v, f"{path}.{k}" if path else k, found)
    return found


def check(d):
    p = []
    if d.get("refusal"):
        r = d["refusal"]
        return [f"отказ: {r.get('reason', '')} {r.get('hint', '')}".strip()]
    missing = [k for k in NEED if k not in d]
    if missing:
        return ["нет полей: " + ", ".join(missing)]
    if len(d["intake"]) != 6:
        p.append("intake: нужно ровно 6 пар")
    kinds = [r.get("kind") for r in d["readers"]]
    if kinds != ["decider", "champion", "executor"]:
        p.append(f"readers: порядок decider, champion, executor, сейчас {kinds}")
    for r in d["readers"]:
        for k in ("name", "role", "matters", "reads", "outcome", "feed"):
            if not r.get(k):
                p.append(f"readers[{r.get('name', '?')}]: нет поля {k}")
        steps = [f.get("step") for f in r.get("feed", []) if f.get("step") != "pre"]
        if steps != STEPS:
            p.append(f"feed у {r.get('name', '?')}: шаги 1..6 по порядку, сейчас {steps}")
        if r.get("kind") != "decider" and any(f.get("step") == "pre" for f in r.get("feed", [])):
            p.append(f"feed у {r.get('name', '?')}: шаг pre только у decider")
        for f in r.get("feed", []):
            if (f.get("state") == "drop") != bool(f.get("badge")):
                p.append(f"feed у {r.get('name', '?')}: badge есть только и обязательно при state drop")
    if not 8 <= len(d["chat"]) <= 14:
        p.append(f"chat: от 8 до 14 сообщений, сейчас {len(d['chat'])}")
    timers = sorted(m.get("timer") for m in d["chat"] if m.get("timer"))
    if timers != ["start", "stop"]:
        p.append("chat: ровно один timer start и один timer stop")
    for i, m in enumerate(d["chat"]):
        if not m.get("text") and not m.get("file"):
            p.append(f"chat[{i}]: пустой текст допустим только с file")
        if m.get("status") not in (None, "Прочитано", "Доставлено"):
            p.append(f"chat[{i}]: status только Прочитано или Доставлено")
    words = len(d["verdict"].get("text", "").split())
    if not 25 <= words <= 60:
        p.append(f"verdict: от 25 до 60 слов, сейчас {words}")
    if [b.get("id") for b in d["blocks"]] != [1, 2, 3, 4, 5, 6]:
        p.append("blocks: ровно 6 с id 1..6 по порядку")
    ids = {s.get("id") for s in d["source"]}
    for b in d["blocks"]:
        for k in ("title", "summary", "state", "quote", "why", "do", "was", "now"):
            if not b.get(k):
                p.append(f"blocks[{b.get('id')}]: нет поля {k}")
        if b.get("state") not in ("ok", "weak", "crit"):
            p.append(f"blocks[{b.get('id')}]: state только ok, weak, crit")
        if b.get("quote_src") and b["quote_src"] not in ids:
            p.append(f"blocks[{b.get('id')}]: quote_src {b['quote_src']} нет в source")
        if len(b.get("summary", "")) > 60:
            p.append(f"blocks[{b.get('id')}]: summary до 60 символов")
    if not 4 <= len(d["flags"]) <= 6:
        p.append(f"flags: от 4 до 6, сейчас {len(d['flags'])}")
    names = {r.get("name") for r in d["readers"]}
    for f in d["flags"]:
        if f.get("from") not in names:
            p.append(f"flags: from должен быть именем читателя, сейчас {f.get('from')}")
        if not f.get("title") or not f.get("text"):
            p.append("flags: у каждого title и text")
    if not 2 <= len(d["holds"]) <= 5:
        p.append(f"holds: от 2 до 5, сейчас {len(d['holds'])}")
    fp = d["fixed_page"]
    if len(fp.get("sections", [])) != 6 or not fp.get("contacts") or not fp.get("subject"):
        p.append("fixed_page: subject, contacts и ровно 6 sections")
    total = sum(int(s.get("minutes", 0)) for s in d["plan"])
    if not 4 <= len(d["plan"]) <= 6 or total != 60:
        p.append(f"plan: от 4 до 6 шагов, сумма минут ровно 60, сейчас {len(d['plan'])} шагов и {total} минут")
    if [s.get("id") for s in d["source"]] != [f"src-{i}" for i in range(1, len(d["source"]) + 1)]:
        p.append("source: id подряд src-1..N")
    for s in d["source"]:
        if s.get("kind") == "list" and not s.get("items"):
            p.append(f"source {s.get('id')}: пустой список")
        if s.get("kind") == "table" and not all(s.get("rows") or [[]]):
            p.append(f"source {s.get('id')}: пустая таблица")
    if len(d["meta"].get("title", "")) > 60 or ":" in d["meta"].get("title", ""):
        p.append("meta.title: до 60 символов, без двоеточий")
    dd = dashes(d)
    if dd:
        p.append("длинное тире в полях: " + ", ".join(dd[:10]) + ". Замените на запятую или точку")
    return p


def build(data: dict) -> str:
    tpl = TEMPLATE.read_text(encoding="utf-8")
    if DATA_TAG not in tpl:
        raise SystemExit("в шаблоне нет пустого блока данных")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace(DATA_TAG, DATA_TAG.replace("></script>", ">" + payload + "</script>"), 1)


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    src = Path(argv[0])
    data = fix_strings(json.loads(src.read_text(encoding="utf-8")))
    problems = check(data)
    if problems:
        print("Отчет не собран, исправьте данные:")
        for x in problems:
            print(" -", x)
        raise SystemExit(2)
    if "--check" in argv:
        print("ok")
        return
    client = re.sub(r"^ООО\s+", "", data["meta"].get("client", "")).replace("«", "").replace("»", "").strip() or "клиент"
    out = Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else src.with_name(f"КП {client}, прогон.html")
    out.write_text(build(data), encoding="utf-8")
    print(out)
    print(data["meta"].get("title", ""))


if __name__ == "__main__":
    main(sys.argv[1:])
