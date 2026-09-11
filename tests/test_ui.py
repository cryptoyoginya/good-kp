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


def test_screenshot_matches_baseline(request, page, page_html):
    """Скриншот снимается на свежей странице того же браузера, а не на модульной
    `page`: test_was_now_toggle кликает и мутирует общую страницу, а порядок
    тестов в файле не должен влиять на результат сравнения со скриншотом.
    """
    from PIL import Image, ImageChops
    root = request.config.rootpath
    base = root / "tests" / "screenshots" / "baseline" / "full.png"
    actual = root / "tests" / "screenshots" / "actual"
    actual.mkdir(parents=True, exist_ok=True)
    shot = page.context.browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    shot.goto(page_html.as_uri())
    shot.wait_for_timeout(500)
    shot.screenshot(path=str(actual / "full.png"), full_page=True)
    shot.close()
    if request.config.getoption("--update-baseline"):
        import shutil
        base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(actual / "full.png", base)
        return
    if not base.exists():
        pytest.fail("нет эталона, запустите с --update-baseline")
    a, b = Image.open(actual / "full.png").convert("RGB"), Image.open(base).convert("RGB")
    assert a.size == b.size, f"размер {a.size} против {b.size}"
    diff = ImageChops.difference(a, b).getbbox()
    if diff:
        hist = ImageChops.difference(a, b).convert("L").histogram()
        changed = sum(hist[8:]) / (a.size[0] * a.size[1])
        assert changed < 0.01, f"изменилось {changed:.1%} пикселей"


@pytest.fixture(scope="module")
def golden_data(request):
    p = request.config.rootpath / "tests" / "golden" / "stroymarket" / "report.json"
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def edge_page(page, tmp_path_factory):
    """Второй набор данных: все шесть опор прошли, нижние границы контракта."""
    from tests.edge_data import edge_report
    p = tmp_path_factory.mktemp("edge") / "report.html"
    p.write_text(render(Report.model_validate(edge_report())), encoding="utf-8")
    pg = page.context.browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(p.as_uri())
    pg.wait_for_timeout(500)
    pg.errors = errors
    yield pg
    pg.close()


def test_edge_dataset_renders_without_errors(edge_page):
    assert edge_page.errors == []
    assert not edge_page.evaluate("() => document.body.classList.contains('nodata')")
    for sec in ["s-toc", "s-intake", "s-verdict", "s-readers", "s-blocks", "s-flags",
                "s-fixed", "s-plan", "s-method", "s-source"]:
        assert edge_page.locator("#" + sec).count() == 1


def test_hero_lead_agrees_with_zero_counts(edge_page):
    got = edge_page.evaluate("() => document.querySelector('.hero-t p').innerText")
    assert norm(got).startswith(
        "Ни одна из шести опор не провалена, ни одна не шатается, шесть держат.")


def test_missing_top_level_key_named_in_nodata(page, golden_data, tmp_path):
    """Без одного из одиннадцати полей страница уходит в nodata и называет поле."""
    from goodkp.render import inject, load_template, wrap
    d = dict(golden_data)
    d.pop("plan")
    p = tmp_path / "no_plan.html"
    p.write_text(wrap(inject(load_template(), d)), encoding="utf-8")
    pg = page.context.browser.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(p.as_uri())
    pg.wait_for_timeout(300)
    nodata = pg.evaluate("() => document.body.classList.contains('nodata')")
    msg = pg.evaluate("() => document.querySelector('.nodata-msg').innerText")
    pg.close()
    assert nodata
    assert "plan" in msg
    assert errors == []


def test_dl_note_host_present(page):
    assert page.evaluate("() => !!document.getElementById('dlNote')")


def test_mount_twice_does_not_duplicate(page, page_html):
    """GK.mount повторно рендерит и переинициализирует, ничего не удваивая."""
    pg = page.context.browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(page_html.as_uri())
    pg.wait_for_timeout(400)
    bars = pg.evaluate("() => document.getElementById('wave').children.length")
    heads = pg.evaluate("() => document.querySelectorAll('.chat-h').length")
    pg.evaluate("() => { GK.mount(GK.data); GK.mount(GK.data); }")
    pg.wait_for_timeout(400)
    got = pg.evaluate("() => ({bars: document.getElementById('wave').children.length,"
                      " heads: document.querySelectorAll('.chat-h').length,"
                      " blocks: document.querySelectorAll('.block').length,"
                      " cards: document.querySelectorAll('#nstack .ncard').length})")
    pg.close()
    assert errors == []
    assert heads == 1 and got["heads"] == 1
    assert got["bars"] == bars
    assert got["blocks"] == 6 and got["cards"] == 6


# --- панель вставки JSON ---

@pytest.fixture
def fresh(page):
    """Свежая страница в том же браузере: вложенный sync_playwright падает."""
    made = []

    def open_uri(uri):
        pg = page.context.browser.new_page(viewport={"width": 1280, "height": 900},
                                           reduced_motion="reduce")
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(uri)
        pg.wait_for_timeout(400)
        pg.errors = errors
        made.append(pg)
        return pg

    yield open_uri
    for pg in made:
        pg.close()


