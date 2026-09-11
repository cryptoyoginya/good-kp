"""report.json -> готовый HTML. Терминальный путь для тех, у кого есть репозиторий.

    uv run python scripts/build_report.py report.json
    uv run python scripts/build_report.py report.json out.html
    pbpaste | uv run python scripts/build_report.py

Без второго аргумента имя файла берется из клиента, как у кнопки в браузере.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from goodkp.render import render  # noqa: E402
from goodkp.schema import Report  # noqa: E402


def client_short(client: str) -> str:
    return re.sub(r"^ООО\s+", "", client).replace("«", "").replace("»", "")


def build(text: str) -> tuple[str, str]:
    """Возвращает HTML и имя файла по умолчанию."""
    raw = json.loads(text)
    if raw.get("refusal"):
        r = raw["refusal"]
        raise SystemExit("Модель не стала делать прогон: "
                         f"{r.get('reason', 'причина не названа')}. {r.get('hint', '')}".strip())
    report = Report.model_validate(raw)
    return render(report), f"КП {client_short(report.meta.client)}, прогон.html"


def main(argv: list[str]) -> None:
    text = Path(argv[0]).read_text(encoding="utf-8") if argv else sys.stdin.read()
    html, name = build(text)
    out = Path(argv[1]) if len(argv) > 1 else ROOT / name
    out.write_text(html, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
