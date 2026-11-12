"""Asistan talimatındaki her SQL örneği doğrulayıcıdan geçmeli.

Talimat ile validate_select_only birbirinden koparsa (talimat bir kalıp önerir, doğrulayıcı
reddeder) bu testler başarısız olur. Örnekler talimat metninden çıkarılır; elle kopyalanmaz.
"""

import re
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.sql_safety import validate_select_only
from backend.app.services import assistant_service

_ROLLER = ("principal", "teacher", "parent", "student")
_DILLER = ("tr", "en")

# Talimatta bir SQL örneği her zaman bir satırın sonuna kadar uzanır ve SELECT ... FROM içerir.
_ORNEK = re.compile(r"\bSELECT\b.+?\bFROM\b.*")


@pytest.fixture(autouse=True)
def _sema_sabit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assistant_service, "build_schema_context", lambda: "")


def _ornekler(metin: str) -> list[str]:
    bulunan: list[str] = []
    for satir in metin.splitlines():
        eslesme = _ORNEK.search(satir)
        if eslesme:
            bulunan.append(eslesme.group(0).strip())
    return bulunan


@pytest.mark.parametrize("dil", _DILLER)
@pytest.mark.parametrize("rol", _ROLLER)
def test_talimattaki_her_sql_ornegi_dogrulayicidan_gecer(rol: str, dil: str) -> None:
    metin = assistant_service._sistem(rol, dil)
    ornekler = _ornekler(metin)
    # Çıkarma sessizce boş dönüp testi anlamsızlaştırmasın.
    asgari = 4 if rol in {"parent", "student"} else 2
    assert len(ornekler) >= asgari, ornekler
    for sql in ornekler:
        try:
            validate_select_only(sql)
        except ValueError as exc:  # noqa: PERF203 - hangi örnek reddedildi bilinmeli
            pytest.fail(f"Talimattaki örnek reddedildi ({rol}/{dil}): {sql!r} -> {exc}")


@pytest.mark.parametrize("dil", _DILLER)
@pytest.mark.parametrize("rol", ("parent", "student"))
def test_talimatin_student_rank_varyantlari_gecer(rol: str, dil: str) -> None:
    """Talimat 'aynı sorgu, student_rank('school', NULL) ile' gibi varyantları da önerir."""
    metin = assistant_service._sistem(rol, dil)
    temel = next(o for o in _ornekler(metin) if "student_rank('class', NULL)" in o)
    for degisim in ("student_rank('school', NULL)", "student_rank('class', 'Matematik')"):
        validate_select_only(temel.replace("student_rank('class', NULL)", degisim))


@pytest.mark.parametrize("dil", _DILLER)
@pytest.mark.parametrize("rol", _ROLLER)
def test_talimatin_onerdigi_kalip_adlari_hala_talimatta(rol: str, dil: str) -> None:
    """Aşağıdaki kalıp testleri talimatla bağlı kalsın: metinden silinirlerse test bildirir."""
    metin = assistant_service._sistem(rol, dil)
    assert "SUM(CASE" in metin
    assert "DATE 'YYYY-MM-DD'" in metin
    assert "GROUP BY status" in metin


@pytest.mark.parametrize(
    "sql",
    [
        # "SUM(CASE ...)" ile ayrı sayım (talimat: mazeretsiz/mazeretli ayrı say).
        "SELECT SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) AS absent, "
        "SUM(CASE WHEN status = 'excused' THEN 1 ELSE 0 END) AS excused FROM attendance",
        # "GROUP BY status".
        "SELECT status, COUNT(*) AS n FROM attendance GROUP BY status",
        # Tarih bloğundaki tarih sabit değer olarak: DATE 'YYYY-MM-DD'; aralık için AND.
        "SELECT subject, ROUND(AVG(grade)::numeric, 2) AS average FROM grades "
        "WHERE date >= DATE '2026-09-28' AND date <= DATE '2026-10-23' GROUP BY subject",
        "SELECT * FROM attendance WHERE date = DATE '2026-11-04'",
    ],
)
def test_talimatin_tarif_ettigi_kaliplar_gecer(sql: str) -> None:
    validate_select_only(sql)
