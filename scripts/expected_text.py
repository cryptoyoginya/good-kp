"""Прототип -> ожидаемый текст секций. Одноразовый, но воспроизводимый.

Текст берется из прототипа, скрытые элементы выброшены: тест сравнивает
innerText, а в него они не попадают. Два места рендер меняет сознательно,
оба в hero, и они пересобираются из golden.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tests/fixtures/prototype.html"
GOLDEN = ROOT / "tests/golden/stroymarket/report.json"
OUT = ROOT / "tests/fixtures/expected_text.json"

IDS = ["s-toc", "s-intake", "s-verdict", "s-readers", "s-blocks",
       "s-flags", "s-fixed", "s-plan", "s-source"]

# лид собирается из исходов читателей, заголовок чата из имени подрядчика
LEAD_WAS = ("Тому, кто продвигает проект внутри клиента, нечем его защитить, "
            "а тому, кто платит, не за что зацепиться на первых двух страницах.")
TITLE_WAS = "Сайт, КП от {vendor}"

# шапка письма: счетчик писем выдуман, дата и время идут из run_date
CNT_WAS, CNT_NOW = "1 из 3", "Черновик"
MAILDATE_WAS = "21 авг. 2026 г., 10:12"
# сокращения месяцев как у Intl ru-RU с month: 'short'
MONTHS = ("янв.", "февр.", "мар.", "апр.", "мая", "июн.",
          "июл.", "авг.", "сент.", "окт.", "нояб.", "дек.")


def mail_date(iso: str) -> str:
    """«7 сент. 2026 г., 14:24» из run_date, как это выводит Intl в шаблоне."""
    dt = datetime.fromisoformat(iso).astimezone(ZoneInfo("Europe/Moscow"))
    return "%d %s %d г., %02d:%02d" % (dt.day, MONTHS[dt.month - 1], dt.year, dt.hour, dt.minute)


def norm(el) -> str:
    t = el.get_text(" ", strip=True).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def main() -> None:
    # html.parser, а не lxml: у .bbody в прототипе не хватает </div>,
    # и lxml вкладывает следующие секции внутрь s-blocks
    soup = BeautifulSoup(SRC.read_text(encoding="utf-8"), "html.parser")
    for el in soup.select("[hidden]"):
        el.decompose()
    out = {i: norm(soup.select_one("#" + i)) for i in IDS}
    out["hero"] = norm(soup.select_one(".hero"))
    out["header"] = norm(soup.select_one("header"))

    d = json.loads(GOLDEN.read_text(encoding="utf-8"))
    lead = ("Тому, кто продвигает проект внутри клиента: %s Тому, кто платит: %s"
            % (d["readers"][1]["outcome"], d["readers"][0]["outcome"]))
    vendor = d["meta"]["vendor"]
    hero = out["hero"]
    assert LEAD_WAS in hero and TITLE_WAS.format(vendor=vendor) in hero
    out["hero"] = hero.replace(LEAD_WAS, lead).replace(
        TITLE_WAS.format(vendor=vendor), "КП от " + vendor)

    fixed = out["s-fixed"]
    assert CNT_WAS in fixed and MAILDATE_WAS in fixed
    out["s-fixed"] = fixed.replace(CNT_WAS, CNT_NOW).replace(
        MAILDATE_WAS, mail_date(d["meta"]["run_date"]))

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("ok:", OUT)


if __name__ == "__main__":
    main()
