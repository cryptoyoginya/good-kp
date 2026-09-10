from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent


def pytest_addoption(parser):
    parser.addoption("--update-baseline", action="store_true", default=False,
                     help="перезаписать эталонные скриншоты вместо сравнения")

@pytest.fixture
def template_path() -> Path:
    return ROOT / "template" / "report.html"

@pytest.fixture
def prototype_path() -> Path:
    return ROOT / "tests" / "fixtures" / "prototype.html"

@pytest.fixture
def golden_path() -> Path:
    return ROOT / "tests" / "golden" / "stroymarket" / "report.json"
