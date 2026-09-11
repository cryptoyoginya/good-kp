"""Файл-загрузчик: маленький HTML с данными внутри, который при открытии
подтягивает шаблон из репозитория и собирает отчет. Его отдает модель в чате."""
from __future__ import annotations

import json

TEMPLATE_URL = "https://raw.githubusercontent.com/cryptoyoginya/good-kp/main/goodkp.html"

HEAD = (
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<meta name="color-scheme" content="dark"><title>Good КП</title></head>'
    '<body style="margin:0;background:#000;color:#8e8e93;font:15px -apple-system,BlinkMacSystemFont,sans-serif;padding:48px 28px">'
    'Собираю отчет. Нужна сеть, шаблон подтягивается из репозитория.\n'
    '<script type="application/json" id="data">\n'
)

TAIL = (
    '\n</script>\n<script>\n'
    "fetch('" + TEMPLATE_URL + "').then(function(r){ return r.text(); }).then(function(t){\n"
    "  var d = document.getElementById('data').textContent.replace(/<\\//g, '<\\\\/');\n"
    "  var h = t.replace('<html lang=\"ru\">', '<html lang=\"ru\" data-loader>')\n"
    "           .replace('id=\"data\"><\\/script>', 'id=\"data\">' + d + '<\\/script>');\n"
    "  document.open(); document.write(h); document.close();\n"
    "}).catch(function(){\n"
    "  document.body.textContent = 'Нет сети. Откройте goodkp.html из репозитория и вставьте данные из этого файла.';\n"
    "});\n"
    '</script></body></html>\n'
)


def build_loader(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return HEAD + payload + TAIL


def loader_shell() -> str:
    """Оболочка без данных, как ее должна воспроизвести модель: JSON вставляется между HEAD и TAIL."""
    return HEAD + "…JSON…" + TAIL
