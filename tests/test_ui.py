"""Эквивалентность: текст секций на golden JSON равен тексту прототипа."""
import json
import re

import pytest
from playwright.sync_api import sync_playwright

from goodkp.render import render
from goodkp.schema import Report

IDS = ['header', 'hero', 's-toc', 's-intake', 's-verdict', 's-readers',
       's-blocks', 's-flags', 's-fixed', 's-plan', 's-source']
SEL = {'header': 'header', 'hero': '.hero'}


def norm(s: str) -> str:
    """Пробелы схлопнуты, nbsp обычный, пробел перед знаком препинания убран.

    Ожидаемый текст снят из прототипа через get_text(' '), который вставляет
    пробел между элементами, поэтому «[имя] ,» и «[имя],» надо считать равными.
    """
    s = re.sub(r'\s+', ' ', s.replace('\xa0', ' ')).strip()
    return re.sub(r'\s+([,.!?:;»])', r'\1', s)


@pytest.fixture(scope="module")
def expected(request):
    p = request.config.rootpath / "tests" / "fixtures" / "expected_text.json"
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def page_html(request, tmp_path_factory):
    golden = request.config.rootpath / "tests" / "golden" / "stroymarket" / "report.json"
    r = Report.model_validate(json.loads(golden.read_text(encoding="utf-8")))
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
        # исходное КП лежит в закрытом details, его текст в innerText не попадает
        pg.evaluate("() => { var d = document.querySelector('#s-source details');"
                    " if (d) d.open = true; }")
        pg.wait_for_timeout(100)
        pg.errors = errors
        yield pg
        b.close()


@pytest.mark.parametrize("sec", IDS)
def test_section_text_matches_prototype(page, expected, sec):
    sel = SEL.get(sec, "#" + sec)
    got = page.evaluate("s => document.querySelector(s).innerText", sel)
    assert norm(got) == norm(expected[sec])


def test_no_page_errors(page):
    assert page.errors == []
