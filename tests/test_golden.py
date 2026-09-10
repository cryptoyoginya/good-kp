import json
from goodkp.schema import Report

def test_golden_valid(golden_path):
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    r = Report.model_validate(data)
    assert r.meta.title == "До стола директора это КП не дойдет"
    assert [b.state for b in r.blocks].count("crit") == 3
    assert r.readers[0].name == "Сергей" and r.readers[0].feed[0].step == "pre"
    assert sum(p.minutes for p in r.plan) == 60
    assert any(m.file for m in r.chat)
    assert [s.kind for s in r.source].count("table") == 2 and r.source[0].kind == "h"
    assert all(f.title for f in r.flags) and len(r.flags) == 6
