# Good КП, фаза 1: схема данных и шаблон на данных

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Превратить прототип отчета в шаблон, который рендерит любой валидный `report.json`, и получить Python-рендерер с тестами. Модель и CLI будут в фазе 2.

**Architecture:** Один HTML-файл `template/report.html` содержит стили, каркас секций, JS-рендеры и интерактивы. Данные приходят в `<script type="application/json" id="data">`. Pydantic-модели в `goodkp/schema.py` задают контракт, `goodkp/render.py` вставляет JSON и оборачивает каркасом. Golden-набор извлекается из прототипа, и тест Playwright проверяет, что шаблон на golden JSON дает тот же текст, что прототип.

**Tech Stack:** Python 3.11+, uv, pydantic 2, pytest, beautifulsoup4 + lxml (только для извлечения golden), Playwright (chromium), ванильный JS в шаблоне.

## Global Constraints

- Спека: `docs/superpowers/specs/2026-09-10-good-kp-design.md`. Контракт данных в разделе 5 спеки обязателен.
- В тексте интерфейса: без «—», без «·», без ё, без «не X, а Y». Проверять `grep` перед коммитом шаблона.
- Шаблон без каркаса: в `template/report.html` нет `<!doctype>`, `<html>`, `<head>`, `<body>`. Каркас добавляет `render.py`.
- Только темная тема: `color-scheme: dark`, ни одного `prefers-color-scheme` и `data-theme` в шаблоне.
- Внешние скрипты только JSZip с cdnjs (уже есть в прототипе).
- Коммиты завершаются строками:
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01EHASJP1XNNhrAe9BNqjJvL`
- Прототип-источник: `/Users/vinter/.claude/skills/tg-post/good-kp-source.html` (без каркаса, 1468 строк). Его копия кладется в `tests/fixtures/prototype.html` и больше не меняется.

---

## Файлы фазы 1

- `pyproject.toml`: пакет `goodkp`, зависимости, pytest.
- `goodkp/__init__.py`: версия.
- `goodkp/schema.py`: pydantic-модели, `Report`, `export_schema()`.
- `goodkp/render.py`: `render(data, template) -> str`, `wrap(inner) -> str`, `load_template()`.
- `schema/report.schema.json`: экспорт схемы (коммитится).
- `template/report.html`: шаблон на данных.
- `scripts/extract_golden.py`: прототип -> `tests/golden/stroymarket/report.json`.
- `tests/fixtures/prototype.html`: неизменяемая копия прототипа.
- `tests/golden/stroymarket/report.json`: golden-данные.
- `tests/test_schema.py`, `tests/test_render.py`, `tests/test_ui.py`, `tests/conftest.py`.

---

### Task 1: Каркас репозитория

**Files:**
- Create: `pyproject.toml`, `goodkp/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `.gitignore`
- Create: `tests/fixtures/prototype.html` (копия), `template/report.html` (копия, будет меняться)

**Interfaces:**
- Produces: `ROOT` в conftest (Path корня репо), фикстуры `template_path`, `prototype_path`, `golden_path`.

- [ ] **Step 1: pyproject**

```toml
[project]
name = "goodkp"
version = "0.1.0"
description = "Разбор коммерческого предложения глазами клиента по методике Вадима Школьного"
requires-python = ">=3.11"
dependencies = ["pydantic>=2.7"]

[project.scripts]
goodkp = "goodkp.cli:main"

[dependency-groups]
dev = ["pytest>=8", "beautifulsoup4>=4.12", "lxml>=5", "playwright>=1.45", "pytest-playwright>=0.5"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["goodkp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: пакет и conftest**

`goodkp/__init__.py`:
```python
__version__ = "0.1.0"
```

`tests/conftest.py`:
```python
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def template_path() -> Path:
    return ROOT / "template" / "report.html"

@pytest.fixture
def prototype_path() -> Path:
    return ROOT / "tests" / "fixtures" / "prototype.html"

@pytest.fixture
def golden_path() -> Path:
    return ROOT / "tests" / "golden" / "stroymarket" / "report.json"
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
test-results/
tests/screenshots/actual/
```

- [ ] **Step 3: копии прототипа**

```bash
mkdir -p tests/fixtures template
cp /Users/vinter/.claude/skills/tg-post/good-kp-source.html tests/fixtures/prototype.html
cp /Users/vinter/.claude/skills/tg-post/good-kp-source.html template/report.html
head -c 200 template/report.html   # должно начинаться с <title>, без doctype
```

- [ ] **Step 4: окружение и пустой прогон**

```bash
uv sync --group dev
uv run playwright install chromium
uv run pytest -q
```
Expected: `no tests ran`, код 5 допустим.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Каркас: пакет goodkp, прототип как фикстура и стартовый шаблон"
```

---

### Task 2: Схема данных (pydantic)

**Files:**
- Create: `goodkp/schema.py`, `tests/test_schema.py`, `schema/report.schema.json`

**Interfaces:**
- Produces: `Report` (pydantic), `Report.model_validate(dict)`, `export_schema() -> dict`, константы `PILLARS = 6`, `READERS = 3`.

- [ ] **Step 1: failing tests**

`tests/test_schema.py`:
```python
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
        "flags": [{"from": "Сергей", "text": "т"}] * 4,
        "holds": [{"title": "з", "text": "т"}] * 2,
        "fixed_page": {"subject": "т", "from_initials": "ПЛ",
                       "sections": [{"title": "з", "text": "т"}] * 6},
        "plan": [{"title": "з", "text": "т", "minutes": 15}] * 4,
        "source": [{"id": "src-1", "text": "абзац"}],
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


def test_refusal_short_circuits():
    Report.model_validate({"version": "1.0.0", "methodology_version": "1.0",
                           "refusal": {"reason": "Это не КП", "hint": "Пришлите документ с предложением и ценой"}})


def test_export_schema_roundtrip():
    s = export_schema()
    assert s["title"] == "Report" and "blocks" in s["properties"]
    json.dumps(s)
```

- [ ] **Step 2: run, expect ImportError**

`uv run pytest tests/test_schema.py -q` → FAIL, `No module named 'goodkp.schema'`.

- [ ] **Step 3: implementation**

