"""validate_select_only: tek SELECT, izinli tablolar, takma ad."""

import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.core.sql_safety import validate_select_only


def test_gecerli_select_kabul() -> None:
    validate_select_only("SELECT id, name FROM students")


def test_drop_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("DROP TABLE students")


def test_coklu_ifade_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM students; DROP TABLE students")


def test_users_referansi_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM users")


def test_teachers_referansi_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT id FROM teachers")


def test_student_rank_kabul() -> None:
    validate_select_only("SELECT * FROM student_rank('class', NULL)")


def test_class_teacher_kabul() -> None:
    validate_select_only("SELECT name FROM class_teacher()")


def test_pg_ls_dir_reddedilir() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT * FROM pg_ls_dir('.')")


def test_toplama_ve_pencere_kabul() -> None:
    validate_select_only(
        """
        SELECT COUNT(*) AS total, ROUND(AVG(g.grade), 2), MIN(g.grade), MAX(g.grade),
               SUM(g.grade), LOWER(s.name), UPPER(s.name), COALESCE(s.name, ''),
               EXTRACT(YEAR FROM g.date), DATE_TRUNC('month', g.date),
               NOW(), CURRENT_DATE,
               RANK() OVER (ORDER BY g.grade),
               DENSE_RANK() OVER (ORDER BY g.grade),
               ROW_NUMBER() OVER (ORDER BY g.grade)
        FROM students AS s
        JOIN grades g ON g.student_id = s.id
        """
    )


def test_lag_ile_onceki_aya_fark_kabul() -> None:
    validate_select_only(
        """
        SELECT DATE_TRUNC('month', date) AS ay,
               ROUND(AVG(grade)::numeric, 2) AS ortalama,
               ROUND((AVG(grade) - LAG(AVG(grade)) OVER (ORDER BY DATE_TRUNC('month', date)))
                     ::numeric, 2) AS onceki_aya_fark
        FROM grades
        GROUP BY DATE_TRUNC('month', date)
        ORDER BY ay
        """
    )
    validate_select_only("SELECT LAG(grade) OVER (ORDER BY date) FROM grades")


@pytest.mark.parametrize(
    "sql",
    [
        # LAG dışındaki pencere fonksiyonları izin listesine eklenmedi.
        "SELECT LEAD(grade) OVER (ORDER BY date) FROM grades",
        "SELECT NTILE(4) OVER (ORDER BY grade) FROM grades",
        "SELECT FIRST_VALUE(grade) OVER (ORDER BY date) FROM grades",
    ],
)
def test_lag_disi_pencere_fonksiyonu_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_select_only(sql)


def test_lag_tablo_kurallarini_gevsetmez() -> None:
    with pytest.raises(ValueError):
        validate_select_only("SELECT LAG(id) OVER (ORDER BY id) FROM users")


def test_tur_donusumu_kabul() -> None:
    validate_select_only("SELECT id::text, CAST(id AS integer) FROM students")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT set_config('app.role', 'principal', true)",
        "WITH x AS (SELECT set_config('app.role', 'principal', true)) "
        "SELECT s.* FROM students s, x",
        "SELECT s.* FROM students s WHERE (SELECT set_config('app.role', 'principal', true)) IS NOT NULL",
        "SELECT current_setting('app.role', true)",
        "SELECT pg_sleep(1)",
        "SELECT lo_import('/etc/passwd')",
        "SELECT dblink('host=localhost', 'SELECT 1')",
        "SELECT student_rank('class', NULL)",
        "SELECT class_teacher()",
    ],
)
def test_izin_listesi_disi_fonksiyon_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_select_only(sql)


def test_join_ve_takma_ad_kabul() -> None:
    validate_select_only(
        """
        SELECT s.name, g.grade
        FROM students AS s
        JOIN grades g ON g.student_id = s.id
        """
    )