@pytest.fixture(scope="module")
def goodkp_uri(request):
    return (request.config.rootpath / "goodkp.html").as_uri()


@pytest.fixture(scope="module")
def golden_text(request):
    p = request.config.rootpath / "tests" / "golden" / "stroymarket" / "report.json"
    return p.read_text(encoding="utf-8")


def build(pg, text):
    """Вставить текст в панель и нажать «Собрать отчет»."""
    pg.fill("#pasteBox", text)
    pg.click("#pasteRun")
    pg.wait_for_timeout(600)


def test_goodkp_opens_with_paste_panel(fresh, goodkp_uri):
    pg = fresh(goodkp_uri)
    assert pg.evaluate("() => document.body.classList.contains('nodata')")
    assert pg.locator("#pasteBox").is_visible()
    assert pg.locator("#pasteRun").is_visible()
    assert pg.locator("#pasteFile").is_visible()
    assert not pg.locator("#saveBtn").is_visible()
    assert pg.errors == []


def test_paste_builds_report(fresh, goodkp_uri, golden_text, golden_data):
    pg = fresh(goodkp_uri)
    build(pg, golden_text)
    assert not pg.evaluate("() => document.body.classList.contains('nodata')")
    for sec in ["s-toc", "s-intake", "s-verdict", "s-readers", "s-blocks", "s-flags",
                "s-fixed", "s-plan", "s-method", "s-source"]:
        assert pg.locator("#" + sec).count() == 1
    assert norm(pg.evaluate("() => document.querySelector('.hero h1').innerText")) == \
        norm(golden_data["meta"]["title"])
    assert pg.locator("#saveBtn").is_visible()
    assert pg.errors == []


def test_serialized_file_renders_on_its_own(fresh, goodkp_uri, golden_text, tmp_path):
    pg = fresh(goodkp_uri)
    build(pg, golden_text)
    saved = tmp_path / "saved.html"
    saved.write_text(pg.evaluate("() => GK.serialize()"), encoding="utf-8")
    out = fresh(saved.as_uri())
    assert not out.evaluate("() => document.body.classList.contains('nodata')")
    assert out.locator("#s-blocks .block").count() == 6
    assert not out.locator("#saveBtn").is_visible()
    assert out.evaluate("() => document.querySelector('#pasteBox').value") == ""
    assert out.errors == []


def test_em_dash_reported_yo_fixed(fresh, goodkp_uri, golden_data):
    d = json.loads(json.dumps(golden_data))
    d["verdict"]["text"] = "Всё не так. " + d["verdict"]["text"]
    d["blocks"][0]["why"] = "Срок — выдуман. " + d["blocks"][0]["why"]
    pg = fresh(goodkp_uri)
    build(pg, json.dumps(d, ensure_ascii=False))
    err = pg.evaluate("() => document.querySelector('#pasteErr').innerText")
    assert "тире" in err
    assert "blocks[0].why" in err
    assert pg.evaluate("() => document.body.classList.contains('nodata')")

    d["blocks"][0]["why"] = d["blocks"][0]["why"].replace("—", "взят с потолка,")
    build(pg, json.dumps(d, ensure_ascii=False))
    assert not pg.evaluate("() => document.body.classList.contains('nodata')")
    got = pg.evaluate("() => document.querySelector('#memo').innerText")
    assert "ё" not in got
    assert "Все" in got
    assert pg.errors == []


def test_refusal_named_in_panel(fresh, goodkp_uri):
    pg = fresh(goodkp_uri)
    build(pg, json.dumps({"refusal": {"reason": "не КП", "hint": "пришлите документ"}},
                         ensure_ascii=False))
    err = pg.evaluate("() => document.querySelector('#pasteErr').innerText")
    assert "не КП" in err
    assert "пришлите документ" in err
    assert pg.evaluate("() => document.body.classList.contains('nodata')")
    assert pg.errors == []


def test_broken_json_named_in_panel(fresh, goodkp_uri):
    pg = fresh(goodkp_uri)
    build(pg, "{не json")
    err = pg.evaluate("() => document.querySelector('#pasteErr').innerText")
    assert "JSON не разобран" in err
    assert pg.evaluate("() => document.body.classList.contains('nodata')")
    assert pg.errors == []


def test_serialized_file_starts_unrevealed(page_html, page):
    """Сохраненный файл не должен уносить с собой состояние прокрутки."""
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    pg = page.context.browser.new_page(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    pg.goto((root / "goodkp.html").as_uri()); pg.wait_for_timeout(300)
    pg.fill("#pasteBox", (root / "tests/golden/stroymarket/report.json").read_text(encoding="utf-8"))
    pg.click("#pasteRun"); pg.wait_for_timeout(600)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(600)
    assert pg.evaluate("document.querySelectorAll('.rv.in').length") > 0
    html = pg.evaluate("GK.serialize()")
    assert 'class="' not in html or " rv in" not in html
    assert html.startswith("<!doctype html>")
    pg.close()
