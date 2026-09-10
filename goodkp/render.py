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
        raise ValueError('в шаблоне нет блока #data (<script type="application/json" id="data">)')
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return DATA_RE.sub(lambda m: m.group(1) + payload + m.group(3), template, count=1)


def wrap(inner: str) -> str:
    """Режет шаблон по первому тегу <script>.

    Все до него (title и style) уходит в head, все от него и дальше в body.
    """
    cut = inner.find("<script")
    if cut < 0:
        cut = len(inner)
    head, body = inner[:cut], inner[cut:]
    return HEAD + head + RESET + "</head><body>" + body + "</body></html>"


def render(report: Report, template: str | None = None) -> str:
    data = report.model_dump(by_alias=True, exclude_none=True)
    return wrap(inject(template or load_template(), data))
