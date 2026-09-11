"""Каркас без данных -> goodkp.html в корне. Один файл, который скачивают и открывают."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from goodkp.render import render_empty  # noqa: E402

OUT = ROOT / "goodkp.html"


def build() -> str:
    return render_empty()


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(OUT)