# --- Kalıp matrisi: yazım sırasında (düzeltmeden önce) AND, OR, CASE ve NULLIF reddediliyordu ---
# Nedeni: sqlglot And/Or/Case/If düğümlerini exp.Func alt sınıfı yapar; fonksiyon izin listesi
# kontrolü bunları "and", "or", "case" adlı fonksiyon sayıyordu. NULLIF izin listesinde yoktu.
# Diğer kalıplar Func olmadığı ya da listede olduğu için zaten geçiyordu.
_KALIPLAR = [
    ("and", "SELECT * FROM grades WHERE date >= DATE '2026-09-28' AND date <= DATE '2026-10-23'"),
    ("or", "SELECT * FROM grades WHERE grade < 50 OR subject = 'Matematik'"),
    ("not", "SELECT * FROM grades WHERE NOT grade < 50"),
    ("case_sum", "SELECT SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) FROM attendance"),
    (
        "case_ay_adi",
        "SELECT CASE WHEN EXTRACT(MONTH FROM date) = 9 THEN 'Eylül' ELSE 'Ekim' END AS ay, "
        "AVG(grade) FROM grades GROUP BY 1",
    ),
    ("between", "SELECT * FROM grades WHERE grade BETWEEN 50 AND 70"),
    ("in_liste", "SELECT * FROM grades WHERE subject IN ('Matematik', 'Fizik')"),
    ("is_null", "SELECT * FROM grades WHERE grade IS NULL"),
    ("is_not_null", "SELECT * FROM grades WHERE grade IS NOT NULL"),
    ("like", "SELECT * FROM students WHERE name LIKE 'A%'"),
    ("ilike", "SELECT * FROM students WHERE name ILIKE 'a%'"),
    ("coalesce", "SELECT COALESCE(grade, 0) FROM grades"),
    ("nullif", "SELECT NULLIF(grade, 0) FROM grades"),
    ("date_literali", "SELECT * FROM grades WHERE date = DATE '2026-11-04'"),
    ("cift_iki_nokta_date", "SELECT g.date::date FROM grades g"),
    ("cast", "SELECT CAST(grade AS numeric) FROM grades"),
    ("interval", "SELECT * FROM grades WHERE date >= DATE '2026-11-04' - INTERVAL '7 days'"),
    ("extract", "SELECT EXTRACT(MONTH FROM date) FROM grades"),
    ("date_trunc", "SELECT DATE_TRUNC('month', date) FROM grades"),
    ("count_filter", "SELECT COUNT(*) FILTER (WHERE status = 'absent') FROM attendance"),
    ("lag_over", "SELECT LAG(grade) OVER (ORDER BY date) FROM grades"),
    ("round", "SELECT ROUND(AVG(grade)::numeric, 2) FROM grades"),
    ("toplamalar", "SELECT AVG(grade), SUM(grade), COUNT(*), MIN(grade), MAX(grade) FROM grades"),
    (
        "alt_sorgu_in",
        "SELECT * FROM grades WHERE student_id IN (SELECT id FROM students WHERE class_name = '9-A')",
    ),
    (
        "with_cte_govdesi_izinli_tablo",
        "WITH x AS (SELECT id FROM students) SELECT 1",
    ),
]


@pytest.mark.parametrize(("ad", "sql"), _KALIPLAR, ids=[ad for ad, _ in _KALIPLAR])
def test_kalip_matrisi_kabul(ad: str, sql: str) -> None:
    validate_select_only(sql)


def test_cte_adina_basvuru_mevcut_davranis_reddedilir() -> None:
    """Mevcut davranış belgesi: CTE adı tablo izin listesinde olmadığı için reddedilir.

    Bu görevde değiştirilmedi (tablo izin listesini gevşetmek kapsam dışı); bkz. rapor.
    """
    with pytest.raises(ValueError, match="İzin verilmeyen tablo: x"):
        validate_select_only("WITH x AS (SELECT id FROM students) SELECT * FROM x")