`goodkp/schema.py`:
```python
"""Контракт данных отчета. Модель возвращает только это. Раздел 5 спеки."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

PILLARS = 6
READERS = 3
BANNED = ("—", "·", "ё", "Ё")


class Strict(BaseModel):
    model_config = {"extra": "forbid"}

    @field_validator("*", mode="before")
    @classmethod
    def _no_banned(cls, v):
        if isinstance(v, str):
            for g in BANNED:
                if g in v:
                    raise ValueError(f"запрещенный символ {g!r} в тексте: {v[:60]!r}")
        return v


class Refusal(Strict):
    reason: str
    hint: str


class Meta(Strict):
    kp_number: str
    kp_date: str
    vendor: str
    client: str
    run_date: str
    title: str = Field(max_length=60)


class KV(Strict):
    k: str
    v: str


class FeedItem(Strict):
    step: Literal["pre", "1", "2", "3", "4", "5", "6"]
    text: str
    state: Literal["ok", "drop", "off"]


class Reader(Strict):
    name: str
    role: str
    kind: Literal["decider", "champion", "executor"]
    matters: str
    reads: str
    outcome: str
    feed: list[FeedItem] = Field(min_length=6, max_length=7)


class ChatFile(Strict):
    name: str
    size: str


class ChatMsg(Strict):
    side: Literal["me", "them"]
    name: Optional[str] = None
    text: str = ""
    file: Optional[ChatFile] = None
    status: Optional[Literal["Прочитано", "Доставлено"]] = None
    timer: Optional[Literal["start", "stop"]] = None


class Verdict(Strict):
    speaker: str
    text: str


class Block(Strict):
    id: int = Field(ge=1, le=PILLARS)
    title: str
    summary: str = Field(max_length=60)
    state: Literal["ok", "weak", "crit"]
    quote: str
    quote_src: Optional[str] = Field(default=None, pattern=r"^src-\d+$")
    why: str
    do: str
    was: str
    now: str


class Flag(Strict):
    from_: str = Field(alias="from")
    text: str
    model_config = {"extra": "forbid", "populate_by_name": True}


class Hold(Strict):
    title: str
    text: str


class Section(Strict):
    title: str
    text: str


class FixedPage(Strict):
    subject: str
    from_initials: str = Field(max_length=3)
    sections: list[Section] = Field(min_length=PILLARS, max_length=PILLARS)


class PlanStep(Strict):
    title: str
    text: str
    minutes: int = Field(ge=1, le=40)


class SourcePara(Strict):
    id: str = Field(pattern=r"^src-\d+$")
    text: str


class Report(Strict):
    version: str
    methodology_version: str
    refusal: Optional[Refusal] = None
    meta: Optional[Meta] = None
    intake: Optional[list[KV]] = Field(default=None, min_length=6, max_length=6)
    readers: Optional[list[Reader]] = Field(default=None, min_length=READERS, max_length=READERS)
    chat: Optional[list[ChatMsg]] = Field(default=None, min_length=8, max_length=14)
    verdict: Optional[Verdict] = None
    blocks: Optional[list[Block]] = Field(default=None, min_length=PILLARS, max_length=PILLARS)
    flags: Optional[list[Flag]] = Field(default=None, min_length=4, max_length=6)
    holds: Optional[list[Hold]] = Field(default=None, min_length=2, max_length=4)
    fixed_page: Optional[FixedPage] = None
    plan: Optional[list[PlanStep]] = Field(default=None, min_length=4, max_length=6)
    source: Optional[list[SourcePara]] = None

    @model_validator(mode="after")
    def _full_or_refusal(self):
        if self.refusal is not None:
            return self
        required = ["meta", "intake", "readers", "chat", "verdict", "blocks",
                    "flags", "holds", "fixed_page", "plan", "source"]
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(f"без refusal обязательны поля: {', '.join(missing)}")
        kinds = [r.kind for r in self.readers]
        if kinds != ["decider", "champion", "executor"]:
            raise ValueError("readers должны идти в порядке decider, champion, executor")
        timers = [m.timer for m in self.chat if m.timer]
        if sorted(timers) != ["start", "stop"]:
            raise ValueError("в chat нужен ровно один timer:start и один timer:stop")
        if [b.id for b in self.blocks] != list(range(1, PILLARS + 1)):
            raise ValueError("blocks должны иметь id 1..6 по порядку")
        total = sum(p.minutes for p in self.plan)
        if not 45 <= total <= 75:
            raise ValueError(f"сумма minutes в plan должна быть от 45 до 75, сейчас {total}")
        words = len(self.verdict.text.split())
        if not 25 <= words <= 70:
            raise ValueError(f"verdict.text: от 25 до 70 слов, сейчас {words}")
        return self


def export_schema() -> dict:
    return Report.model_json_schema(by_alias=True)
```

Примечание: pydantic сообщает об ошибке длины списка с именем поля, поэтому `match="blocks"` сработает. Для порядка readers сообщение содержит фразу из `ValueError`.

- [ ] **Step 4: run** `uv run pytest tests/test_schema.py -q` → 8 passed.

- [ ] **Step 5: экспорт схемы**

```bash
mkdir -p schema && uv run python -c "import json; from goodkp.schema import export_schema; open('schema/report.schema.json','w').write(json.dumps(export_schema(), ensure_ascii=False, indent=1))"
```

- [ ] **Step 6: Commit** `git add -A && git commit -m "Схема отчета: pydantic-контракт и экспорт JSON-схемы"`

---

### Task 3: Golden-данные из прототипа

**Files:**
- Create: `scripts/extract_golden.py`, `tests/golden/stroymarket/report.json`, `tests/test_golden.py`

**Interfaces:**
- Consumes: `Report` из Task 2.
- Produces: `tests/golden/stroymarket/report.json`, валидный по `Report`. Ключевые правила извлечения ниже, они же определяют, как рендеры в Task 5 должны читать данные.

Правила извлечения (селекторы по `tests/fixtures/prototype.html`):

