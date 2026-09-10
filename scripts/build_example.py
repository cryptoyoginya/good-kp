"""Golden report.json -> examples/stroymarket.html. Пример в репозитории всегда свежий."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from goodkp.render import render  # noqa: E402
from goodkp.schema import Report  # noqa: E402

GOLDEN = ROOT / "tests" / "golden" / "stroymarket" / "report.json"
OUT = ROOT / "examples" / "stroymarket.html"


def build() -> str:
    return render(Report.model_validate(json.loads(GOLDEN.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(OUT)
