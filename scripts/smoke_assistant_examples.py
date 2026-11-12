"""Her rolün örnek sorularını çalışan asistana sorar.

Pytest toplamaz. Backend ayaktayken elle çalıştırın:

    .venv/bin/python scripts/smoke_assistant_examples.py
    .venv/bin/python scripts/smoke_assistant_examples.py --tam
    .venv/bin/python scripts/smoke_assistant_examples.py --rol teacher1 --soru "soru metni"
"""

import argparse
import os
import sys

import requests

BASE = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
_TIMEOUT = 180
_HESAPLAR = (
    ("principal", "admin123"),
    ("teacher1", "teacher123"),
    ("parent1", "parent123"),
    ("student1", "student123"),
)
_ROLLER = tuple(hesap[0] for hesap in _HESAPLAR)


def _argumanlar(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Örnek soruları çalışan asistana sorar.")
    parser.add_argument(
        "--tam",
        action="store_true",
        help="Her soru için tam cevap, grounding_retry ve bütün SQL.",
    )
    parser.add_argument(
        "--soru",
        help="Yalnızca bu soruyu, örneklerinde geçen rollerde çalıştır.",
    )
    parser.add_argument(
        "--rol",
        choices=_ROLLER,
        help="Yalnızca bu hesap.",
    )
    return parser.parse_args(argv)


def _giris(username: str, password: str) -> str:
    response = requests.post(
        f"{BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def _ornekler(token: str) -> list[str]:
    response = requests.get(
        f"{BASE}/assistant/examples",
        headers={"Authorization": f"Bearer {token}"},
        params={"lang": "tr"},
        timeout=30,
    )
    response.raise_for_status()
    gelen = response.json()
    if not isinstance(gelen, list):
        return []
    cikti: list[str] = []
    for oge in gelen:
        if not isinstance(oge, dict):
            continue
        soru = oge.get("question")
        if isinstance(soru, str) and soru.strip():
            cikti.append(soru)
    return cikti


def _sql_listesi(govde: dict) -> list[str]:
    sql = govde.get("sql") or []
    if isinstance(sql, list):
        return [str(parca) for parca in sql]
    if sql:
        return [str(sql)]
    return []


def _sor(token: str, soru: str) -> tuple[str, list[str], bool, str]:
    try:
        response = requests.post(
            f"{BASE}/query",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": soru, "lang": "tr", "history": []},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as exc:
        return "evet", [], False, str(exc)
    if response.status_code != 200:
        return "evet", [], False, response.text
    govde = response.json()
    if not isinstance(govde, dict):
        return "evet", [], False, response.text
    return (
        "hayır",
        _sql_listesi(govde),
        bool(govde.get("grounding_retry")),
        str(govde.get("answer") or ""),
    )


def _yaz(satirlar: list[tuple[str, str, str, str, str, str]]) -> None:
    basliklar = ("rol", "soru", "hata", "ek_tur", "cevap", "sql")
    tavan = (12, 72, 5, 6, 250, 72)
    genislikler = [len(baslik) for baslik in basliklar]
    for satir in satirlar:
        for indeks, hucre in enumerate(satir):
            genislikler[indeks] = max(
                genislikler[indeks], min(len(hucre), tavan[indeks])
            )
    cizgi = "-+-".join("-" * genislik for genislik in genislikler)

    def _satir(hucreler: tuple[str, ...]) -> str:
        parcalar = []
        for hucre, genislik in zip(hucreler, genislikler, strict=True):
            goster = hucre if len(hucre) <= genislik else hucre[: genislik - 1] + "…"
            parcalar.append(goster.ljust(genislik))
        return " | ".join(parcalar)

    print(_satir(basliklar))
    print(cizgi)
    for satir in satirlar:
        print(_satir(satir))


def _tam_yaz(kayitlar: list[dict]) -> None:
    for kayit in kayitlar:
        print(f"rol: {kayit['rol']}")
        print(f"soru: {kayit['soru']}")
        print(f"hata: {kayit['hata']}")
        print(f"grounding_retry: {'true' if kayit['grounding_retry'] else 'false'}")
        print("cevap:")
        print(kayit["cevap"] if kayit["cevap"] else "-")
        print("sql:")
        sqller = kayit["sqller"]
        if not sqller:
            print("-")
        else:
            for indeks, sql in enumerate(sqller, start=1):
                print(f"{indeks}.")
                print(sql)
        print("---")


def main() -> None:
    args = _argumanlar()
    istenen = args.soru.strip() if isinstance(args.soru, str) else None
    hesaplar = _HESAPLAR
    if args.rol:
        hesaplar = tuple(hesap for hesap in _HESAPLAR if hesap[0] == args.rol)
    kayitlar: list[dict] = []
    for username, password in hesaplar:
        token = _giris(username, password)
        for soru in _ornekler(token):
            if istenen is not None and soru != istenen:
                continue
            print(
                f"... {username}: {soru}",
                file=sys.stderr if args.tam else sys.stdout,
                flush=True,
            )
            hata, sqller, ek_tur, cevap = _sor(token, soru)
            kayitlar.append(
                {
                    "rol": username,
                    "soru": soru,
                    "hata": hata,
                    "ek_tur": "evet" if ek_tur else "hayır",
                    "cevap": cevap,
                    "sqller": sqller,
                    "grounding_retry": ek_tur,
                }
            )
    if args.tam:
        print()
        _tam_yaz(kayitlar)
        return
    satirlar = []
    for kayit in kayitlar:
        sql = " | ".join(parca.replace("\n", " ") for parca in kayit["sqller"]) or "-"
        satirlar.append(
            (
                kayit["rol"],
                kayit["soru"],
                kayit["hata"],
                kayit["ek_tur"],
                "-",
                sql,
            )
        )
    print()
    _yaz(satirlar)


if __name__ == "__main__":
    main()