| Поле | Откуда |
|---|---|
| `meta.title` | `.hero h1` |
| `meta.kp_number`, `kp_date`, `vendor`, `client` | `header .meta b` («КП №0417 от 21.08.2026») и вторая строка («Пиксель Лаб» для ООО «СтройМаркет») |
| `meta.run_date` | «Прогон 07.09.2026» + `#noteDate` время → ISO `2026-09-07T14:24:00+03:00` |
| `hero_lead` не хранится: абзац под h1 генерируется из `blocks[].state` (см. Task 5) |
| `chat` | `#chat .m`: `me/them` по классу, `data-name`, `.b` текст, `.file` → `{name: b, size: i}`, `.st` → status, `data-timer` |
| `intake` | `.intake > div` → `.k`, `.v` |
| `verdict` | `.memo-t b` → speaker, `#memoQ` → text (склеить span через пробел) |
| `readers` | `#readers .pane` по порядку; `.pc h3` name, `.pc div div` role, `.ptiles div:nth(1) p` matters, `nth(2) p` reads, `.pt-final p` outcome; `.feed .msg` → `step` из `.step` («Сначала цена» → `pre`, «1. Проблема» → `1`), `state`: класс `drop`→drop, `off`→off, иначе ok |
| `blocks` | `.block`: `.i` id, `.bt b` title, `.bt > span > span` summary, класс `crit/weak/ok` state, `.kpq p` quote, `.findsrc[data-src]` quote_src, `.bwhy` why, `.bdo` do без «Что делать.», `.was` was, `.now` now |
| `flags` | `#nstack .ncard`: имя отправителя `.nh b` или `.nname`, текст `.nt` (проверить фактические классы в прототипе, `grep -o 'class="n[a-z]*"'`) |
| `holds` | `.holds li`: `b` title без завершающей точки, остальной текст |
| `fixed_page` | `.msubj` subject, `.mav` from_initials, `#docBody .ds` кроме `#docCta`: `h4`, `p` (плейсхолдеры `.ph` в квадратных скобках как есть) |
| `plan` | `#plan li`: `data-min`, `.t` первый текстовый узел title, вложенный `span` text |
| `source` | `#s-source .kp` детей: каждый `h3` и `p` с `id="src-N"` или без; узлы без id получают `src-N` по счету, `h3` префикс `## ` в тексте |

Все тексты: `get_text()` с `\xa0` → обычный пробел (nbsp вернет `typo.py` в фазе 2, а в шаблоне JS ставит nbsp при рендере, см. Task 5).

- [ ] **Step 1: failing test**

`tests/test_golden.py`:
```python
import json
from goodkp.schema import Report

def test_golden_valid(golden_path):
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    r = Report.model_validate(data)
    assert r.meta.title == "До стола директора это КП не дойдет"
    assert [b.state for b in r.blocks].count("crit") == 3
    assert r.readers[0].name == "Сергей" and r.readers[0].feed[0].step == "pre"
    assert sum(p.minutes for p in r.plan) == 60
    assert any(m.file for m in r.chat)
```

- [ ] **Step 2: run** → FAIL, файла нет.

- [ ] **Step 3: скрипт извлечения**

`scripts/extract_golden.py` (запуск `uv run python scripts/extract_golden.py`):
```python
"""Прототип -> golden report.json. Одноразовый, но воспроизводимый."""
import json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from goodkp.schema import Report

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tests/fixtures/prototype.html"
OUT = ROOT / "tests/golden/stroymarket/report.json"

def t(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\xa0", " ")).strip() if node else ""

soup = BeautifulSoup(SRC.read_text(encoding="utf-8"), "lxml")
meta_b, meta_lines = soup.select_one("header .meta b"), [s for s in soup.select_one("header .meta").stripped_strings]
m = re.match(r"КП №(\S+) от (\S+)", t(meta_b))
vendor, client = re.match(r"«(.+?)» для (.+)", meta_lines[1].replace("\xa0", " ")).groups()
d, mo, y = m.group(2).split(".")

STEP = {"Сначала цена": "pre"}
def step_of(s):
    s = s.replace("\xa0", " ")
    return STEP.get(s) or s.split(".")[0]
def state_of(cls):
    return "drop" if "drop" in cls else "off" if "off" in cls else "ok"

readers = []
for pane in soup.select("#readers .pane"):
    tiles = pane.select(".ptiles > div")
    readers.append({
        "name": t(pane.select_one(".pc h3")), "role": t(pane.select_one(".pc h3").find_next_sibling()),
        "kind": ["decider", "champion", "executor"][len(readers)],
        "matters": t(tiles[0].p), "reads": t(tiles[1].p), "outcome": t(tiles[2].p),
        "feed": [{"step": step_of(t(li.select_one(".step"))), "text": t(li.p), "state": state_of(li.get("class", []))}
                 for li in pane.select(".feed .msg")],
    })

chat = []
for mm in soup.select("#chat .m"):
    msg = {"side": "me" if "me" in mm["class"] else "them", "text": t(mm.select_one(".b"))}
    if mm.get("data-name"): msg["name"] = mm["data-name"]
    f = mm.select_one(".file")
    if f: msg["file"] = {"name": t(f.b), "size": t(f.i)}
    st = mm.select_one(".st")
    if st: msg["status"] = t(st)
    if mm.get("data-timer"): msg["timer"] = mm["data-timer"]
    chat.append(msg)

blocks = []
for b in soup.select(".block"):
    cls = b.get("class", [])
    fs = b.select_one(".findsrc")
    blocks.append({
        "id": int(t(b.select_one(".i"))), "title": t(b.select_one(".bt b")),
        "summary": t(b.select_one(".bt > span > span")),
        "state": "crit" if "crit" in cls else "weak" if "weak" in cls else "ok",
        "quote": t(b.select_one(".kpq p")), "quote_src": fs["data-src"] if fs else None,
        "why": t(b.select_one(".bwhy")),
        "do": re.sub(r"^Что делать\.\s*", "", t(b.select_one(".bdo"))),
        "was": t(b.select_one(".was")), "now": t(b.select_one(".now")),
    })

flags = [{"from": t(c.select_one(".nh b, .nname")), "text": t(c.select_one(".nt, .nb"))} for c in soup.select("#nstack .ncard")]
holds = [{"title": t(li.b).rstrip("."), "text": t(li.select_one("span:last-child")).replace(t(li.b), "", 1).strip()}
         for li in soup.select(".holds li")]
sections = [{"title": t(ds.h4), "text": t(ds.p)} for ds in soup.select("#docBody .ds") if ds.h4]
plan = [{"title": li.select_one(".t").find(string=True, recursive=False).replace("\xa0", " ").strip(),
         "text": t(li.select_one(".t span")), "minutes": int(li["data-min"])} for li in soup.select("#plan li")]
source, n = [], 0
for el in soup.select_one("#s-source .kp").find_all(["h3", "p"], recursive=False):
    if "fine" in el.get("class", []): continue
    n += 1
    source.append({"id": el.get("id") or f"src-{n}", "text": ("## " if el.name == "h3" else "") + t(el)})

data = {
    "version": "1.0.0", "methodology_version": "1.0", "refusal": None,
    "meta": {"kp_number": m.group(1), "kp_date": f"{y}-{mo}-{d}", "vendor": vendor, "client": client,
             "run_date": "2026-09-07T14:24:00+03:00", "title": t(soup.select_one(".hero h1"))},
    "intake": [{"k": t(dv.select_one(".k")), "v": t(dv.select_one(".v"))} for dv in soup.select(".intake > div")],
    "readers": readers, "chat": chat,
    "verdict": {"speaker": t(soup.select_one(".memo-t b")), "text": t(soup.select_one("#memoQ"))},
    "blocks": blocks, "flags": flags, "holds": holds,
    "fixed_page": {"subject": t(soup.select_one(".msubj")), "from_initials": t(soup.select_one(".mav")), "sections": sections},
    "plan": plan, "source": source,
}
Report.model_validate(data)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", OUT, len(source), "абзацев источника")
```

