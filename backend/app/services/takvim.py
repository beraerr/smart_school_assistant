"""2026-2027 eğitim ve öğretim yılı takvimi.

Kaynak: MEB 2026-2027 Eğitim ve Öğretim Yılı Çalışma Takvimi;
Diyanet 2027 dini günler takvimi.

Saf Python; dış bağımlılık yok. Tarihler kapsayıcıdır (başlangıç ve bitiş
günü dahil). Arife yarım günleri okul günü sayılır.
"""

from __future__ import annotations

from datetime import date, timedelta

DONEM_1_BASLANGIC = date(2026, 9, 14)
DONEM_1_BITIS = date(2027, 1, 22)
ARA_TATIL_1 = (date(2026, 11, 16), date(2026, 11, 20))
YARIYIL_TATILI = (date(2027, 1, 25), date(2027, 2, 5))
DONEM_2_BASLANGIC = date(2027, 2, 8)
DONEM_2_BITIS = date(2027, 6, 25)
ARA_TATIL_2 = (date(2027, 3, 8), date(2027, 3, 12))

# (başlangıç, bitiş, ad). Okul günlerine düşen resmî tatiller.
RESMI_TATILLER: tuple[tuple[date, date, str], ...] = (
    (date(2026, 10, 29), date(2026, 10, 29), "Cumhuriyet Bayramı"),
    (date(2027, 1, 1), date(2027, 1, 1), "Yılbaşı"),
    (date(2027, 3, 9), date(2027, 3, 11), "Ramazan Bayramı"),
    (date(2027, 4, 23), date(2027, 4, 23), "Ulusal Egemenlik ve Çocuk Bayramı"),
    (date(2027, 5, 1), date(2027, 5, 1), "Emek ve Dayanışma Günü"),
    (date(2027, 5, 16), date(2027, 5, 19), "Kurban Bayramı"),
    (date(2027, 5, 19), date(2027, 5, 19), "Atatürk'ü Anma, Gençlik ve Spor Bayramı"),
)

_DONEM_ADLARI: dict[str, tuple[str, str]] = {
    "okul_oncesi": ("Okul öncesi", "Before school year"),
    "donem_1": ("1. dönem", "First term"),
    "ara_tatil_1": ("1. dönem ara tatili", "First term mid-term break"),
    "yariyil": ("Yarıyıl tatili", "Semester break"),
    "donem_2": ("2. dönem", "Second term"),
    "ara_tatil_2": ("2. dönem ara tatili", "Second term mid-term break"),
    "yaz": ("Yaz tatili", "Summer break"),
}


def _aralikta(gun: date, aralik: tuple[date, date]) -> bool:
    return aralik[0] <= gun <= aralik[1]


def _resmi_tatil_mi(gun: date) -> bool:
    return any(baslangic <= gun <= bitis for baslangic, bitis, _ in RESMI_TATILLER)


def _donemde_mi(gun: date) -> bool:
    return (
        DONEM_1_BASLANGIC <= gun <= DONEM_1_BITIS
        or DONEM_2_BASLANGIC <= gun <= DONEM_2_BITIS
    )


def okul_gunu_mu(gun: date) -> bool:
    """Dönem içinde, hafta içi, ara tatil ve resmî tatil değilse True."""
    if not _donemde_mi(gun):
        return False
    if gun.weekday() >= 5:
        return False
    if _aralikta(gun, ARA_TATIL_1) or _aralikta(gun, ARA_TATIL_2):
        return False
    return not _resmi_tatil_mi(gun)


def okul_gunleri(baslangic: date, bitis: date) -> list[date]:
    """[baslangic, bitis] aralığındaki okul günleri, artan sırada."""
    gunler: list[date] = []
    gun = baslangic
    while gun <= bitis:
        if okul_gunu_mu(gun):
            gunler.append(gun)
        gun += timedelta(days=1)
    return gunler


def _durum(
    kod: str, baslangic: date | None, bitis: date | None
) -> dict[str, object]:
    ad_tr, ad_en = _DONEM_ADLARI[kod]
    return {
        "durum": kod,
        "ad_tr": ad_tr,
        "ad_en": ad_en,
        "baslangic": baslangic,
        "bitis": bitis,
    }


def donem_durumu(gun: date) -> dict[str, object]:
    """Günün takvimdeki durumu.

    Ara tatil kodu dönem kodundan önceliklidir. Hafta sonu veya resmî tatil
    dönem kodunu değiştirmez. İki dönem arasındaki hafta sonu günleri
    (2027-01-23/24 ve 2027-02-06/07) "yariyil" sayılır. baslangic ve bitis
    resmî aralığı verir; "okul_oncesi" için baslangic, "yaz" için bitis
    sınırsız olduğundan None döner.
    """
    if _aralikta(gun, ARA_TATIL_1):
        return _durum("ara_tatil_1", *ARA_TATIL_1)
    if _aralikta(gun, ARA_TATIL_2):
        return _durum("ara_tatil_2", *ARA_TATIL_2)
    if gun < DONEM_1_BASLANGIC:
        return _durum("okul_oncesi", None, DONEM_1_BASLANGIC - timedelta(days=1))
    if gun <= DONEM_1_BITIS:
        return _durum("donem_1", DONEM_1_BASLANGIC, DONEM_1_BITIS)
    if gun < DONEM_2_BASLANGIC:
        return _durum("yariyil", *YARIYIL_TATILI)
    if gun <= DONEM_2_BITIS:
        return _durum("donem_2", DONEM_2_BASLANGIC, DONEM_2_BITIS)
    return _durum("yaz", DONEM_2_BITIS + timedelta(days=1), None)


