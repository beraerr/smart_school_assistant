"""bootstrap_roles.py'nin kurduğu RLS/GRANT/rol listesi database/ref/sema.sql ile eşit.

Beklenen değerler sema.sql ve roller.sql ayrıştırılarak elde edilir. DB testi
diğer DB testleri gibi settings'teki gerçek veritabanını kullanır.
"""

import re
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.database import engine
from database import bootstrap_roles as br
from database import enable_rls as er

_REF = _PROJECT_ROOT / "database" / "ref"


def _norm(ifade: str) -> str:
    return " ".join(ifade.split())


def _sema_ifadeleri() -> list[str]:
    satirlar = [
        s
        for s in (_REF / "sema.sql").read_text(encoding="utf-8").splitlines()
        if not s.startswith("--") and not s.startswith("\\")
    ]
    parcalar = re.split(r";[ \t]*\n", "\n".join(satirlar))
    return [_norm(p) for p in parcalar if p.strip()]


def _politika_adi(ifade: str) -> str:
    return re.match(r"CREATE POLICY (\w+) ON ", ifade).group(1)


_ENABLE_RLS_POLITIKALARI = {er._GRADES_POLICY, er._ATTENDANCE_POLICY}


def _beklenen() -> dict[str, list[str]]:
    tum = _sema_ifadeleri()
    politikalar = [t for t in tum if t.startswith("CREATE POLICY ")]
    return {
        "rls": [t for t in tum if t.endswith("ENABLE ROW LEVEL SECURITY")],
        "politikalar": politikalar,
        "bootstrap_politikalari": [
            p for p in politikalar if _politika_adi(p) not in _ENABLE_RLS_POLITIKALARI
        ],
        # Fonksiyon ACL'leri enable_rls.py'de; REVOKE sema.sql'de yalnız onlar için.
        "grantler": [
            t for t in tum if t.startswith("GRANT ") and " ON FUNCTION " not in t
        ],
    }


def test_rls_ifadeleri_sema_ile_esit() -> None:
    assert sorted(map(_norm, br.RLS_IFADELERI)) == sorted(_beklenen()["rls"])


def test_politikalar_sema_ile_esit() -> None:
    beklenen = _beklenen()["bootstrap_politikalari"]
    assert beklenen, "sema.sql'de politika bulunamadı"
    assert sorted(map(_norm, br.POLITIKA_IFADELERI)) == sorted(beklenen)


def test_grantler_sema_ile_esit() -> None:
    beklenen = _beklenen()["grantler"]
    assert beklenen, "sema.sql'de GRANT bulunamadı"
    assert sorted(map(_norm, br.GRANT_IFADELERI)) == sorted(beklenen)


def test_bootstrap_ve_enable_rls_politikalari_sema_nin_tamamini_kapsar() -> None:
    sema = {_politika_adi(p) for p in _beklenen()["politikalar"]}
    bootstrap = {_politika_adi(p) for p in br.POLITIKA_IFADELERI}
    assert bootstrap | _ENABLE_RLS_POLITIKALARI == sema
    assert not bootstrap & _ENABLE_RLS_POLITIKALARI


def test_rol_oznitelikleri_roller_sql_ile_ayni() -> None:
    satir = next(
        s
        for s in (_REF / "roller.sql").read_text(encoding="utf-8").splitlines()
        if s.startswith("ALTER ROLE school_app WITH ")
    )
    assert br.ROL_OZNITELIKLERI == satir.removeprefix("ALTER ROLE school_app WITH ").rstrip(";")


def test_veritabaninda_politikalar_ve_yetkiler_sema_ile_esit() -> None:
    """Yeniden çalıştırma hata vermez; sonuçta politika/GRANT kümesi sema.sql'dekiyle aynı."""
    br.bootstrap_roles()
    br.bootstrap_roles()
    er.enable_rls()

    beklenen = _beklenen()
    with engine.connect() as conn:
        politikalar = {
            r[0]
            for r in conn.execute(
                text("SELECT policyname FROM pg_policies WHERE schemaname = 'public'")
            )
        }
        rls = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity"
                )
            )
        }
        select_tablolari = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT table_name FROM information_schema.role_table_grants "
                    "WHERE grantee = 'school_app' AND table_schema = 'public' "
                    "AND privilege_type = 'SELECT'"
                )
            )
        }
        rol = conn.execute(
            text(
                "SELECT rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolreplication, "
                "rolbypassrls FROM pg_roles WHERE rolname = 'school_app'"
            )
        ).one()

    assert politikalar == {_politika_adi(p) for p in beklenen["politikalar"]}
    assert rls == {
        re.match(r"ALTER TABLE public\.(\w+) ", t).group(1) for t in beklenen["rls"]
    }
    assert select_tablolari == {
        re.match(r"GRANT SELECT ON TABLE public\.(\w+) ", t).group(1)
        for t in beklenen["grantler"]
        if t.startswith("GRANT SELECT ON TABLE ")
    }
    assert tuple(rol) == (False, False, False, True, False, False)


def test_parolasiz_url_hata_verip_durur(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(br.settings, "APP_DATABASE_URL", "postgresql://school_app@db/okul")
    with pytest.raises(SystemExit):
        br.uygulama_kimligi()