Перед запуском проверить фактические классы карточек уведомлений и якорей источника:
```bash
grep -o 'class="n[a-z]*"' tests/fixtures/prototype.html | sort | uniq -c
grep -o 'id="src-[0-9]*"' tests/fixtures/prototype.html | head
```
и поправить селекторы `flags`/`source`, если отличаются. Если якорей `src-N` в источнике меньше, чем ссылок `quote_src` в блоках, скрипт упадет на валидации: тогда присвоить якоря так, чтобы каждый `quote_src` существовал (проверка добавляется в `Report`: в Task 2 она не нужна, здесь достаточно `assert {b['quote_src'] for b in blocks if b['quote_src']} <= {s['id'] for s in source}` перед записью).

- [ ] **Step 4: run** `uv run python scripts/extract_golden.py && uv run pytest tests/test_golden.py -q` → passed.

- [ ] **Step 5: Commit** `git add -A && git commit -m "Golden: данные СтройМаркета извлечены из прототипа"`

---

### Task 4: render.py

**Files:**
- Create: `goodkp/render.py`, `tests/test_render.py`

**Interfaces:**
- Consumes: `Report`.
- Produces: `load_template() -> str`, `inject(template: str, data: dict) -> str` (шаблон с JSON в `#data`), `wrap(inner: str) -> str` (каркас), `render(report: Report, template: str | None = None) -> str` (standalone HTML).

- [ ] **Step 1: failing tests**

`tests/test_render.py`:
```python
import json
from goodkp.render import inject, wrap, render, load_template
from goodkp.schema import Report

TPL = '<title>T</title><style>a{}</style><script type="application/json" id="data"></script><div>x</div>'

def test_inject_puts_json_in_data_block():
    out = inject(TPL, {"a": 1})
    assert '<script type="application/json" id="data">{"a": 1}</script>' in out

def test_inject_escapes_closing_script():
    out = inject(TPL, {"a": "</script><b>"})
    assert "</script><b>" not in out.split('id="data">')[1].split("</script>")[0]
    assert "<\\/script>" in out

def test_inject_refuses_template_without_data_block():
    import pytest
    with pytest.raises(ValueError, match="#data"):
        inject("<div></div>", {})

def test_wrap_adds_skeleton():
    out = wrap(TPL)
    assert out.startswith("<!doctype html><html lang=\"ru\"><head>")
    assert '<meta charset="utf-8">' in out and 'content="dark"' in out
    assert "[hidden]{display:none!important}" in out
    assert out.index("<title>") < out.index("</head>") < out.index("<div>x</div>")

def test_render_golden(golden_path):
    r = Report.model_validate(json.loads(golden_path.read_text(encoding="utf-8")))
    html = render(r)
    assert "До стола директора" in html and html.count('id="data"') == 1

def test_template_has_no_skeleton(template_path):
    s = load_template()
    assert "<!doctype" not in s.lower() and "<body" not in s
```

- [ ] **Step 2: run** → FAIL, нет модуля.

- [ ] **Step 3: implementation**

`goodkp/render.py`:
```python
"""JSON в шаблон, шаблон в каркас. Раздел 7 спеки."""
from __future__ import annotations
import json
import re
from pathlib import Path
from .schema import Report

TEMPLATE = Path(__file__).resolve().parent.parent / "template" / "report.html"
DATA_RE = re.compile(r'(<script type="application/json" id="data">)(.*?)(</script>)', re.S)
HEAD = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="dark">')
RESET = '<style>body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'


def load_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def inject(template: str, data: dict) -> str:
    if not DATA_RE.search(template):
        raise ValueError('в шаблоне нет <script type="application/json" id="data">')
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return DATA_RE.sub(lambda m: m.group(1) + payload + m.group(3), template, count=1)


def wrap(inner: str) -> str:
    """Голова: title и первый <style> шаблона. Тело: все от первого <script src= или первого не-head тега."""
    cut = inner.find("<script")
    if cut < 0:
        cut = len(inner)
    head, body = inner[:cut], inner[cut:]
    return HEAD + head + RESET + "</head><body>" + body + "</body></html>"


def render(report: Report, template: str | None = None) -> str:
    data = report.model_dump(by_alias=True, exclude_none=True)
    return wrap(inject(template or load_template(), data))
```

Замечание про `wrap`: шаблон начинается с `<title>` и `<style>`, а первый `<script` идет после них, поэтому разрез по первому `<script` кладет title и стили в head. В тестовом `TPL` первый script это блок данных, он уходит в body, что нормально.

- [ ] **Step 4: run** `uv run pytest tests/test_render.py -q` → `test_render_golden` упадет: в `template/report.html` еще нет блока `#data`. Добавить его в шаблон сразу после `<script>document.documentElement.classList.add('js')</script>`:

```html
<script type="application/json" id="data"></script>
```
Повторить → 6 passed.

- [ ] **Step 5: Commit** `git add -A && git commit -m "render: вставка JSON и каркас standalone-файла"`

---

### Task 5: Шаблон на данных

Самая большая задача. Разметка секций в шаблоне заменяется на пустые контейнеры, JS строит ее из `#data`. Интерактивы (чат, диктофон, readers, blocks, lock, torch/cam, doc, timer, toc, nav, method) не переписываются: они уже ищут элементы по id и классам, значит рендеры обязаны выдавать ту же разметку. Проверка эквивалентности: текст каждой секции на golden JSON равен тексту прототипа.

**Files:**
- Modify: `template/report.html`
- Create: `tests/test_ui.py` (первая часть), `tests/fixtures/expected_text.json`

