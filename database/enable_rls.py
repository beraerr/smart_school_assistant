"""student_rank fonksiyonunu kurar. Süper kullanıcıyla çalışır ve yeniden çalıştırılabilir.

Proje kökünden:
    python database/enable_rls.py

Fonksiyon SECURITY DEFINER olduğu için sahibi (bu betiği çalıştıran süper
kullanıcı) adına okur ve satır güvenliğini aşar. Çağıran öğrenci kimliğini
parametre olarak veremez; kimlik yalnızca app.student_id oturum ayarından
okunur ve sonuçta yalnız o öğrencinin özet satırı döner.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy import text

from backend.app.core.database import engine

_FONKSIYON = """
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
            RANK() OVER (ORDER BY a.student_avg DESC) AS placement,
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


def enable_rls() -> None:
    """student_rank fonksiyonunu oluşturur veya değiştirir, yetkileri yeniler."""
    if engine.dialect.name != "postgresql":
        raise SystemExit("enable_rls.py PostgreSQL ister (DATABASE_URL).")

    with engine.begin() as conn:
        conn.execute(text(_FONKSIYON))
        conn.execute(
            text(
                "REVOKE ALL ON FUNCTION public.student_rank(text, text) FROM PUBLIC"
            )
        )
        conn.execute(
            text(
                "GRANT EXECUTE ON FUNCTION public.student_rank(text, text) TO school_app"
            )
        )


if __name__ == "__main__":
    enable_rls()
    print("student_rank kuruldu. EXECUTE yalnızca school_app rolünde.")
