"""school_app rolünü ve ilk RLS kurulumunu (database/ref/sema.sql) kurar.

Süper kullanıcı bağlantısıyla (DATABASE_URL) çalışır ve yeniden çalıştırılabilir.
Sıra: init_db.py -> bootstrap_roles.py -> enable_rls.py -> seed_mock.py.

Kurulanlar:
- school_app rolü: kullanıcı adı ve parola APP_DATABASE_URL'den ayrıştırılır;
  öznitelikler database/ref/roller.sql'dekiyle aynıdır. Rol varsa dokunulmaz
  ("zaten var" loglanır; parola değiştirilmez).
- attendance, grades, students için ENABLE ROW LEVEL SECURITY.
- İzin veren politikalar: attendance_via_students, grades_via_students,
  students_role_access. Politika varsa yeniden yazılmaz ("zaten var" loglanır).
- Şema ve tablo GRANT'leri.

Aşağıdaki ifadeler database/ref/sema.sql'den birebir alınmıştır; sema.sql'de
olmayan hiçbir nesne eklenmez. Zaman kapısı politikaları
(*_zaman_kapisi) ve fonksiyonların (student_rank, class_teacher) yetkileri
enable_rls.py'ye aittir; fonksiyonlar o betikte oluştuğu için burada yoktur.

Proje kökünden:
    python database/bootstrap_roles.py
"""

import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from psycopg2 import sql
from sqlalchemy import text
from sqlalchemy.engine.url import make_url

from backend.app.core.database import engine
from config.settings import settings

# database/ref/roller.sql: ALTER ROLE school_app WITH ...
ROL_OZNITELIKLERI = (
    "NOSUPERUSER INHERIT NOCREATEROLE NOCREATEDB LOGIN NOREPLICATION NOBYPASSRLS"
)

# sema.sql: "ALTER TABLE public.<tablo> ENABLE ROW LEVEL SECURITY;"
RLS_IFADELERI = [
    "ALTER TABLE public.attendance ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE public.grades ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE public.students ENABLE ROW LEVEL SECURITY",
]

# sema.sql: izin veren (PERMISSIVE) politikalar.
POLITIKA_IFADELERI = [
    """CREATE POLICY attendance_via_students ON public.attendance FOR SELECT USING ((student_id IN ( SELECT students.id
   FROM public.students)))""",
    """CREATE POLICY grades_via_students ON public.grades FOR SELECT USING ((student_id IN ( SELECT students.id
   FROM public.students)))""",
    """CREATE POLICY students_role_access ON public.students FOR SELECT USING (((current_setting('app.role'::text, true) = 'principal'::text) OR ((current_setting('app.role'::text, true) = 'teacher'::text) AND ((class_name)::text = current_setting('app.class'::text, true))) OR ((current_setting('app.role'::text, true) = ANY (ARRAY['parent'::text, 'student'::text])) AND (id = (NULLIF(current_setting('app.student_id'::text, true), ''::text))::integer))))""",
]

# sema.sql: şema ve tablo ACL'leri (fonksiyon ACL'leri enable_rls.py'de).
GRANT_IFADELERI = [
    "GRANT USAGE ON SCHEMA public TO school_app",
    "GRANT SELECT ON TABLE public.attendance TO school_app",
    "GRANT SELECT ON TABLE public.grades TO school_app",
    "GRANT SELECT ON TABLE public.students TO school_app",
]

_ROL = "school_app"
_POLITIKA_RE = re.compile(r"^CREATE POLICY (\w+) ON public\.(\w+) ")
_RLS_RE = re.compile(r"^ALTER TABLE public\.(\w+) ENABLE ROW LEVEL SECURITY$")
_TABLO_GRANT_RE = re.compile(r"^GRANT SELECT ON TABLE public\.(\w+) TO school_app$")


def _log(mesaj: str) -> None:
    print(f"[bootstrap_roles] {mesaj}")