**Interfaces:**
- Produces: в шаблоне глобальный объект `GK` с функциями `GK.render(data)`, `GK.init()` и `GK.nb(text)` (nbsp-типографика). Порядок в файле: `<script id="data">`, затем `<script>` с утилитами и рендерами, затем существующий `<script>` с интерактивами, которые теперь запускаются из `GK.init()` после рендера.

- [ ] **Step 1: зафиксировать ожидаемый текст секций из прототипа**

```bash
uv run python - <<'EOF'
import json, re
from bs4 import BeautifulSoup
s = BeautifulSoup(open('tests/fixtures/prototype.html', encoding='utf-8').read(), 'lxml')
ids = ['s-toc','s-intake','s-verdict','s-readers','s-blocks','s-flags','s-fixed','s-plan','s-source']
def norm(el): return re.sub(r'\s+', ' ', el.get_text(' ', strip=True).replace('\xa0',' ')).strip()
out = {i: norm(s.select_one('#'+i)) for i in ids}
out['hero'] = norm(s.select_one('.hero'))
out['header'] = norm(s.select_one('header'))
json.dump(out, open('tests/fixtures/expected_text.json','w', encoding='utf-8'), ensure_ascii=False, indent=1)
EOF
```

- [ ] **Step 2: failing UI-тест эквивалентности**

`tests/test_ui.py`:
```python
import json, re
import pytest
from playwright.sync_api import sync_playwright
from goodkp.render import render
from goodkp.schema import Report

IDS = ['header', 'hero', 's-toc', 's-intake', 's-verdict', 's-readers', 's-blocks', 's-flags', 's-fixed', 's-plan', 's-source']
SEL = {'header': 'header', 'hero': '.hero'}

def norm(s): return re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()

@pytest.fixture(scope="module")
def page_html(golden_path, tmp_path_factory):
    r = Report.model_validate(json.loads(golden_path.read_text(encoding="utf-8")))
    p = tmp_path_factory.mktemp("ui") / "report.html"
    p.write_text(render(r), encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def page(page_html):
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(page_html.as_uri())
        pg.wait_for_timeout(500)
        pg.errors = errors
        yield pg
        b.close()

@pytest.mark.parametrize("sec", IDS)
def test_section_text_matches_prototype(page, sec):
    expected = json.loads(open("tests/fixtures/expected_text.json", encoding="utf-8").read())[sec]
    sel = SEL.get(sec, "#" + sec)
    got = page.evaluate("s => document.querySelector(s).innerText", sel)
    assert norm(got) == norm(expected)

def test_no_page_errors(page):
    assert page.errors == []
```

Тест сравнивает `innerText`, поэтому скрытые элементы (`hidden`, `display:none`) в нем не участвуют. Прототип и шаблон должны совпасть по видимому тексту после reveal. Чтобы reveal не мешал, в тесте `reduced_motion="reduce"`, а JS шаблона при `prefers-reduced-motion` сразу добавляет класс `in` всем `.rv`, и чат с диктофоном показывают конечное состояние (это поведение уже есть в прототипе для reveal; для чата проверить блок `/* iMessage chat */`: при reduced motion все `.m` должны получать `show` сразу, если нет, добавить).

- [ ] **Step 3: run** → FAIL: страница все еще рендерит захардкоженный текст, но `innerText` header совпадет, а секции упадут после следующего шага. Сейчас цель: убедиться, что тест запускается и проходит на нетронутом шаблоне (он должен пройти полностью, это базовая линия). Expected: 12 passed.

- [ ] **Step 4: утилиты и обвязка `GK`**

Вставить сразу после `<script type="application/json" id="data"></script>`:

```html
<script>
window.GK = (function(){
  var PREP = /(^|[\s(«„])((?:[а-яa-z]{1,3}|же|бы|ли|или|как|для|при|под|над|про|без|через|из-за|из-под))\s+/gi;
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  /* nbsp после коротких слов и предлогов, перед же/бы/ли, между числом и единицей, в разрядах */
  function nb(s){
    s = esc(s);
    s = s.replace(PREP, function(m, a, w){ return a + w + ' '; });
    s = s.replace(/\s+(же|бы|ли|б|ж)(?=[\s,.!?»])/g, ' $1');
    s = s.replace(/(\d)\s+(?=(?:млн|тыс|руб|₽|%|ч|мин|сек|недел|дн|мес|МБ|КБ|стр)\b)/g, '$1 ');
    s = s.replace(/(\d)\s(\d{3})(?!\d)/g, '$1 $2');
    return s;
  }
  /* [плейсхолдер] -> <span class="ph">[плейсхолдер]</span> */
  function ph(s){ return nb(s).replace(/\[([^\]]+)\]/g, '<span class="ph">[$1]</span>'); }
  function h(tag, attrs, inner){
    var a = '';
    for (var k in attrs || {}) if (attrs[k] != null && attrs[k] !== false) a += ' ' + k + '="' + esc(attrs[k]) + '"';
    return '<' + tag + a + '>' + (inner == null ? '' : inner) + '</' + tag + '>';
  }
  function fmtDate(iso, opts){ return new Intl.DateTimeFormat('ru-RU', Object.assign({ timeZone: 'Europe/Moscow' }, opts)).format(new Date(iso)); }
  function ddmmyyyy(iso){ return fmtDate(iso, { day: '2-digit', month: '2-digit', year: 'numeric' }); }
  return { esc: esc, nb: nb, ph: ph, h: h, fmtDate: fmtDate, ddmmyyyy: ddmmyyyy, renderers: {} };
})();
</script>
```

Проверка nb в консоли браузера: `GK.nb('Пришло КП от Пиксель Лаб. Посмотрите же, 2,4 млн и 3 500')` → nbsp после «от», перед «же», между «2,4» и «млн», между «3» и «500».

- [ ] **Step 5: рендеры секций**

Следующий `<script>` после утилит. Каждая функция получает `data` и возвращает HTML-строку, которую обвязка вставляет в контейнер по id. Разметка копируется из прототипа один в один (классы, id, `data-*`, svg-иконки), меняется только текст. Ниже полный список контейнеров и точная разметка для трех секций; остальные реализуются по прототипу теми же правилами.

Контейнеры в шаблоне (существующие теги остаются, их содержимое очищается):

