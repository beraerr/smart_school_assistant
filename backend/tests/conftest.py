"""Test oturumunda süreç içi hız sınırı sayacını sıfırlar ve "bugün"ü sabitler."""

import sys
from datetime import date
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.rate_limiter import limiter, login_failure_limiter
from config.settings import settings

# Öğretim yılı sonu: bütün mock satırları görünür. Tarihe duyarlı testler
# monkeypatch ile kendi gününü verir.
VARSAYILAN_BUGUN = date(2027, 6, 25)


@pytest.fixture(autouse=True)
def _hiz_siniri_sayacini_sifirla():
    limiter.reset()
    login_failure_limiter.reset()
    yield
    limiter.reset()
    login_failure_limiter.reset()


@pytest.fixture(autouse=True)
def _sabit_bugun(monkeypatch: pytest.MonkeyPatch) -> None:
    """Testler çalıştırıldığı güne bağlı olmasın."""
    monkeypatch.setattr(settings, "DEMO_TODAY", VARSAYILAN_BUGUN)
