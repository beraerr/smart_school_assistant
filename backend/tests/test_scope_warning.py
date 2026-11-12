"""Kapsam uyarısı: veli/öğrenci, toplama fonksiyonu ve student_rank yokken eklenir."""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.api.query import KAPSAM_UYARISI
from backend.app.core.sql_safety import aggregates_without_rank
from backend.app.main import app
from backend.tests.sahte_model import bagla
from database.enable_rls import enable_rls

client = TestClient(app)

_ORTALAMA = "SELECT ROUND(AVG(grade)::numeric, 2) AS ortalama FROM grades"
_SIRA = (
    'SELECT "rank", total_students, ROUND(student_avg, 2) AS student_avg, '
    "ROUND(group_avg, 2) AS group_avg FROM student_rank('class', NULL)"
)
_DUZ = "SELECT subject, grade FROM grades"
_HESAPLAR = {
    "parent": ("parent1", "parent123"),
    "student": ("student1", "student123"),
    "teacher": ("teacher1", "teacher123"),
    "principal": ("principal", "admin123"),
}


@pytest.fixture(scope="module", autouse=True)
def _fonksiyon_kurulu() -> None:
    enable_rls()


@pytest.mark.parametrize(
    ("sql", "beklenen"),
    [
        ("SELECT AVG(grade) FROM grades", True),
        ("SELECT COUNT(*) FROM attendance WHERE status = 'absent'", True),
        ("SELECT SUM(total_absences) FROM students", True),
        ("SELECT MIN(grade), MAX(grade) FROM grades", True),
        ("SELECT subject FROM grades WHERE grade > (SELECT AVG(grade) FROM grades)", True),
        (_SIRA, False),
        ("SELECT MAX(group_avg) FROM student_rank('school', NULL)", False),
        (_DUZ, False),
        ("SELECT", False),
    ],
)
def test_toplama_tespiti(sql: str, beklenen: bool) -> None:
    assert aggregates_without_rank(sql) is beklenen


def _arac_sonucu(rol: str, sql: str, monkeypatch: pytest.MonkeyPatch) -> dict:
    istemci = bagla(monkeypatch, [[sql], "Tamam."])
    kullanici, parola = _HESAPLAR[rol]
    giris = client.post("/auth/login", json={"username": kullanici, "password": parola})
    response = client.post(
        "/query",
        headers={"Authorization": f"Bearer {giris.json()['access_token']}"},
        json={"question": "ortalama"},
    )
    assert response.status_code == 200
    assert "scope_warning" not in response.json()
    sonuclar = [
        parca
        for mesaj in istemci.cagrilar[1]["messages"]
        if isinstance(mesaj.get("content"), list)
        for parca in mesaj["content"]
        if parca.get("type") == "tool_result"
    ]
    assert len(sonuclar) == 1
    assert sonuclar[0]["is_error"] is False
    return json.loads(sonuclar[0]["content"])


@pytest.mark.parametrize("rol", ["parent", "student"])
def test_veli_ogrenci_toplamada_uyari(rol: str, monkeypatch: pytest.MonkeyPatch) -> None:
    govde = _arac_sonucu(rol, _ORTALAMA, monkeypatch)
    assert govde["scope_warning"] == KAPSAM_UYARISI


@pytest.mark.parametrize("rol", ["parent", "student"])
@pytest.mark.parametrize("sql", [_SIRA, _DUZ])
def test_veli_ogrenci_student_rank_veya_duz_sorguda_uyari_yok(
    rol: str, sql: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert "scope_warning" not in _arac_sonucu(rol, sql, monkeypatch)


@pytest.mark.parametrize("rol", ["teacher", "principal"])
def test_ogretmen_mudur_uyari_yok(rol: str, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "scope_warning" not in _arac_sonucu(rol, _ORTALAMA, monkeypatch)
