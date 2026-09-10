import json
from goodkp.render import inject, wrap, render, load_template
from goodkp.schema import Report

TPL = '<title>T</title><style>a{}</style><script type="application/json" id="data"></script><div>x</div>'

def test_inject_puts_json_in_data_block():
    out = inject(TPL, {"a": 1})
    assert '<script type="application/json" id="data">{"a": 1}</script>' in out

def test_inject_escapes_closing_script():
    out = inject(TPL, {"a": "</script><b>"})
    assert "</script><b>" not in out.split('id="data">')[1].split("</script>")[0]
    assert "<\\/script>" in out

def test_inject_refuses_template_without_data_block():
    import pytest
    with pytest.raises(ValueError, match="#data"):
        inject("<div></div>", {})

def test_wrap_adds_skeleton():
    out = wrap(TPL)
    assert out.startswith("<!doctype html><html lang=\"ru\"><head>")
    assert '<meta charset="utf-8">' in out and 'content="dark"' in out
    assert "[hidden]{display:none!important}" in out
    assert out.index("<title>") < out.index("</head>") < out.index("<div>x</div>")

def test_render_golden(golden_path):
    r = Report.model_validate(json.loads(golden_path.read_text(encoding="utf-8")))
    html = render(r)
    assert "До стола директора" in html and html.count('id="data"') == 1

def test_template_has_no_skeleton(template_path):
    s = load_template()
    assert "<!doctype" not in s.lower() and "<body" not in s