| id контейнера | что рендерит | источник данных |
|---|---|---|
| `header .meta` | 3 строки | meta |
| `.hero-t` | h1, p, кнопка replay | meta.title, blocks (счетчики), статичная кнопка |
| `#chat` | шапка и `.chat-b` | chat, readers (аватары: инициалы отправителей `them` в порядке появления) |
| `#s-toc .note` | заметка | статичный список из 9 пунктов, дата из meta.run_date |
| `.intake` | 6 строк | intake |
| `#memo` | диктофон | verdict, meta.run_date |
| `#readers` | сегменты и панели | readers |
| `.blocks` | 6 статей | blocks |
| `#nstack` | карточки + `#nhint` | flags |
| `.holds` | список | holds |
| `#docp` | почта + документ | fixed_page, meta, readers[1].name (Кому) |
| `#hour` | кольцо + `#plan` | plan |
| `#s-source details` | summary + `.kp` | meta, source |

Шаблонные строки, которые рендеры генерируют из данных (не из модели):

- hero `p`: «{crit} из шести опор провалены, {weak} шатаются, {ok} держит.» Числа словами: 0 «ни одна», 1 «одна», 2 «две», 3 «три», 4 «четыре», 5 «пять», 6 «шесть». Затем вторая фраза из прототипа заменяется на `readers[1].outcome` и `readers[0].outcome`, склеенные: «Тому, кто продвигает проект внутри клиента: {champion.outcome} Тому, кто платит: {decider.outcome}». Ожидаемый текст в `expected_text.json` для hero нужно после этого пересобрать (Step 1 выполняется повторно после того, как рендеры готовы, и diff руками проверяется на осмысленность: единственная допустимая разница в hero это этот абзац).
- Подпись строки блока по state: `ok` «Держит», `weak` «Шатается», `crit` «Отвалился».
- `#timer span` начальный текст: «{decider.name} читает файл».
- `.memo-dur` и `#memoLeft`: секунды = `Math.max(8, Math.round(words / 2.6))`, формат `m:ss`.
- Дата в заметке и диктофоне: `fmtDate(run_date, {day:'numeric', month:'long', year:'numeric'}) + ', ' + fmtDate(run_date, {hour:'2-digit', minute:'2-digit'})`, в заметке плюс « МСК». Экран блокировки: `#lockDate` день недели и дата, `#lockTime` часы.
- Кольцо таймера: сегменты из `plan[].minutes`: длина окружности `C = 741.42`, дуга `C * min / total` минус зазор `8`, поворот `-90 + 360 * acc / total + 1.7`. Шаг по цвету не отличается (сегменты `stroke: var(--faint)`), это уже в CSS.

Полная разметка intake:
```js
GK.renderers.intake = function(d){
  return d.intake.map(function(r){
    return '<div><span class="k">' + GK.nb(r.k) + '</span><span class="v">' + GK.nb(r.v) + '</span></div>';
  }).join('');
};
```

Полная разметка одного блока (обратить внимание: `hidden` у `.was` и `translateX(100%)` у thumb, как в прототипе):
```js
GK.renderers.blocks = function(d){
  var LABEL = { ok: 'Держит', weak: 'Шатается', crit: 'Отвалился' };
  return d.blocks.map(function(b){
    var src = b.quote_src ? '<a class="findsrc" href="#' + b.quote_src + '" data-src="' + b.quote_src + '">Найти в исходном КП</a>' : '';
    return '<article class="block ' + b.state + ' rv">' +
      '<button class="brow" type="button" aria-expanded="false"><span class="i">' + b.id + '</span>' +
      '<span class="bt"><b>' + GK.nb(b.title) + '</b><span>' + GK.nb(b.summary) + '</span></span>' +
      '<span class="st ' + b.state + '">' + LABEL[b.state] + '</span><span class="chev" aria-hidden="true"></span></button>' +
      '<div class="bbody"><div><div class="bx">' +
        '<div class="bl"><div class="kpq"><span class="kq">Из КП</span><p>' + GK.nb(b.quote) + '</p>' + src + '</div>' +
        '<p class="bwhy">' + GK.nb(b.why) + '</p>' +
        '<p class="bdo"><b>Что делать.</b> ' + GK.nb(b.do) + '</p></div>' +
        '<div class="br"><div class="ba">' +
          '<div class="segctl two" role="tablist" aria-label="Было или стало"><span class="thumb" aria-hidden="true" style="transform:translateX(100%)"></span>' +
          '<button type="button" role="tab" aria-selected="false" data-v="was">Было</button><button type="button" role="tab" aria-selected="true" data-v="now">Стало</button></div>' +
          '<div class="ba-text"><p class="was" hidden>' + GK.nb(b.was) + '</p><p class="now">' + GK.ph(b.now) + '</p></div>' +
        '</div></div>' +
      '</div></div></div></article>';
  }).join('');
};
```
Перед копированием сверить с прототипом (`sed -n '677,690p' tests/fixtures/prototype.html`): атрибуты кнопок сегмента и порядок `was/now` должны совпасть буквально.

Полная разметка чата (`.chat-h` и `.msgs` внутри `.chat-b`, `#typing` остается статичным в шаблоне после `.msgs`):
```js
GK.renderers.chat = function(d){
  var names = [];
  d.chat.forEach(function(m){ if (m.side === 'them' && m.name && names.indexOf(m.name) < 0) names.push(m.name); });
  var head = '<div class="chat-h"><div class="chat-avs">' + names.map(function(n){ return '<span>' + GK.esc(n[0]) + '</span>'; }).join('') + '</div>' +
    '<div class="chat-t"><b>' + GK.nb(d.chat_title || ('КП от ' + d.meta.vendor)) + '</b><span>' + GK.esc(names.join(', ')) + '</span></div>' +
    '<div class="chat-timer" id="timer"><span>' + GK.esc(d.readers[0].name) + ' читает файл</span><b>0:00</b></div></div>';
  var msgs = d.chat.map(function(m, i){
    var attrs = { 'class': 'm ' + m.side, 'data-wait': m.side === 'me' ? 300 + Math.min(m.text.length * 30, 3000) : 500 + Math.min(m.text.length * 12, 1200) };
    if (m.side === 'them') { attrs['data-name'] = m.name; attrs['data-type'] = 800 + Math.min(m.text.length * 20, 1600); }
    if (m.timer) attrs['data-timer'] = m.timer;
    var inner = m.file
      ? '<div class="file"><span class="ico">' + GK.esc(m.file.name.split('.').pop().toUpperCase()) + '</span><span><b>' + GK.nb(m.file.name) + '</b><i>' + GK.nb(m.file.size) + '</i></span></div>'
      : '';
    if (m.text) inner += '<div class="b">' + GK.nb(m.text) + '</div>';
    if (m.status) inner += '<div class="st">' + m.status + '</div>';
    return GK.h('div', attrs, inner);
  }).join('');
  return { head: head, msgs: msgs };
};
```
Обвязка вставляет `head` перед `.chat-b`, а `msgs` в `.msgs`. Заголовок чата в golden: «Сайт, КП от Пиксель Лаб». В схему поле `chat_title` не добавляется: заголовок собирается как `'{meta.project_short}, КП от {vendor}'`… чтобы не плодить поля, принять правило: заголовок чата = `'КП от ' + vendor`, и обновить golden-ожидание для hero в `expected_text.json` (это второе допустимое расхождение в hero). Прототип в `tests/fixtures/prototype.html` при этом не меняется.

