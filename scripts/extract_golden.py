"""Прототип -> golden report.json. Одноразовый, но воспроизводимый."""
import json, re, sys
from pathlib import Path
from bs4 import BeautifulSoup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from goodkp.schema import Report

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "tests/fixtures/prototype.html"
OUT = ROOT / "tests/golden/stroymarket/report.json"

def t(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True).replace("\xa0", " ")).strip() if node else ""

soup = BeautifulSoup(SRC.read_text(encoding="utf-8"), "lxml")
meta_b, meta_lines = soup.select_one("header .meta b"), [s for s in soup.select_one("header .meta").stripped_strings]
m = re.match(r"КП №(\S+) от (\S+)", t(meta_b))
vendor, client = re.match(r"«(.+?)» для (.+)", meta_lines[1].replace("\xa0", " ")).groups()
d, mo, y = m.group(2).split(".")

STEP = {"Сначала цена": "pre"}
def step_of(s):
    s = s.replace("\xa0", " ")
    return STEP.get(s) or s.split(".")[0]
def state_of(cls):
    return "drop" if "drop" in cls else "off" if "off" in cls else "ok"
def block_state_of(cls):
    # прототип использует классы crit/warn/good у .block (не crit/weak/ok, как в прозе брифа)
    return "crit" if "crit" in cls else "weak" if "warn" in cls else "ok"

def feed_item(li):
    """Шаг ленты. Бейдж «отвалился» лежит в данных: он в роде персоны."""
    item = {"step": step_of(t(li.select_one(".step"))), "text": t(li.p),
            "state": state_of(li.get("class", []))}
    if item["state"] == "drop":
        item["badge"] = t(li.select_one(".st"))
    return item

readers = []
for pane in soup.select("#readers .pane"):
    tiles = pane.select(".ptiles > div")
    readers.append({
        "name": t(pane.select_one(".pc h3")), "role": t(pane.select_one(".pc h3").find_next_sibling()),
        "kind": ["decider", "champion", "executor"][len(readers)],
        "matters": t(tiles[0].p), "reads": t(tiles[1].p), "outcome": t(tiles[2].p),
        "feed": [feed_item(li) for li in pane.select(".feed .msg")],
    })

chat = []
for mm in soup.select("#chat .m"):
    msg = {"side": "me" if "me" in mm["class"] else "them", "text": t(mm.select_one(".b"))}
    if mm.get("data-name"): msg["name"] = mm["data-name"]
    f = mm.select_one(".file")
    if f: msg["file"] = {"name": t(f.b), "size": t(f.i)}
    st = mm.select_one(".st")
    if st: msg["status"] = t(st)
    if mm.get("data-timer"): msg["timer"] = mm["data-timer"]
    chat.append(msg)

blocks = []
for b in soup.select(".block"):
    cls = b.get("class", [])
    fs = b.select_one(".findsrc")
    blocks.append({
        "id": int(t(b.select_one(".i"))), "title": t(b.select_one(".bt b")),
        "summary": t(b.select_one(".bt > span")),
        "state": block_state_of(cls),
        "quote": t(b.select_one(".kpq p")), "quote_src": fs["data-src"] if fs else None,
        "why": t(b.select_one(".bwhy")),
        "do": re.sub(r"^Что делать\.\s*", "", t(b.select_one(".bdo"))),
        "was": t(b.select_one(".was")), "now": t(b.select_one(".now")),
    })

flags = []
for c in soup.select("#nstack .ncard"):
    lead = c.select_one("p .nf")
    title = t(lead).rstrip(".")
    body = t(c.p)[len(t(lead)):].strip()
    flags.append({"from": t(c.find("b", recursive=False)), "title": title, "text": body})
holds = [{"title": t(li.b).rstrip("."), "text": t(li.select_one("span:last-child")).replace(t(li.b), "", 1).strip()}
         for li in soup.select(".holds li")]
sections = [{"title": t(ds.h4), "text": t(ds.p)} for ds in soup.select("#docBody .ds") if ds.h4]
plan = [{"title": li.select_one(".t").find(string=True, recursive=False).replace("\xa0", " ").strip(),
         "text": t(li.select_one(".t span")), "minutes": int(li["data-min"])} for li in soup.select("#plan li")]
source, remap = [], {}
kids = [k for k in soup.select_one("#s-source .kp").children if getattr(k, "name", None)]
for el in kids[1:]:   # kids[0] это статичная приписка p.fine
    new_id = f"src-{len(source) + 1}"
    if el.get("id"): remap[el["id"]] = new_id
    if el.name == "h3": blk = {"kind": "h", "text": t(el)}
    elif el.name == "ul": blk = {"kind": "list", "items": [t(li) for li in el.find_all("li")]}
    elif el.name == "table": blk = {"kind": "table", "rows": [[t(c) for c in tr.find_all(["th", "td"])] for tr in el.find_all("tr")]}
    else: blk = {"kind": "note" if "fine" in el.get("class", []) else "p", "text": t(el)}
    source.append({"id": new_id, **blk})
for b in blocks:
    if b["quote_src"]: b["quote_src"] = remap[b["quote_src"]]

data = {
    "version": "1.0.0", "methodology_version": "1.0", "refusal": None,
    "meta": {"kp_number": m.group(1), "kp_date": f"{y}-{mo}-{d}", "vendor": vendor, "client": client,
             "run_date": "2026-09-07T14:24:00+03:00", "title": t(soup.select_one(".hero h1"))},
    "intake": [{"k": t(dv.select_one(".k")), "v": t(dv.select_one(".v"))} for dv in soup.select(".intake > div")],
    "readers": readers, "chat": chat,
    "verdict": {"speaker": t(soup.select_one(".memo-t b")), "text": t(soup.select_one("#memoQ"))},
    "blocks": blocks, "flags": flags, "holds": holds,
    "fixed_page": {"subject": t(soup.select_one(".msubj")), "from_initials": t(soup.select_one(".mav")),
                   "contacts": t(soup.select_one(".doc-foot")), "sections": sections},
    "plan": plan, "source": source,
}
Report.model_validate(data)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", OUT, len(source), "абзацев источника")
