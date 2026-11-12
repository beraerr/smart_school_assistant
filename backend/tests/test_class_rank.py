"""class_rank: sınıf öğretmeni yalnız kendi sınıfının okul içindeki sıra satırını görür."""

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.access_context import set_access_context
from backend.app.core.bugun import bugun
from backend.app.core.database import AppSessionLocal, SessionLocal
from backend.app.core.sql_safety import validate_select_only
from backend.app.main import app
from backend.tests import mock_veri
from backend.tests.sahte_model import bagla
from config.settings import settings
from database.enable_rls import enable_rls

client = TestClient(app)

_SUTUNLAR = ["class_name", "subject", "rank", "total_classes", "class_avg", "school_avg"]


@pytest.fixture(scope="module", autouse=True)
def _fonksiyon_kurulu() -> None:
    enable_rls()


def _hesap(username: str) -> tuple[str, str | None, int | None]:
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                "SELECT role::text AS role, related_class, related_id "
                "FROM users WHERE username = :username"
            ),
            {"username": username},
        ).one()
    finally:
        db.close()
    return row.role.lower(), row.related_class, row.related_id


def _cagir(
    role: str, related_class: str | None, related_id: int | None, subject: str | None
) -> list[dict]:
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, role, related_class, related_id)
        rows = db.execute(
            text("SELECT * FROM public.class_rank(:subject)"), {"subject": subject}
        ).mappings().all()
        return [dict(row) for row in rows]
    finally:
        db.close()


def _beklenen(sinif: str, gun: date, ders: str | None) -> dict:
    """mock_data.json'dan: sınıf ortalaması, okul ortalaması, sıra, sınıf sayısı."""
    notlar, _ = mock_veri.gune_kadar(gun)
    sinif_of = {r["id"]: r["class_name"] for r in mock_veri.ogrenciler()}
    secili = [r for r in notlar if ders is None or r["subject"].lower() == ders.lower()]
    sinif_notlari: dict[str, list[float]] = {s: [] for s in mock_veri.siniflar()}
    for r in secili:
        sinif_notlari[sinif_of[r["student_id"]]].append(r["grade"])
    ortalama = {s: (sum(v) / len(v) if v else None) for s, v in sinif_notlari.items()}
    benim = ortalama[sinif]
    dolu = [v for v in ortalama.values() if v is not None]
    sira = len(dolu) + 1 if benim is None else 1 + sum(1 for v in dolu if v > benim)
    tum = [r["grade"] for r in secili]
    return {
        "rank": sira,
        "total_classes": len(mock_veri.siniflar()),
        "class_avg": benim,
        "school_avg": sum(tum) / len(tum) if tum else None,
    }


@pytest.mark.parametrize("subject", [None, "Matematik"])
def test_ogretmen_kendi_sinifinin_satirini_alir(subject: str | None) -> None:
    role, related_class, related_id = _hesap("teacher1")
    assert related_class is not None
    gelen = _cagir(role, related_class, related_id, subject)
    assert len(gelen) == 1
    satir = gelen[0]
    assert list(satir.keys()) == _SUTUNLAR
    assert satir["class_name"] == related_class
    assert satir["subject"] == subject
    beklenen = _beklenen(related_class, bugun(), subject)
    assert satir["rank"] == beklenen["rank"]
    assert satir["total_classes"] == beklenen["total_classes"]
    assert float(satir["class_avg"]) == pytest.approx(beklenen["class_avg"], abs=1e-6)
    assert float(satir["school_avg"]) == pytest.approx(beklenen["school_avg"], abs=1e-6)


def test_gelecek_notu_saymaz(monkeypatch: pytest.MonkeyPatch) -> None:
    gun = date(2026, 11, 3)
    monkeypatch.setattr(settings, "DEMO_TODAY", gun)
    role, related_class, related_id = _hesap("teacher1")
    gelen = _cagir(role, related_class, related_id, None)
    beklenen = _beklenen(related_class, gun, None)
    assert gelen[0]["rank"] == beklenen["rank"]
    assert float(gelen[0]["class_avg"]) == pytest.approx(beklenen["class_avg"], abs=1e-6)
    yil_sonu = _beklenen(related_class, date(2027, 6, 25), None)
    assert yil_sonu["class_avg"] != pytest.approx(beklenen["class_avg"], abs=1e-6)


@pytest.mark.parametrize("username", ["principal", "parent1", "student1"])
def test_ogretmen_disi_roller_satir_gormez(username: str) -> None:
    role, related_class, related_id = _hesap(username)
    assert _cagir(role, related_class, related_id, None) == []


def test_sinifsiz_ogretmen_satir_gormez() -> None:
    assert _cagir("teacher", None, None, None) == []


def test_baska_sinif_adi_veya_ortalamasi_donmez() -> None:
    role, related_class, related_id = _hesap("teacher1")
    gelen = _cagir(role, related_class, related_id, None)
    assert {satir["class_name"] for satir in gelen} == {related_class}


def test_fonksiyon_yetkisi_ve_imzasi() -> None:
    db = SessionLocal()
    try:
        tanim = db.execute(
            text("SELECT prosecdef, proconfig FROM pg_proc WHERE proname = 'class_rank'")
        ).one()
        assert tanim.prosecdef is True
        assert any("search_path" in madde for madde in tanim.proconfig)
        sutunlar = db.execute(
            text(
                """
                SELECT a.name
                FROM pg_proc AS p
                CROSS JOIN LATERAL unnest(p.proargnames, p.proargmodes)
                    WITH ORDINALITY AS a(name, mode, ord)
                WHERE p.proname = 'class_rank' AND a.mode = 't'
                ORDER BY a.ord
                """
            )
        ).scalars().all()
        assert sutunlar == _SUTUNLAR
        assert db.execute(
            text("SELECT has_function_privilege('school_app', 'public.class_rank(text)', 'EXECUTE')")
        ).scalar_one() is True
        public_execute = db.execute(
            text(
                """
                SELECT bool_or(a.grantee = 0)
                FROM pg_proc AS p
                CROSS JOIN LATERAL aclexplode(p.proacl) AS a
                WHERE p.proname = 'class_rank' AND a.privilege_type = 'EXECUTE'
                """
            )
        ).scalar_one()
        assert public_execute is not True
    finally:
        db.close()


def test_sql_denetimi_class_rank_kabul_eder() -> None:
    validate_select_only(
        "SELECT class_name, \"rank\", total_classes FROM class_rank(NULL)"
    )


def test_query_ogretmen_sinif_sirasi(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(
        monkeypatch,
        [
            [
                "SELECT class_name, \"rank\", total_classes, ROUND(class_avg, 2) AS class_avg, "
                "ROUND(school_avg, 2) AS school_avg FROM class_rank(NULL)"
            ],
            "Sınıfınızın sırası hazır.",
        ],
    )
    login = client.post("/auth/login", json={"username": "teacher1", "password": "teacher123"})
    token = login.json()["access_token"]
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "sınıfım okulda kaçıncı"},
    )
    assert response.status_code == 200
    body = response.json()
    _, related_class, _ = _hesap("teacher1")
    assert body["row_count"] == 1
    assert body["results"][0]["class_name"] == related_class
    assert body["results"][0]["total_classes"] == len(mock_veri.siniflar())
