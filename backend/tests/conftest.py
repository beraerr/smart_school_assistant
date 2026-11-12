"""Test oturumunda süreç içi hız sınırı sayacını sıfırlar."""

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.rate_limiter import limiter, login_failure_limiter


@pytest.fixture(autouse=True)
def _hiz_siniri_sayacini_sifirla():
    limiter.reset()
    login_failure_limiter.reset()
    yield
    limiter.reset()
    login_failure_limiter.reset()