Остальные рендеры (`header`, `hero`, `toc`, `memo`, `readers`, `flags`, `holds`, `doc`, `plan`, `source`) пишутся по тому же образцу: открыть соответствующий фрагмент прототипа, перенести разметку в строку, подставить данные через `GK.nb`/`GK.ph`/`GK.esc`. Для `memo` слова вердикта оборачиваются в `<span>` по одному, как в прототипе (`#memoQ`). Для `readers` порядок панелей и `style="--i:N"` в `.msg` сохраняются. Для `source` элементы с `## ` в тексте становятся `<h3 id="src-N">`, остальные `<p id="src-N">`; первая строка `.fine` про вымышленные компании остается статичной в шаблоне.

- [ ] **Step 6: обвязка запуска**

В конце скрипта рендеров:
```js
GK.render = function(d){
  var R = GK.renderers, q = function(s){ return document.querySelector(s); };
  q('header .meta').innerHTML = R.header(d);
  q('.hero-t').innerHTML = R.hero(d);
  var c = R.chat(d); q('#chat').insertAdjacentHTML('afterbegin', c.head); q('#chat .msgs').innerHTML = c.msgs;
  q('#s-toc .note').innerHTML = R.toc(d);
  q('.intake').innerHTML = R.intake(d);
  q('#memo').innerHTML = R.memo(d);
  q('#readers').innerHTML = R.readers(d);
  q('.blocks').innerHTML = R.blocks(d);
  q('#nstack').innerHTML = R.flags(d);
  q('.holds').innerHTML = R.holds(d);
  q('#docp').innerHTML = R.doc(d);
  q('#hour').innerHTML = R.plan(d);
  q('#s-source details').innerHTML = R.source(d);
  document.title = 'Good КП: ' + d.meta.client.replace(/^ООО\s+/, '').replace(/[«»]/g, '');
};
GK.boot = function(){
  var el = document.getElementById('data'), txt = (el && el.textContent || '').trim();
  if (!txt) { document.body.classList.add('nodata'); return false; }
  var d;
  try { d = JSON.parse(txt); } catch (e) { document.body.classList.add('nodata'); console.error('Good КП: JSON не разобран', e); return false; }
  if (d.refusal) { document.body.classList.add('nodata'); console.error('Good КП: отказ', d.refusal.reason); return false; }
  GK.render(d);
  return true;
};
```

Существующий скрипт интерактивов оборачивается: его IIFE `(function(){ ... })()` становится `GK.init = function(){ ... }`, а в самом конце файла добавляется:
```html
<script>if (GK.boot()) GK.init();</script>
```
Состояние без данных: в `<main>` перед первой секцией добавить
```html
<div class="nodata-msg" hidden>Нет данных. Вставьте report.json в блок <code>#data</code> или откройте страницу через docs/index.html.</div>
```
и CSS `body.nodata main>section,body.nodata .hero,body.nodata header .meta{display:none}body.nodata .nodata-msg{display:block;padding:80px 28px;color:var(--ink2)}`.

- [ ] **Step 7: очистить статичные данные из разметки**

Удалить из шаблона содержимое контейнеров из таблицы Step 5 (оставить сами теги-контейнеры, статичные `h2`, `.lead`, `#typing`, `.fine`, разметку методики и подвала). Проверить, что в файле не осталось текста про СтройМаркет:
```bash
grep -c "СтройМаркет\|Пиксель Лаб\|Сергей\|Ольга\|Дмитрий" template/report.html
```
Expected: 0.

- [ ] **Step 8: run** `uv run pytest tests/test_ui.py -q` → 12 passed. Расхождения читать через diff двух строк; типовые причины: пропущенный nbsp в статичном тексте (в тесте nbsp нормализуется, так что это не причина), пропущенная статичная подпись (например «Из КП», «Что делать.»), лишний пробел перед знаком препинания из `get_text(' ')` в expected (тогда исправить нормализацию `norm` на `re.sub(r'\s+([,.!?»])', r'\1', ...)` с обеих сторон).

- [ ] **Step 9: глазами**

```bash
uv run python -c "import json; from goodkp.render import render; from goodkp.schema import Report; open('/tmp/gk.html','w').write(render(Report.model_validate(json.load(open('tests/golden/stroymarket/report.json')))))" && open /tmp/gk.html
```
Пройти все интерактивы: чат проигрывается, диктофон играет и перематывает, сегменты читателей, раскрытие блоков и было/стало, уведомления раскрываются, фонарик и камера, почта разворачивается, docx и PDF скачиваются, таймер стартует, методика листается, «Найти в исходном КП» подсвечивает абзац.

- [ ] **Step 10: Commit** `git add -A && git commit -m "Шаблон рендерит отчет из JSON, интерактивы без изменений"`

---

### Task 6: Только темная тема

**Files:**
- Modify: `template/report.html` (блок `<style>`)
- Test: `tests/test_template_static.py`

- [ ] **Step 1: failing test**

`tests/test_template_static.py`:
```python
import re

def test_dark_only(template_path):
    s = template_path.read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in s
    assert "data-theme" not in s
    assert re.search(r":root\s*\{[^}]*color-scheme:\s*dark", s)

def test_no_banned_glyphs_in_static_text(template_path):
    s = template_path.read_text(encoding="utf-8")
    body = s[s.index("<header"):]
    for g in ("—", "·", "ё", "Ё"):
        assert g not in body, g
```

- [ ] **Step 2: run** → FAIL на `prefers-color-scheme`.

- [ ] **Step 3: правка стилей**

