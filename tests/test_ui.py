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


def test_nb_binds_number_and_unit(page):
    """GK.nb ставит nbsp между числом и единицей и после снятия \\b в юникоде."""
    result = page.evaluate("() => GK.nb('2,4 млн и 16 недель, 3 500 руб')")
    assert '2,4\xa0млн' in result
    assert '16\xa0недель' in result
    assert '3\xa0500\xa0руб' in result
    text = page.evaluate("() => document.body.innerText")
    assert len(re.findall(r'\d\xa0(?:млн|недел|мин|МБ)', text)) >= 10


def test_nav_highlights_current_section(page):
    # instant, а не CSS scroll-behavior:smooth (html{scroll-behavior:smooth}) -
    # иначе прокрутка до дальней секции не успевает завершиться за 400ms
    page.evaluate("document.querySelector('#s-fixed').scrollIntoView({block: 'start', behavior: 'instant'})")
    page.wait_for_timeout(400)
    active = page.evaluate("[...document.querySelectorAll('#nav a')].filter(a => a.classList.contains('cur')).map(a => a.getAttribute('href'))")
    assert active == ["#s-fixed"]


def test_bad_date_falls_back_to_nodata(page, page_html, tmp_path):
    """Ошибка рендера (битая дата) не должна ронять страницу наполовину отрендеренной."""
    html = page_html.read_text(encoding="utf-8")
    target = '"run_date": "2026-09-07T14:24:00+03:00"'
    assert html.count(target) == 1
    bad_html = html.replace(target, '"run_date": "не дата"')
    p = tmp_path / "bad_date.html"
    p.write_text(bad_html, encoding="utf-8")
    # переиспользуем браузер модульной страницы: вложенный sync_playwright() внутри
    # уже работающего цикла событий падает с ошибкой asyncio
    pg = page.context.browser.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(p.as_uri())
    pg.wait_for_timeout(500)
    has_nodata = pg.evaluate("() => document.body.classList.contains('nodata')")
    pg.close()
    assert has_nodata
    assert errors == []


def test_was_now_toggle(page):
    page.click("#s-blocks .block:first-child .brow")
    page.wait_for_timeout(300)
    blk = page.locator("#s-blocks .block:first-child")
    assert blk.locator(".now").is_visible() and not blk.locator(".was").is_visible()
    blk.locator('[data-v="was"]').click()
    page.wait_for_timeout(300)
    assert blk.locator(".was").is_visible() and not blk.locator(".now").is_visible()


def test_chat_completes_under_reduced_motion(page):
    shown = page.evaluate("document.querySelectorAll('#chat .m.in:not([hidden])').length")
    total = page.evaluate("document.querySelectorAll('#chat .m').length")
    assert shown == total


def test_all_sections_present(page):
    for sec in ["s-toc", "s-intake", "s-verdict", "s-readers", "s-blocks", "s-flags",
                "s-fixed", "s-plan", "s-method", "s-source"]:
        assert page.locator("#" + sec).count() == 1


def test_screenshot_matches_baseline(page, page_html, tmp_path):
    """Скриншот снимается на свежей странице того же браузера, а не на модульной
    `page`: test_was_now_toggle кликает и мутирует общую страницу, а порядок
    тестов в файле не должен влиять на результат сравнения со скриншотом.
    """
    from pathlib import Path
    from PIL import Image, ImageChops
    base = Path("tests/screenshots/baseline/full.png")
    actual = Path("tests/screenshots/actual")
    actual.mkdir(parents=True, exist_ok=True)
    shot = page.context.browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    shot.goto(page_html.as_uri())
    shot.wait_for_timeout(500)
    shot.screenshot(path=str(actual / "full.png"), full_page=True)
    shot.close()
    if not base.exists():
        import shutil
        base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(actual / "full.png", base)
        return
    a, b = Image.open(actual / "full.png").convert("RGB"), Image.open(base).convert("RGB")
    assert a.size == b.size, f"размер {a.size} против {b.size}"
    diff = ImageChops.difference(a, b).getbbox()
    if diff:
        hist = ImageChops.difference(a, b).convert("L").histogram()
        changed = sum(hist[8:]) / (a.size[0] * a.size[1])
        assert changed < 0.01, f"изменилось {changed:.1%} пикселей"
