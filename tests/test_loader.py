import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from goodkp.loader import TEMPLATE_URL, build_loader

ROOT = Path(__file__).resolve().parent.parent


def _golden():
    return json.loads((ROOT / "tests/golden/stroymarket/report.json").read_text(encoding="utf-8"))


def test_loader_embeds_data_and_escapes():
    d = _golden(); d["verdict"]["text"] = d["verdict"]["text"] + " </script><b>"
    html = build_loader(d)
    assert html.startswith("<!doctype html>") and TEMPLATE_URL in html
    body = html.split('id="data">', 1)[1].split("</script>", 1)[0]
    assert "</script>" not in body and "<\\/script>" in body


def test_loader_renders_report_with_template_served(tmp_path):
    loader = tmp_path / "loader.html"
    loader.write_text(build_loader(_golden()), encoding="utf-8")
    template = (ROOT / "goodkp.html").read_text(encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.route(TEMPLATE_URL, lambda route: route.fulfill(status=200, content_type="text/plain; charset=utf-8", body=template))
        pg.goto(loader.as_uri())
        pg.wait_for_selector("#s-blocks .block", timeout=10000)
        assert pg.locator("#s-blocks .block").count() == 6
        assert not pg.evaluate("document.body.classList.contains('nodata')")
        assert pg.evaluate("!document.getElementById('saveBtn').hidden")
        assert errors == []
        saved = pg.evaluate("GK.serialize()")
        assert "data-loader" not in saved.split("<head", 1)[0]
        b.close()


def test_loader_offline_shows_hint(tmp_path):
    loader = tmp_path / "loader.html"
    loader.write_text(build_loader(_golden()), encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.route(TEMPLATE_URL, lambda route: route.abort())
        pg.goto(loader.as_uri())
        pg.wait_for_timeout(500)
        assert "Нет сети" in pg.inner_text("body")
        b.close()
