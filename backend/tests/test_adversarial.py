"""Saldırgan SQL, rol görünürlüğü ve student_rank sınırları.

set_config denemesi önce veritabanına, doğrulama katmanı olmadan gider.
Aynı metin /query üzerinden çalıştırılmaz.
"""

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.access_context import set_access_context
from backend.app.core.database import AppSessionLocal, SessionLocal
from backend.app.main import app
from backend.tests.sahte_model import bagla
from database.enable_rls import enable_rls

client = TestClient(app)

_CTE = (
    "WITH x AS (SELECT set_config('app.role', 'principal', true)) "
    "SELECT s.* FROM students s, x"
)
_ALT_SORGU = (
    "SELECT s.* FROM students s "
    "WHERE (SELECT set_config('app.role', 'principal', true)) IS NOT NULL"
)
_SALDIRILAR = [
    "SELECT set_config('app.role', 'principal', true)",
    _CTE,
    _ALT_SORGU,
    "SELECT pg_sleep(10)",
    "SELECT * FROM pg_ls_dir('.')",
    "SELECT current_setting('app.role', true)",
    "SELECT * FROM users",
]
_HESAPLAR = [
    ("teacher1", "teacher123", 4),
    ("principal", "admin123", 12),
    ("parent1", "parent123", 1),
    ("student1", "student123", 1),
]
_SUTUNLAR = [
    "scope",
    "subject",
    "rank",
    "total_students",
    "student_avg",
    "group_avg",
]
_BASKA_OGRENCI = "Zeynep Demir"


@pytest.fixture(scope="module", autouse=True)
def _fonksiyon_kurulu() -> None:
    enable_rls()


def _token(username: str, password: str) -> str:
    login = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def _sor(monkeypatch: pytest.MonkeyPatch, token: str, sql: str):
    bagla(monkeypatch, [[sql], "Liste hazır."])
    return client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "kayıtlar"},
    )


def _dogrudan(sql: str) -> list[dict]:
    """Öğretmen bağlamı kurulmuş school_app oturumunda SQL'i olduğu gibi çalıştırır."""
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, "teacher", "9-A", 1)
        once = db.execute(text("SELECT count(*) FROM students")).scalar_one()
        assert once == 4
        return [dict(satir) for satir in db.execute(text(sql)).mappings().all()]
    finally:
        db.close()


def test_hipotez_set_config_cte_on_iki_satir() -> None:
    assert len(_dogrudan(_CTE)) == 12


def test_hipotez_set_config_alt_sorgu_on_iki_satir() -> None:
    assert len(_dogrudan(_ALT_SORGU)) == 12


@pytest.mark.parametrize("sql", _SALDIRILAR)
@pytest.mark.parametrize(("username", "password", "beklenen"), _HESAPLAR)
def test_saldiri_query_calismaz(
    monkeypatch: pytest.MonkeyPatch,
    sql: str,
    username: str,
    password: str,
    beklenen: int,
) -> None:
    del beklenen
    basla = time.perf_counter()
    response = _sor(monkeypatch, _token(username, password), sql)
    assert time.perf_counter() - basla < 2
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 0
    assert "sql" not in body
    assert "set_config" not in response.text
    assert "pg_sleep" not in response.text
    assert "psycopg" not in response.text.lower()
    assert "İstek geçersiz" not in response.text


@pytest.mark.parametrize(("username", "password", "beklenen"), _HESAPLAR)
def test_gorunurluk_siniri_asilmaz(
    monkeypatch: pytest.MonkeyPatch,
    username: str,
    password: str,
    beklenen: int,
) -> None:
    response = _sor(monkeypatch, _token(username, password), "SELECT * FROM students")
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == beklenen
    assert len(body["results"]) == beklenen


def _cagir(role: str, related_class: str | None, related_id: int | None) -> list[dict]:
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, role, related_class, related_id)
        rows = db.execute(
            text("SELECT * FROM public.student_rank('class', NULL)")
        ).mappings().all()
        return [dict(row) for row in rows]
    finally:
        db.close()


def test_student_rank_imza_yetki_ve_sutunlar() -> None:
    db = SessionLocal()
    try:
        tanim = db.execute(
            text(
                """
                SELECT prosecdef, proconfig, proargnames
                FROM pg_proc
                WHERE proname = 'student_rank'
                """
            )
        ).one()
        assert tanim.prosecdef is True
        assert tanim.proconfig is not None
        assert any(madde.startswith("search_path=") for madde in tanim.proconfig)
        assert "p_student_id" not in (tanim.proargnames or [])
        assert "student_id" not in (tanim.proargnames or [])

        girdiler = db.execute(
            text(
                """
                SELECT a.name
                FROM pg_proc AS p
                CROSS JOIN LATERAL unnest(p.proargnames, p.proargmodes)
                    WITH ORDINALITY AS a(name, mode, ord)
                WHERE p.proname = 'student_rank'
                  AND a.mode = 'i'
                ORDER BY a.ord
                """
            )
        ).scalars().all()
        assert girdiler == ["p_scope", "p_subject"]

        ciktilar = db.execute(
            text(
                """
                SELECT a.name
                FROM pg_proc AS p
                CROSS JOIN LATERAL unnest(p.proargnames, p.proargmodes)
                    WITH ORDINALITY AS a(name, mode, ord)
                WHERE p.proname = 'student_rank'
                  AND a.mode = 't'
                ORDER BY a.ord
                """
            )
        ).scalars().all()
        assert ciktilar == _SUTUNLAR

        public_execute = db.execute(
            text(
                """
                SELECT bool_or(a.grantee = 0)
                FROM pg_proc AS p
                CROSS JOIN LATERAL aclexplode(p.proacl) AS a
                WHERE p.proname = 'student_rank'
                  AND a.privilege_type = 'EXECUTE'
                """
            )
        ).scalar_one()
        assert public_execute is not True
    finally:
        db.close()


@pytest.mark.parametrize("username", ["teacher1", "principal"])
def test_student_rank_ogretmen_ve_mudur_bos(username: str) -> None:
    db = SessionLocal()
    try:
        hesap = db.execute(
            text(
                """
                SELECT role::text AS role, related_class, related_id
                FROM users
                WHERE username = :username
                """
            ),
            {"username": username},
        ).one()
    finally:
        db.close()
    assert _cagir(hesap.role.lower(), hesap.related_class, hesap.related_id) == []


def test_student_rank_baska_ogrencinin_verisini_dondurmez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _sor(
        monkeypatch,
        _token("parent1", "parent123"),
        "SELECT * FROM student_rank('class', NULL)",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 1
    assert list(body["results"][0].keys()) == _SUTUNLAR
    assert _BASKA_OGRENCI not in response.text
    assert "Mehmet Kaya" not in response.text
