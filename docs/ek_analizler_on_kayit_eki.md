# Ön kayıt eki: grup ataması

**Tarih:** 5 Kasım 2026. Bu ek, ek analizler koşulmadan **önce** yazıldı. `ek_analizler_on_kayit.md` dosyası değiştirilmedi; bu dosya onun E1 bölümündeki "her sütun tam olarak bir gruba" kuralını sütun düzeyinde açıklar.

## Genel kural

Bir sütunun grubu, sütunun türediği veriye göre belirlenir:

- Puan değeri → NOT.
- Ödev kayıtlarından türeyen sayaç veya zamanlama → TESLİM.
- `vle_*` → ETKİNLİK.
- Kayıt tarihi → KAYIT.

Bu kurala rağmen grubu belirsiz kalan bir sütun olursa koşu durur; grup tahmin edilmez ve sonuca göre değiştirilmez.

## GENERAL sütunlarının grup tablosu

| sütun | grup | gerekçe |
| --- | --- | --- |
| score_mean | NOT | Teslimlerin ağırlıksız ortalama puanıdır. |
| score_weighted_mean | NOT | Teslimlerin ağırlıklı ortalama puanıdır. |
| n_expected | TESLİM | Ödev kayıtlarından türeyen, beklenen ödev sayısıdır. |
| n_submitted | TESLİM | Ödev kayıtlarından türeyen, teslim sayısıdır. |
| n_unsubmitted | TESLİM | Beklenen ile teslim edilen ödev sayısının farkıdır. |
| delay_mean | TESLİM | Teslim tarihi ile ödev tarihi arasındaki zamanlama farkıdır. |
| n_banked | TESLİM | Devralınan (is_banked = 1) teslim kayıtlarının sayacıdır. |
| vle_clicks | ETKİNLİK | Sanal öğrenme ortamı toplam tıklamasıdır. |
| vle_active_days | ETKİNLİK | Sanal öğrenme ortamında etkin gün sayısıdır. |
| vle_days_to_cutoff | ETKİNLİK | Son sanal öğrenme ortamı etkinliğinden kesim gününe kalan süredir. |
| vle_click_forumng | ETKİNLİK | Sanal öğrenme ortamı forumng tıklama toplamıdır. |
| vle_click_subpage | ETKİNLİK | Sanal öğrenme ortamı subpage tıklama toplamıdır. |
| vle_click_oucontent | ETKİNLİK | Sanal öğrenme ortamı oucontent tıklama toplamıdır. |
| vle_click_homepage | ETKİNLİK | Sanal öğrenme ortamı homepage tıklama toplamıdır. |
| vle_click_resource | ETKİNLİK | Sanal öğrenme ortamı resource tıklama toplamıdır. |
| date_registration | KAYIT | Kayıt tarihidir. |

## Karar kuralları

- **Tuttu / tutmadı / belirsiz:** Bir beklenti, doğrulama (2014B) **ve** test (2014J) dönemlerinin ikisinde de ölçütü sağlarsa "tuttu", ikisinde de sağlamazsa "tutmadı", dönemler ayrışırsa "belirsiz" sayılır. Tek dönem karar vermez. B7 de aynı kuralla, doğrulama ve test bayraklarıyla karara bağlanır.
- **GGG dışlaması:** GGG yalnız doğrulama (2014B) ve test (2014J) dönemlerinde dışarıda kalır; 2013J eğitim satırlarında kalır (Hafta 11 ile aynı).
- **B5:** "fark", işaretli GENERAL − ETKİNLİK farkıdır.
- **Referans hedef:** GGG dışlaması nedeniyle `model_metrics.json` değerlerinden farklı olabilir.
- **B1–B6** hgb modeliyle hesaplanır.

## Notlar

- NOT_TESLİM setinde KAYIT yok; B3'teki fark ETKİNLİK ile birlikte KAYIT'ı da kapsar.
- `n_banked` bir puan değil, devralınan teslim sayısıdır; dolaylı olarak önceki deneme bilgisini taşır.
- Setler: yalnız NOT, yalnız TESLİM, yalnız ETKİNLİK, NOT + TESLİM, GENERAL. KAYIT yalnız GENERAL içindedir; NOT + TESLİM setinde yoktur.
- `ek.py` içindeki grup sözlüğü bu tabloyla birebir aynıdır; bir test bunu sınar.