def uygulama_kimligi() -> tuple[str, str]:
    """APP_DATABASE_URL'den (kullanıcı, parola); yoksa hata verip durur."""
    adres = (settings.APP_DATABASE_URL or "").strip()
    if not adres:
        raise SystemExit("APP_DATABASE_URL boş; school_app rolü kurulamaz.")
    url = make_url(adres)
    if not url.username or not url.password:
        raise SystemExit(
            "APP_DATABASE_URL içinde kullanıcı adı ve parola olmalı; school_app rolü kurulamaz."
        )
    if url.username != _ROL:
        raise SystemExit(
            f"APP_DATABASE_URL kullanıcısı '{_ROL}' olmalı (RLS politikaları bu role bağlı)."
        )
    return url.username, url.password


def _rol_kur(conn, kullanici: str, parola: str) -> None:
    var = conn.execute(
        text("SELECT 1 FROM pg_roles WHERE rolname = :ad"), {"ad": kullanici}
    ).first()
    if var:
        _log(f"rol {kullanici}: zaten var (değiştirilmedi)")
        return
    raw = conn.connection.cursor()
    try:
        ifade = sql.SQL("CREATE ROLE {} WITH {} PASSWORD {}").format(
            sql.Identifier(kullanici),
            sql.SQL(ROL_OZNITELIKLERI),
            sql.Literal(parola),
        )
        raw.execute(ifade)
    finally:
        raw.close()
    _log(f"rol {kullanici}: oluşturuldu")


def _tablolar_var_mi(conn) -> None:
    eksik = [
        t
        for t in ("attendance", "grades", "students")
        if conn.execute(text("SELECT to_regclass(:ad)"), {"ad": f"public.{t}"}).scalar_one()
        is None
    ]
    if eksik:
        raise SystemExit(
            f"Tablo yok: {', '.join(eksik)}. Önce database/init_db.py çalıştırılmalı."
        )


def _rls_ac(conn) -> None:
    for ifade in RLS_IFADELERI:
        tablo = _RLS_RE.match(ifade).group(1)
        acik = conn.execute(
            text(
                "SELECT c.relrowsecurity FROM pg_class c "
                "JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = :t"
            ),
            {"t": tablo},
        ).scalar_one()
        conn.exec_driver_sql(ifade)
        _log(f"RLS {tablo}: " + ("zaten açık" if acik else "açıldı"))


def _politikalar(conn) -> None:
    for ifade in POLITIKA_IFADELERI:
        ad, tablo = _POLITIKA_RE.match(ifade).groups()
        var = conn.execute(
            text(
                "SELECT 1 FROM pg_policies WHERE schemaname = 'public' "
                "AND tablename = :t AND policyname = :p"
            ),
            {"t": tablo, "p": ad},
        ).first()
        if var:
            _log(f"politika {ad} ({tablo}): zaten var (değiştirilmedi)")
            continue
        conn.exec_driver_sql(ifade)
        _log(f"politika {ad} ({tablo}): oluşturuldu")


def _grantler(conn) -> None:
    for ifade in GRANT_IFADELERI:
        eslesme = _TABLO_GRANT_RE.match(ifade)
        if eslesme:
            tablo = eslesme.group(1)
            var = conn.execute(
                text("SELECT has_table_privilege(:r, :t, 'SELECT')"),
                {"r": _ROL, "t": f"public.{tablo}"},
            ).scalar_one()
            etiket = f"SELECT {tablo}"
        else:
            var = conn.execute(
                text("SELECT has_schema_privilege(:r, 'public', 'USAGE')"), {"r": _ROL}
            ).scalar_one()
            etiket = "USAGE public"
        conn.exec_driver_sql(ifade)
        _log(f"GRANT {etiket}: " + ("zaten var" if var else "verildi"))


def bootstrap_roles() -> None:
    """Rolü, RLS'i, politikaları ve GRANT'leri kurar; yeniden çalıştırılabilir."""
    if engine.dialect.name != "postgresql":
        raise SystemExit("bootstrap_roles.py PostgreSQL ister (DATABASE_URL).")
    kullanici, parola = uygulama_kimligi()
    with engine.begin() as conn:
        _tablolar_var_mi(conn)
        _rol_kur(conn, kullanici, parola)
        _rls_ac(conn)
        _politikalar(conn)
        _grantler(conn)


if __name__ == "__main__":
    bootstrap_roles()
    _log("tamam")