def risk_penceresi(gun: date) -> tuple[date, date] | None:
    """Risk hesabının not ve devamsızlık penceresi (başlangıç, bitiş), kapsayıcı.

    donem_1 ve ara_tatil_1: 1. dönem başı – gün. yariyil: 1. dönemin tamamı.
    donem_2 ve ara_tatil_2: 2. dönem başı – gün. yaz: 2. dönemin tamamı.
    okul_oncesi: pencere yok (None).
    """
    kod = donem_durumu(gun)["durum"]
    if kod in ("donem_1", "ara_tatil_1"):
        return DONEM_1_BASLANGIC, gun
    if kod == "yariyil":
        return DONEM_1_BASLANGIC, DONEM_1_BITIS
    if kod in ("donem_2", "ara_tatil_2"):
        return DONEM_2_BASLANGIC, gun
    if kod == "yaz":
        return DONEM_2_BASLANGIC, DONEM_2_BITIS
    return None


def _gun_ay(gun: date) -> str:
    aylar = (
        "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
        "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
    )
    return f"{gun.day} {aylar[gun.month - 1]} {gun.year}"


def _aralik_metni(aralik: tuple[date, date]) -> str:
    return f"{_gun_ay(aralik[0])} – {_gun_ay(aralik[1])}"


# RESMI_TATILLER adının İngilizcesi. Her tatil adı burada olmalıdır (test denetler).
_RESMI_TATIL_EN: dict[str, str] = {
    "Cumhuriyet Bayramı": "Republic Day",
    "Yılbaşı": "New Year's Day",
    "Ramazan Bayramı": "Ramadan Holiday",
    "Ulusal Egemenlik ve Çocuk Bayramı": "National Sovereignty and Children's Day",
    "Emek ve Dayanışma Günü": "Labour and Solidarity Day",
    "Kurban Bayramı": "Feast of Sacrifice Holiday",
    "Atatürk'ü Anma, Gençlik ve Spor Bayramı": (
        "Commemoration of Atatürk, Youth and Sports Day"
    ),
}


def _gun_ay_en(gun: date) -> str:
    aylar = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )
    return f"{aylar[gun.month - 1]} {gun.day}, {gun.year}"


def _aralik_metni_en(aralik: tuple[date, date]) -> str:
    return f"{_gun_ay_en(aralik[0])} – {_gun_ay_en(aralik[1])}"


def ozet_en() -> str:
    """ozet_tr ile aynı içeriğin kısa İngilizce özeti."""
    resmi = "; ".join(
        f"{_RESMI_TATIL_EN[ad]} "
        + (
            _gun_ay_en(baslangic)
            if baslangic == bitis
            else _aralik_metni_en((baslangic, bitis))
        )
        for baslangic, bitis, ad in RESMI_TATILLER
    )
    return (
        "2026-2027 school year calendar: "
        f"first term {_aralik_metni_en((DONEM_1_BASLANGIC, DONEM_1_BITIS))}; "
        f"first term mid-term break {_aralik_metni_en(ARA_TATIL_1)}; "
        f"semester break {_aralik_metni_en(YARIYIL_TATILI)}; "
        f"second term {_aralik_metni_en((DONEM_2_BASLANGIC, DONEM_2_BITIS))}; "
        f"second term mid-term break {_aralik_metni_en(ARA_TATIL_2)}. "
        f"Public holidays: {resmi}. "
        "School day: inside a term, a weekday, and not a mid-term break or public "
        "holiday; half-day eves count as school days."
    )


def ozet_tr() -> str:
    """Takvimin kısa Türkçe özeti."""
    resmi = "; ".join(
        f"{_gun_ay(baslangic)}"
        + ("" if baslangic == bitis else f" – {_gun_ay(bitis)}")
        + f" {ad}"
        for baslangic, bitis, ad in RESMI_TATILLER
    )
    return (
        "2026-2027 öğretim yılı takvimi: "
        f"1. dönem {_aralik_metni((DONEM_1_BASLANGIC, DONEM_1_BITIS))}; "
        f"1. dönem ara tatili {_aralik_metni(ARA_TATIL_1)}; "
        f"yarıyıl tatili {_aralik_metni(YARIYIL_TATILI)}; "
        f"2. dönem {_aralik_metni((DONEM_2_BASLANGIC, DONEM_2_BITIS))}; "
        f"2. dönem ara tatili {_aralik_metni(ARA_TATIL_2)}. "
        f"Resmî tatiller: {resmi}. "
        "Okul günü: dönem içinde, hafta içi, ara tatil ve resmî tatil dışındaki "
        "günlerdir; arife yarım günleri okul günüdür."
    )
