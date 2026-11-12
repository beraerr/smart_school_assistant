"""Kayan pencere: 11. istek, pencerenin kayması, kullanıcıların ayrılığı."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.rate_limiter import RateLimiter


def test_onbirinci_istek_reddedilir() -> None:
    simdi = {"t": 0.0}
    limiter = RateLimiter(clock=lambda: simdi["t"])
    for _ in range(10):
        izin, bekle = limiter.allow("ali")
        assert izin is True
        assert bekle == 0
    izin, bekle = limiter.allow("ali")
    assert izin is False
    assert bekle > 0


def test_pencere_kayinca_acilir() -> None:
    simdi = {"t": 0.0}
    limiter = RateLimiter(clock=lambda: simdi["t"])
    for saniye in range(10):
        simdi["t"] = float(saniye)
        assert limiter.allow("ali")[0] is True
    simdi["t"] = 9.0
    assert limiter.allow("ali")[0] is False
    simdi["t"] = 60.0
    assert limiter.allow("ali")[0] is True


def test_kullanicilar_ayri_sayilir() -> None:
    limiter = RateLimiter(clock=lambda: 0.0)
    for _ in range(10):
        assert limiter.allow("ali")[0] is True
    assert limiter.allow("ali")[0] is False
    izin, bekle = limiter.allow("ayse")
    assert izin is True
    assert bekle == 0


def test_sayac_ve_saat_enjekte_edilir() -> None:
    depo: dict[str, list[float]] = {}
    gorulen: list[float] = []

    def saat() -> float:
        gorulen.append(5.0)
        return 5.0

    limiter = RateLimiter(clock=saat, counter=depo)
    for _ in range(10):
        assert limiter.allow("ali")[0] is True
    assert limiter.allow("ali")[0] is False
    assert depo["ali"] == [5.0] * 10
    assert gorulen
