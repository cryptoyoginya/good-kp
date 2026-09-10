"""Прототип -> ожидаемый текст секций. Одноразовый, но воспроизводимый.

Текст берется из прототипа, скрытые элементы выброшены: тест сравнивает
innerText, а в него они не попадают. Два места рендер меняет сознательно,
оба в hero, и они пересобираются из golden.
"""
import json
import re
from pathlib import Path

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

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("ok:", OUT)


if __name__ == "__main__":
    main()
