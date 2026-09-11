"""report.json -> файл-загрузчик, который сам подтянет шаблон и соберет отчет.

  uv run python scripts/build_loader.py report.json out.html
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from goodkp.loader import build_loader  # noqa: E402
from goodkp.schema import Report  # noqa: E402

src = Path(sys.argv[1])
data = json.loads(src.read_text(encoding="utf-8"))
Report.model_validate(data)
out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".loader.html")
out.write_text(build_loader(data), encoding="utf-8")
print(out)
