"""class_teacher: oturumdaki öğrencinin sınıf öğretmeninin yalnız adı."""

import sys
from pathlib import Path

import pytest
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.access_context import set_access_context
from backend.app.core.database import AppSessionLocal, SessionLocal
from database.enable_rls import enable_rls

_OGRETMEN = "Ahmet Öğretmen"
_BASKA = "Zeynep Demir"


@pytest.fixture(scope="module", autouse=True)
def _fonksiyon_kurulu() -> None:
    enable_rls()


def _cagir(role: str, related_class: str | None, related_id: int | None) -> list[str]:
    db = AppSessionLocal()
    try:
        db.connection()
        set_access_context(db, role, related_class, related_id)
        return list(
            db.execute(text("SELECT name FROM public.class_teacher()")).scalars().all()
        )
    finally:
        db.close()


def test_class_teacher_imza_yetki_ve_sutun() -> None:
    db = SessionLocal()
    try:
        tanim = db.execute(
            text(
                """
                SELECT prosecdef, proconfig, proargnames
                FROM pg_proc
                WHERE proname = 'class_teacher'
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
                WHERE p.proname = 'class_teacher'
                  AND a.mode = 'i'
                ORDER BY a.ord
                """
            )
        ).scalars().all()
        assert girdiler == []

        ciktilar = db.execute(
            text(
                """
                SELECT a.name
                FROM pg_proc AS p
                CROSS JOIN LATERAL unnest(p.proargnames, p.proargmodes)
                    WITH ORDINALITY AS a(name, mode, ord)
                WHERE p.proname = 'class_teacher'
                  AND a.mode = 't'
                ORDER BY a.ord
                """
            )
        ).scalars().all()
        assert ciktilar == ["name"]

        public_execute = db.execute(
            text(
                """
                SELECT bool_or(a.grantee = 0)
                FROM pg_proc AS p
                CROSS JOIN LATERAL aclexplode(p.proacl) AS a
                WHERE p.proname = 'class_teacher'
                  AND a.privilege_type = 'EXECUTE'
                """
            )
        ).scalar_one()
        assert public_execute is not True

        school = db.execute(
            text(
                """
                SELECT has_function_privilege(
                    'school_app',
                    'public.class_teacher()',
                    'EXECUTE'
                )
                """
            )
        ).scalar_one()
        assert school is True
    finally:
        db.close()


@pytest.mark.parametrize(
    ("role", "related_class", "related_id"),
    [("teacher", "9-A", 1), ("principal", None, None)],
)
def test_class_teacher_ogretmen_ve_mudur_bos(
    role: str, related_class: str | None, related_id: int | None
) -> None:
    assert _cagir(role, related_class, related_id) == []


def test_class_teacher_yalniz_ad() -> None:
    adlar = _cagir("parent", None, 1)
    assert adlar == [_OGRETMEN]
    assert _BASKA not in adlar
