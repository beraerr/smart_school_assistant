"""student_rank: veli ve öğrenci yalnız kendi sıra satırını görür."""

import sys
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

_SUTUNLAR = [
    "scope",
    "subject",
    "rank",
    "total_students",
    "student_avg",
    "group_avg",
]

_BEKLENEN = text(
    """
    WITH me AS (
        SELECT id, class_name
        FROM public.students
        WHERE id = :student_id
    ),
    averages AS (
        SELECT
            s.id,
            CAST(AVG(g.grade) AS numeric) AS student_avg
        FROM public.students AS s
        CROSS JOIN me AS m
        LEFT JOIN public.grades AS g
            ON g.student_id = s.id
           AND (
                CAST(:subject AS text) IS NULL
                OR lower(g.subject) = lower(CAST(:subject AS text))
           )
        WHERE CAST(:scope AS text) = 'school'
           OR s.class_name = m.class_name
        GROUP BY s.id
    ),
    ranked AS (
        SELECT
            a.id,
            a.student_avg,
            CAST(RANK() OVER (ORDER BY a.student_avg DESC) AS integer) AS rank,
            CAST(COUNT(*) OVER () AS integer) AS total_students,
            AVG(a.student_avg) OVER () AS group_avg
        FROM averages AS a
    )
    SELECT rank, total_students, student_avg, group_avg
    FROM ranked
    WHERE id = :student_id
    """
)


@pytest.fixture(scope="module", autouse=True)
def _fonksiyon_kurulu() -> None:
    enable_rls()


def _hesap(username: str) -> tuple[str, str | None, int | None]:
    db = SessionLocal()
    try:
        row = db.execute(
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
    return row.role.lower(), row.related_class, row.related_id


def _cagir(
    role: str,
    related_class: str | None,
    related_id: int | None,
    scope: str,
    subject: str | None,
) -> list[dict]:
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, role, related_class, related_id)
        rows = db.execute(
            text("SELECT * FROM public.student_rank(:scope, :subject)"),
            {"scope": scope, "subject": subject},
        ).mappings().all()
        return [dict(row) for row in rows]
    finally:
        db.close()


def _dogru(student_id: int, scope: str, subject: str | None) -> dict:
    db = SessionLocal()
    try:
        row = db.execute(
            _BEKLENEN,
            {"student_id": student_id, "scope": scope, "subject": subject},
        ).mappings().one()
    finally:
        db.close()
    return dict(row)


def _token(username: str, password: str) -> str:
    login = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


@pytest.mark.parametrize("username", ["parent1", "student1"])
@pytest.mark.parametrize(
    ("scope", "subject", "toplam"),
    [
        ("class", None, 4),
        ("school", None, 12),
        ("class", "Matematik", 4),
        ("school", "Matematik", 12),
    ],
)
def test_kendi_satiri_dogru_degerle_eslesir(
    username: str, scope: str, subject: str | None, toplam: int
) -> None:
    role, related_class, related_id = _hesap(username)
    assert related_id is not None
    gelen = _cagir(role, related_class, related_id, scope, subject)
    assert len(gelen) == 1
    satir = gelen[0]
    assert list(satir.keys()) == _SUTUNLAR
    assert satir["scope"] == scope
    assert satir["subject"] == subject
    beklenen = _dogru(related_id, scope, subject)
    assert satir["rank"] == beklenen["rank"]
    assert satir["total_students"] == beklenen["total_students"] == toplam
    assert satir["student_avg"] == beklenen["student_avg"]
    assert satir["group_avg"] == beklenen["group_avg"]


def test_ders_adi_buyuk_kucuk_harf_farketmez() -> None:
    role, related_class, related_id = _hesap("parent1")
    kucuk = _cagir(role, related_class, related_id, "class", "matematik")
    assert len(kucuk) == 1
    beklenen = _dogru(related_id, "class", "Matematik")
    assert kucuk[0]["student_avg"] == beklenen["student_avg"]
    assert kucuk[0]["rank"] == beklenen["rank"]
    assert kucuk[0]["subject"] == "matematik"


@pytest.mark.parametrize("username", ["teacher1", "principal"])
@pytest.mark.parametrize("scope", ["class", "school"])
def test_ogretmen_ve_mudur_satir_gormez(username: str, scope: str) -> None:
    role, related_class, related_id = _hesap(username)
    assert _cagir(role, related_class, related_id, scope, None) == []


def test_bos_ogrenci_kimligi_satir_dondurmez() -> None:
    assert _cagir("parent", None, None, "class", None) == []
    assert _cagir("student", None, None, "school", "Matematik") == []


def test_gecersiz_kapsam_satir_dondurmez() -> None:
    role, related_class, related_id = _hesap("parent1")
    assert _cagir(role, related_class, related_id, "grade", None) == []
    assert _cagir(role, related_class, related_id, "CLASS", None) == []


def test_fonksiyon_yetkisi_ve_imzasi() -> None:
    db = SessionLocal()
    try:
        tanim = db.execute(
            text(
                """
                SELECT prosecdef, proconfig
                FROM pg_proc
                WHERE proname = 'student_rank'
                """
            )
        ).one()
        assert tanim.prosecdef is True
        assert tanim.proconfig is not None
        assert any("search_path" in madde for madde in tanim.proconfig)

        sutunlar = db.execute(
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
        assert sutunlar == _SUTUNLAR

        school = db.execute(
            text(
                """
                SELECT has_function_privilege(
                    'school_app',
                    'public.student_rank(text, text)',
                    'EXECUTE'
                )
                """
            )
        ).scalar_one()
        assert school is True

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


def test_query_student_rank_bir_satir(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(
        monkeypatch,
        [["SELECT * FROM student_rank('class', NULL)"], "Sıran hazır."],
    )
    token = _token("parent1", "parent123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "sınıfta kaçıncı"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["total_students"] == 4
    assert set(body["results"][0]) == set(_SUTUNLAR)


def test_query_birincisi_kim_tekil_kayit_acmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    bagla(monkeypatch, ["Başka bir öğrencinin kaydını açamam. Kendi sırana bakabilirim."])
    token = _token("parent1", "parent123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "sınıfın birincisi kim"},
    )
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert "NOT_SUPPORTED_COMPARISON" not in response.text
    assert "SELECT" not in response.text
    assert "İstek geçersiz" not in response.text


@pytest.mark.parametrize(
    "sql",
    ["SELECT * FROM users", "SELECT * FROM pg_ls_dir('.')"],
)
def test_query_users_ve_pg_ls_dir_reddedilir(
    monkeypatch: pytest.MonkeyPatch, sql: str
) -> None:
    bagla(monkeypatch, [[sql]] * 3)
    token = _token("parent1", "parent123")
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "dosyalar"},
    )
    assert response.status_code == 200
    assert "sql" not in response.json()
    assert sql not in response.text
    assert "psycopg" not in response.text.lower()
