from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent

@pytest.fixture
def template_path() -> Path:
    return ROOT / "template" / "report.html"

@pytest.fixture
def prototype_path() -> Path:
    return ROOT / "tests" / "fixtures" / "prototype.html"

@pytest.fixture
def golden_path() -> Path:
    return ROOT / "tests" / "golden" / "stroymarket" / "report.json"