# --- Operatör düğümleri çocuk düğümlerdeki gerçek fonksiyon çağrılarını gizlemez ---


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM grades WHERE grade > 1 AND pg_sleep(1) IS NULL",
        "SELECT * FROM grades WHERE grade > 1 OR pg_sleep(1) IS NULL",
        "SELECT CASE WHEN pg_sleep(1) IS NULL THEN 1 ELSE 0 END FROM grades",
        "SELECT CASE WHEN grade > 1 THEN pg_sleep(1) END FROM grades",
        "SELECT * FROM grades WHERE NOT (pg_sleep(1) IS NULL)",
        "SELECT * FROM grades WHERE grade BETWEEN 1 AND length(pg_read_file('/etc/passwd'))",
        "SELECT * FROM grades WHERE grade IN (1, version())",
        "SELECT * FROM students WHERE name LIKE pg_read_file('/etc/passwd')",
    ],
)
def test_operator_icindeki_tehlikeli_fonksiyon_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError, match="İzin verilmeyen fonksiyon"):
        validate_select_only(sql)


@pytest.mark.parametrize(
    "fonksiyon",
    [
        "pg_sleep(1)",
        "pg_read_file('/etc/passwd')",
        "pg_read_binary_file('/etc/passwd')",
        "pg_ls_dir('.')",
        "lo_import('/etc/passwd')",
        "dblink('host=localhost', 'SELECT 1')",
        "set_config('app.role', 'principal', true)",
        "current_setting('app.role', true)",
        "version()",
        "txid_current()",
        "pg_terminate_backend(1)",
    ],
)
def test_tehlikeli_fonksiyonlar_reddedilmeye_devam_eder(fonksiyon: str) -> None:
    with pytest.raises(ValueError, match="İzin verilmeyen fonksiyon"):
        validate_select_only(f"SELECT {fonksiyon}")
    with pytest.raises(ValueError):
        validate_select_only(f"SELECT * FROM grades WHERE {fonksiyon} IS NOT NULL")


# --- Denetim 6.2 / 6.3: yazma, INTO, kilit ve şema nitelikli tablolar ---


@pytest.mark.parametrize(
    "sql",
    [
        "WITH x AS (DELETE FROM students RETURNING id) SELECT 1",
        "WITH x AS (UPDATE grades SET grade = 100 RETURNING id) SELECT * FROM x",
        "WITH x AS (INSERT INTO grades (student_id, grade) VALUES (1, 100) RETURNING id) SELECT 1",
        "SELECT * INTO yeni FROM students",
    ],
)
def test_agacin_herhangi_yerindeki_yazma_dugumu_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError, match="İzin verilmeyen ifade"):
        validate_select_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM students FOR UPDATE",
        "SELECT * FROM students FOR SHARE",
        "SELECT * FROM students WHERE id IN (SELECT id FROM students FOR UPDATE)",
    ],
)
def test_satir_kilidi_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError, match="İzin verilmeyen ifade"):
        validate_select_only(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pg_catalog.pg_authid",
        "SELECT * FROM information_schema.tables",
        # Tablo adı izinli, şema değil: yalnız ada bakan eski kontrol bunu geçirirdi.
        "SELECT * FROM pg_catalog.students",
        "SELECT * FROM information_schema.grades",
        "SELECT * FROM postgres.public.students",
        "SELECT * FROM pg_catalog.pg_ls_dir('.')",
    ],
)
def test_baska_sema_reddedilir(sql: str) -> None:
    with pytest.raises(ValueError):
        validate_select_only(sql)


def test_sema_niteleyicisi_mesaji_sema_adini_verir() -> None:
    with pytest.raises(ValueError, match="İzin verilmeyen şema: pg_catalog"):
        validate_select_only("SELECT * FROM pg_catalog.students")


def test_public_semasi_kabul() -> None:
    validate_select_only("SELECT * FROM public.students")
    validate_select_only("SELECT s.name FROM public.students AS s JOIN public.grades g ON g.student_id = s.id")
