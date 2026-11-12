"""Eval soru dosyası grupları ve çok turlu senaryoları içerir."""

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_DOSYA = _PROJECT_ROOT / "eval" / "questions.json"
_GRUPLAR = {
    "grades",
    "attendance",
    "ranking",
    "teacher_school",
    "comment",
    "chat",
    "short",
    "spelling",
    "time",
    "security",
    "missing",
    "policy",
    "support",
    "followup",
}


def test_soru_dosyasi_gruplari() -> None:
    sorular = json.loads(_DOSYA.read_text(encoding="utf-8"))
    assert 55 <= len(sorular) <= 70
    assert len({soru["id"] for soru in sorular}) == len(sorular)
    gercekler = [soru for soru in sorular if soru.get("truth_sql")]
    assert gercekler and all(soru.get("must_contain_truth") for soru in gercekler)
    assert any("50" in (soru.get("must_contain") or []) for soru in sorular)
    assert {soru["group"] for soru in sorular} == _GRUPLAR
    assert any(soru.get("turns") for soru in sorular)
    assert any(soru.get("check") == "missing" for soru in sorular)
    assert any(soru.get("check") == "security" for soru in sorular)
    for soru in sorular:
        assert soru["role"] in {"teacher", "principal", "parent", "student"}
        if soru.get("turns"):
            assert all(isinstance(adim, str) and adim for adim in soru["turns"])
        else:
            assert soru["question"]
        if soru["role"] == "student":
            yasak = soru.get("must_not_contain") or []
            assert "çocuğunuz" in yasak
            assert "velisi" in yasak


def test_s3_ilk_cevapta_veri_kullanilmaz() -> None:
    sorular = json.loads(_DOSYA.read_text(encoding="utf-8"))
    s3 = next(soru for soru in sorular if soru["id"] == "s3")
    yasak = s3["must_not_contain"]
    assert "devamsızl" not in yasak
    for parca in (
        "veremem",
        "bilgi veremem",
        "nedeni olabilir",
        "yol açıyor",
        "yüzünden",
        "sebep",
        "isteksizli",
        "soğum",
        "ortalama",
    ):
        assert parca in yasak
    assert s3["no_sql_first"] is True
    assert s3["no_digits_first"] is True
    assert s3["comment"] == "Asıl kural ilk cevapta veri kullanılmamasıdır."


def test_s3_rakam_ve_sorgu_kontrolleri() -> None:
    from eval.run_eval import _kontroller

    soru = {
        "no_sql_first": True,
        "no_digits_first": True,
        "must_not_contain": ["nedeni olabilir", "yüzünden"],
    }
    temiz, _ = _kontroller(
        soru,
        [(200, {"answer": "Anlıyorum, konuşmayı deneyebilirsin.", "sql": []})],
        None,
        [],
    )
    assert temiz == []

    rakam, _ = _kontroller(
        soru,
        [(200, {"answer": "Anlıyorum, 2 öneri var.", "sql": []})],
        None,
        [],
    )
    assert "ilk cevapta rakam var" in rakam

    sorgu, _ = _kontroller(
        soru,
        [(200, {"answer": "Anlıyorum.", "sql": ["SELECT 1"]})],
        None,
        [],
    )
    assert "ilk cevapta sorgu çalıştı" in sorgu
    assert "ilk cevapta rakam var" not in sorgu
