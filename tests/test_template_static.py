import re

def test_dark_only(template_path):
    s = template_path.read_text(encoding="utf-8")
    assert "prefers-color-scheme" not in s
    assert "data-theme" not in s
    assert re.search(r":root\s*\{[^}]*color-scheme:\s*dark", s)

def test_no_banned_glyphs_in_static_text(template_path):
    s = template_path.read_text(encoding="utf-8")
    body = s[s.index("<header"):]
    for g in ("—", "·", "ё", "Ё"):
        assert g not in body, g
