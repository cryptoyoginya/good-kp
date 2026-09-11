import json

from goodkp.render import render
from goodkp.schema import Report

from tests.conftest import ROOT


def test_example_matches_render(golden_path):
    """examples/stroymarket.html это ровно render(golden), без ручных правок."""
    want = render(Report.model_validate(json.loads(golden_path.read_text(encoding="utf-8"))))
    got = (ROOT / "examples" / "stroymarket.html").read_text(encoding="utf-8")
    assert got == want, "пример устарел, соберите: uv run python scripts/build_example.py"


def test_goodkp_html_matches_build():
    """goodkp.html в корне это ровно render_empty(), без ручных правок."""
    from goodkp.render import render_empty

    got = (ROOT / "goodkp.html").read_text(encoding="utf-8")
    assert got == render_empty(), "каркас устарел, соберите: uv run python scripts/build_goodkp.py"
