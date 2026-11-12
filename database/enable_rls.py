"""Zaman kapısını ve student_rank / class_teacher / class_rank fonksiyonlarını kurar.

Süper kullanıcıyla çalışır ve yeniden çalıştırılabilir. Proje kökünden:
    python database/enable_rls.py

Zaman kapısı: school_app için grades ve attendance SELECT erişimi, tarihi
oturumdaki app.today değerinden sonra olan satırları göstermez. Kapı, mevcut
izin veren SELECT politikalarının üstüne eklenen RESTRICTIVE politikalardır
(her ikisi de sağlanmalı); mevcut politika tanımlarına dokunulmaz. app.today
ayarlı değilse karşılaştırma NULL olur ve satır gelmez (kapalı başarısızlık).
Boş string de NULL sayılır; bağlantı havuzunda transaction sonrası ayar boş
string olarak kalabilir ve '' tarihe çevrilemez.

student_rank SECURITY DEFINER olduğu için sahibi (bu betiği çalıştıran süper
kullanıcı) adına okur ve satır güvenliğini aşar; bu yüzden aynı tarih
koşulunu kendi içinde taşır. Çağıran öğrenci kimliğini parametre olarak
veremez; kimlik yalnızca app.student_id oturum ayarından okunur ve sonuçta
yalnız o öğrencinin özet satırı döner. class_teacher not ve devamsızlığa
bakmadığı için tarih koşulu gerektirmez.

class_rank sınıf öğretmeni içindir: sınıf yalnızca app.class oturum ayarından
okunur, sonuçta yalnız o sınıfın satırı (sıra, sınıf sayısı, sınıf ortalaması,
okul ortalaması) döner; başka sınıfın adı veya ortalaması dönmez. student_rank
gibi aynı tarih koşulunu kendi içinde taşır.

Betik, tabloların, school_app rolünün ve izin veren politikaların (ilk RLS
kurulumu) var olduğunu varsayar.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text

from backend.app.core.database import engine

_GRADES_POLICY = "grades_zaman_kapisi"
_ATTENDANCE_POLICY = "attendance_zaman_kapisi"

# app.today ayarsız ya da boşsa NULL döner; satır elenir.
_BUGUN = "CAST(NULLIF(current_setting('app.today', true), '') AS date)"

# RESTRICTIVE politika, mevcut izin veren SELECT politikalarıyla (grades_via_students,
# attendance_via_students) VE ile birleşir: satır hem onlardan geçmeli hem de
# date <= app.today olmalı. Böylece mevcut politika tanımları yeniden yazılmaz.
_POLITIKALAR = [
    "ALTER TABLE grades ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE attendance ENABLE ROW LEVEL SECURITY",
    f"DROP POLICY IF EXISTS {_GRADES_POLICY} ON grades",
    f"DROP POLICY IF EXISTS {_ATTENDANCE_POLICY} ON attendance",
    f"""
    CREATE POLICY {_GRADES_POLICY} ON grades
    AS RESTRICTIVE
    FOR SELECT
    TO school_app
    USING (date <= {_BUGUN})
    """,
    f"""
    CREATE POLICY {_ATTENDANCE_POLICY} ON attendance
    AS RESTRICTIVE
    FOR SELECT
    TO school_app
    USING (date <= {_BUGUN})
    """,
]

_FONKSIYON = f"""
CREATE OR REPLACE FUNCTION public.student_rank(
    p_scope text,
    p_subject text DEFAULT NULL
)
RETURNS TABLE (
    scope text,
    subject text,
    "rank" integer,
    total_students integer,
    student_avg numeric,
    group_avg numeric
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    WITH params AS (
        SELECT
            CAST(NULLIF(current_setting('app.student_id', true), '') AS integer) AS me,
            current_setting('app.role', true) AS role,
            {_BUGUN} AS today,
            CASE
                WHEN p_scope IN ('class', 'school') THEN p_scope
                ELSE NULL
            END AS scope,
            NULLIF(btrim(p_subject), '') AS subject
    ),
    me_row AS (
        SELECT s.id, s.class_name
        FROM public.students AS s
        CROSS JOIN params AS p
        WHERE p.me IS NOT NULL
          AND p.role IN ('parent', 'student')
          AND p.scope IS NOT NULL
          AND s.id = p.me
    ),
    averages AS (
        SELECT
            s.id,
            CAST(AVG(g.grade) AS numeric) AS student_avg
        FROM public.students AS s
        CROSS JOIN params AS p
        JOIN me_row AS m ON TRUE
        LEFT JOIN public.grades AS g
            ON g.student_id = s.id
           AND g.date <= p.today
           AND (
                p.subject IS NULL
                OR lower(g.subject) = lower(p.subject)
           )
        WHERE p.scope = 'school'
           OR s.class_name = m.class_name
        GROUP BY s.id
    ),
    ranked AS (
        SELECT
            a.id,
            a.student_avg,
            RANK() OVER (ORDER BY a.student_avg DESC NULLS LAST) AS placement,
            COUNT(*) OVER () AS total_students,
            AVG(a.student_avg) OVER () AS group_avg
        FROM averages AS a
    )
    SELECT
        p.scope,
        p.subject,
        CAST(r.placement AS integer),
        CAST(r.total_students AS integer),
        r.student_avg,
        r.group_avg
    FROM ranked AS r
    CROSS JOIN params AS p
    WHERE r.id = p.me
$fn$
"""


_SINIF_OGRETMENI = """
CREATE OR REPLACE FUNCTION public.class_teacher()
RETURNS TABLE (name text)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    SELECT t.name
    FROM public.teachers AS t
    JOIN public.students AS s
        ON s.class_name = t.class_name
    WHERE current_setting('app.role', true) IN ('parent', 'student')
      AND s.id = CAST(NULLIF(current_setting('app.student_id', true), '') AS integer)
$fn$
"""


_SINIF_SIRASI = f"""
CREATE OR REPLACE FUNCTION public.class_rank(
    p_subject text DEFAULT NULL
)
RETURNS TABLE (
    class_name text,
    subject text,
    "rank" integer,
    total_classes integer,
    class_avg numeric,
    school_avg numeric
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    WITH params AS (
        SELECT
            NULLIF(current_setting('app.class', true), '') AS my_class,
            current_setting('app.role', true) AS role,
            {_BUGUN} AS today,
            NULLIF(btrim(p_subject), '') AS subject
    ),
    scoped AS (
        SELECT s.class_name, g.grade
        FROM public.students AS s
        CROSS JOIN params AS p
        LEFT JOIN public.grades AS g
            ON g.student_id = s.id
           AND g.date <= p.today
           AND (
                p.subject IS NULL
                OR lower(g.subject) = lower(p.subject)
           )
        WHERE p.role = 'teacher'
          AND p.my_class IS NOT NULL
          AND s.class_name IS NOT NULL
    ),
    averages AS (
        SELECT sc.class_name, CAST(AVG(sc.grade) AS numeric) AS class_avg
        FROM scoped AS sc
        GROUP BY sc.class_name
    ),
    ranked AS (
        SELECT
            a.class_name,
            a.class_avg,
            RANK() OVER (ORDER BY a.class_avg DESC NULLS LAST) AS placement,
            COUNT(*) OVER () AS total_classes
        FROM averages AS a
    ),
    school AS (
        SELECT CAST(AVG(sc.grade) AS numeric) AS school_avg
        FROM scoped AS sc
    )
    SELECT
        r.class_name,
        p.subject,
        CAST(r.placement AS integer),
        CAST(r.total_classes AS integer),
        r.class_avg,
        sc.school_avg
    FROM ranked AS r
    CROSS JOIN params AS p
    CROSS JOIN school AS sc
    WHERE r.class_name = p.my_class
$fn$
"""


def _yetki(conn, imza: str) -> None:
    conn.execute(text(f"REVOKE ALL ON FUNCTION {imza} FROM PUBLIC"))
    conn.execute(text(f"GRANT EXECUTE ON FUNCTION {imza} TO school_app"))


def enable_rls() -> None:
    """Zaman kapılı politikaları ve fonksiyonları kurar, yetkileri yeniler."""
    if engine.dialect.name != "postgresql":
        raise SystemExit("enable_rls.py PostgreSQL ister (DATABASE_URL).")

    with engine.begin() as conn:
        for ifade in _POLITIKALAR:
            conn.execute(text(ifade))
        conn.execute(text(_FONKSIYON))
        conn.execute(text(_SINIF_OGRETMENI))
        conn.execute(text(_SINIF_SIRASI))
        _yetki(conn, "public.student_rank(text, text)")
        _yetki(conn, "public.class_teacher()")
        _yetki(conn, "public.class_rank(text)")


if __name__ == "__main__":
    enable_rls()
    print(
        "grades ve attendance politikaları zaman kapılı (app.today). "
        "student_rank, class_teacher ve class_rank kuruldu. EXECUTE yalnızca school_app rolünde."
    )