Найти в `<style>` три блока токенов: `:root{...}` (светлые), `@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){...}}` и `:root[data-theme="dark"]{...}`. Взять значения токенов из темного блока, записать их в `:root{...}` вместе с `color-scheme: dark`, оба темных блока удалить. Затем найти все остальные `@media (prefers-color-scheme: dark)` и `[data-theme=` по файлу (`grep -n`), в каждом случае оставить темную ветку как основную. Документ в почте (`.doc-p` и вложенные) и печать (`@media print`) остаются белыми: проверить, что их цвета заданы явно, а не через токены.

- [ ] **Step 4: run** `uv run pytest tests/test_template_static.py tests/test_ui.py -q` → passed. Открыть `/tmp/gk.html` как в Task 5 Step 9, сверить: фон темный при любой системной теме (переключить в системных настройках), письмо и docx белые.

- [ ] **Step 5: Commit** `git commit -am "Только темная тема"`

---

### Task 7: Активный раздел в меню

**Files:**
- Modify: `template/report.html` (CSS `.pillnav`, JS блок `/* pill nav */`)
- Test: `tests/test_ui.py` (добавить)

- [ ] **Step 1: failing test**

```python
def test_nav_highlights_current_section(page):
    page.evaluate("document.querySelector('#s-fixed').scrollIntoView()")
    page.wait_for_timeout(400)
    active = page.evaluate("[...document.querySelectorAll('#nav a')].filter(a => a.classList.contains('cur')).map(a => a.getAttribute('href'))")
    assert active == ["#s-fixed"]
```

- [ ] **Step 2: run** → FAIL (`active == []`).

- [ ] **Step 3: реализация**

CSS, к существующим правилам `.pillnav a`:
```css
.pillnav a{transition:background .25s var(--ease),color .25s var(--ease)}
.pillnav a.cur{background:var(--ink);color:var(--bg)}
.pillnav{scroll-snap-type:x proximity}
@media (prefers-reduced-motion: reduce){.pillnav a{transition:none}}
```
Токены `--ink` и `--bg` есть в `:root` (проверить имена: `grep -o "\-\-[a-z0-9]*:" template/report.html | sort -u`). Если пилюли уже имеют фон, активная получает инверсию: светлый фон, темный текст.

JS: в блоке `/* pill nav */` заменить наблюдение по `offsetTop` на IntersectionObserver:
```js
var cur = -1;
function setCur(i){
  if (i === cur) return; cur = i;
  links.forEach(function(a, k){ a.classList.toggle('cur', k === i); });
  var a = links[i]; if (a && a.scrollIntoView) a.scrollIntoView({ block: 'nearest', inline: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){ if (e.isIntersecting) setCur(secs.indexOf(e.target)); });
}, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });
secs.forEach(function(s){ if (s) io.observe(s); });
```
Показ/скрытие меню после hero (`nav.classList.toggle('show', …)`) оставить как есть. Секции без пункта меню (toc, intake, flags, source) не наблюдаются: подсветка держится на последнем пройденном пункте, что и ожидается от scrollspy.

- [ ] **Step 4: run** `uv run pytest tests/test_ui.py -q` → passed. Глазами на узком окне (400px): активная пилюля подъезжает в видимую область.

- [ ] **Step 5: Commit** `git commit -am "Меню подсвечивает текущий раздел"`

---

### Task 8: Скриншоты и проверки интерактива

**Files:**
- Modify: `tests/test_ui.py`
- Create: `tests/screenshots/baseline/full.png`

- [ ] **Step 1: тесты**

```python
def test_was_now_toggle(page):
    page.click("#s-blocks .block:first-child .brow")
    page.wait_for_timeout(300)
    blk = page.locator("#s-blocks .block:first-child")
    assert blk.locator(".now").is_visible() and not blk.locator(".was").is_visible()
    blk.locator('[data-v="was"]').click()
    page.wait_for_timeout(300)
    assert blk.locator(".was").is_visible() and not blk.locator(".now").is_visible()

def test_chat_completes_under_reduced_motion(page):
    shown = page.evaluate("document.querySelectorAll('#chat .m.show').length")
    total = page.evaluate("document.querySelectorAll('#chat .m').length")
    assert shown == total

def test_all_sections_present(page):
    for sec in ["s-toc", "s-intake", "s-verdict", "s-readers", "s-blocks", "s-flags", "s-fixed", "s-plan", "s-method", "s-source"]:
        assert page.locator("#" + sec).count() == 1

def test_screenshot_matches_baseline(page, tmp_path):
    from pathlib import Path
    from PIL import Image, ImageChops
    base = Path("tests/screenshots/baseline/full.png")
    actual = Path("tests/screenshots/actual"); actual.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(actual / "full.png"), full_page=True)
    if not base.exists():
        import shutil; shutil.copy(actual / "full.png", base); return
    a, b = Image.open(actual / "full.png").convert("RGB"), Image.open(base).convert("RGB")
    assert a.size == b.size, f"размер {a.size} против {b.size}"
    diff = ImageChops.difference(a, b).getbbox()
    if diff:
        hist = ImageChops.difference(a, b).convert("L").histogram()
        changed = sum(hist[8:]) / (a.size[0] * a.size[1])
        assert changed < 0.01, f"изменилось {changed:.1%} пикселей"
```
Класс `show` у сообщений чата: сверить с прототипом (`grep -n "classList.add('show')\|classList.add(\"show\")" tests/fixtures/prototype.html`), если класс другой, подставить его. Добавить `pillow` в dev-группу: `uv add --group dev pillow`.

- [ ] **Step 2: run** дважды: первый создает baseline, второй проходит. Baseline коммитится.

- [ ] **Step 3: Commit** `git add -A && git commit -m "UI-тесты: интерактив и скриншот-эталон"`

---

## Проверка плана по спеке

- Раздел 2 (рендер в HTML, темная тема, scrollspy, автор из рубрики): Tasks 5, 6, 7; автор из рубрики переносится в фазу 2 вместе с rubric.yaml, сейчас статичный текст в шаблоне уже содержит нужную должность.
- Раздел 5 (контракт): Task 2, golden в Task 3.
- Раздел 7 (шаблон и рендер): Tasks 4, 5; `docs/index.html` в фазе 2.
- Раздел 12 (тесты): schema, render, ui сделаны; typo, rubric, live_run в фазе 2.
- Разделы 6, 8, 9, 10, 11: фаза 2 (rubric, prompt, model, typo, intake, bot).
