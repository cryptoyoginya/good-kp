import json

from goodkp.render import render
from goodkp.schema import Report

from tests.conftest import ROOT


def test_example_matches_render(golden_path):
    """examples/stroymarket.html это ровно render(golden), без ручных правок."""
    want = render(Report.model_validate(json.loads(golden_path.read_text(encoding="utf-8"))))
    got = (ROOT / "examples" / "stroymarket.html").read_text(encoding="utf-8")
    assert got == want, "пример устарел, соберите: uv run python scripts/build_example.py"
