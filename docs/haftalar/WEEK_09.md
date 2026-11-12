# Hafta 9 — Veri Bilimi II: OULAD

## Özet
Ders bağlamı hipotezini test edebilmek için Open University Learning Analytics Dataset (OULAD) projeye eklendi. Veri indirildi ve doğrulandı, 60. gün kesimiyle erken uyarı örneklemi kuruldu, genel ve ders geçmişi özellikleri üretildi, sızıntısız zamansal bölme yapıldı ve `02_oulad_eda` notebook'u (TR/EN) hazırlandı. Bu hafta model eğitilmedi; karşılaştırma Hafta 10'da yapılacak.

## Yapılanlar
- **9a — Veri:** `data_science/oulad/` paketi (`download`, `load`, `vle`, `validate`). Arşivin sha256 değeri sabitlendi: `f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4`. `studentVle` parçalı okunup `(modül, sunum, öğrenci, gün, etkinlik türü)` düzeyinde günlük özete indirildi (`student_vle_daily.parquet`).
- **9b — Özellikler:** `dataset.py`. Birim `(code_module, code_presentation, id_student)`. Hedef `at_risk = final_result ∈ {Fail, Withdrawn}`. `CUTOFF_DAY = 60`. Çıktı `features_cutoff60.parquet` (26 sütun) ve `feature_list.md`.
- **9c — Notebook:** `notebooks/02_oulad_eda.ipynb`, `02_oulad_eda_eng.ipynb` ve `notebooks/html/` altındaki HTML çıktıları.

## Veri
| Tablo | Satır | Not |
|---|---|---|
| studentInfo | 32.593 | Anahtar tekil; imd_band 1.111 eksik |
| studentRegistration | 32.593 | date_registration 45, date_unregistration 22.521 boş |
| assessments | 206 | date 11 eksik |
| studentAssessment | 173.912 | score 173 eksik |
| vle | 6.364 | week_from/week_to 5.243 boş |
| courses | 22 | — |
| studentVle | 10.655.280 | Parçalı okundu |

Parçalı özet doğrulaması: ham tablo ile günlük özette satır sayısı (10.655.280) ve toplam tıklama (39.605.099) birebir aynı.

## Örneklem ve kurallar
- Yalnızca tarihi ve teslimi 60. güne kadar olan ödevler; final sınavı (`Exam`) hariç. Tıklamalar 60. güne kadar.
- 60. günden önce kaydını silenler çıkarıldı: 32.593 → 26.403 (6.190 kayıt). Sonra silenler örneklemde kaldı ve `at_risk = 1`.
- Kullanılmayan sütunlar: sosyokültürel sütunlar (`SOCIO_COLUMNS`), `num_of_prev_attempts`, `studied_credits`.
- Ders geçmişi: sunum P için yalnızca aynı modülün P'den kesinlikle önceki sunumları. Ödev eşleme anahtarı `(modül, tür, sunum içi sıra no)`. Geçmiş yoksa `has_history = 0` ve geçmiş sütunları NaN kalır.

## Bölme
| Bölüm | Sunumlar | Satır | at_risk | Geçmişi var |
|---|---|---|---|---|
| history | 2013B | 3.927 | %46,7 | %0,0 |
| train | 2013J + 2014B | 13.639 | %42,6 | %74,1 |
| test | 2014J | 8.837 | %38,3 | %100,0 |

## Ders bağlamı (betimsel)
- Tüm kayıtlarda Fail + Withdrawn oranı modüller arasında %29,0 (AAA) ile %62,2 (CCC) arasında değişiyor. Aynı modülün sunumları arasındaki fark en fazla 6,5 puan (EEE).
- Örneklemde en düşük oran AAA 2013J (%23,4), en yüksek DDD 2013B (%52,6).
- Bu, ders geçmişinin bilgi taşıdığına dair betimsel bir işarettir; kanıt değildir. Kanıt Hafta 10'daki model karşılaştırmasından gelecek.

## Eksik değer tutarlılığı
- `hist_module_risk_rate` 7.465 eksik = history 3.927 + geçmişsiz train 3.538.
- `hist_slot_mean` 8.952 = 7.465 + 1.487 (veri notu 1).
- `score_weighted_mean` 4.172 = `score_mean` 3.995 + 177 (veri notu 2).
- Diğerleri: `score_vs_hist` 10.046, `vle_days_to_cutoff` 564, `date_registration` 7.

## Veri notları (hata değil)
1. **GGG 2014B / 2014J:** 1.487 satırın tamamında `n_expected = 0` (790 + 697). Bu sunumlarda 60. güne kadar notlu ödev yok. Kesim anında yalnızca etkinlik sinyali var.
2. **BBB 2014J:** 60. güne kadar ağırlığı 0 olan bir TMA var. Yalnızca onu teslim eden 177 öğrencide ağırlıklı ortalama tanımsız (NaN doğru).

## Hata kayıtları
**Hata 1 — test ortamı**
- Belirti: pytest toplama aşamasında durdu (`ModuleNotFoundError: sklearn`); Hafta 8 klasöründe de aynı hata.
- Kök neden: tüm haftaların kullandığı ortak sanal ortamda scikit-learn kurulu değildi.
- Düzeltme: ortak ortamda `pip install -r requirements.txt`.
- Durum: doğrulandı (9a sonrası 237 passed, 9b sonrası 243 passed).

## Doğrulama
```
python -m data_science.oulad.download          # raw csv mevcut, checksum dogrulandi
python -m data_science.oulad.vle
python -m data_science.oulad.dataset           # features rows=26403 cols=26
python -m data_science.oulad.validate --features
python -m pytest -q | tail -3                  # 243 passed, 1 warning
```
- Yeni testler ağ kullanmıyor (9a: 4, 9b: 6).
- İki notebook nbconvert ile baştan çalıştı; hata hücresi 0. Son hücredeki OZET değerleri validate çıktısıyla aynı.

## Okul sistemiyle eşleme
| OULAD | Bizim karşılığımız | Durum |
|---|---|---|
| score_mean | Not ortalaması | Var |
| vle_* | Mazeretsiz devamsızlık (yaklaşık) | Yaklaşık |
| n_unsubmitted | Girilmeyen sınav | Doğrulanacak |
| delay_mean | — | Yok |
| hist_* | Geçmiş dönem notları | Sentetik (H10) |
| Sosyokültürel | — | Kullanılmaz |

## Açık konular
- pytest uyarısı tanımlandı: `StarletteDeprecationWarning` (httpx ile starlette test istemcisi). Henüz giderilmedi.
- Notebook görsellerinde alternatif metin eksik: 01'de 6, 02_eng'de 7 görsel (nbconvert uyarısı).
- Hafta 6 hata 4 (pivotta sessiz ortalama) doğrulanacak; Hafta 7 m5 ve c4 açık.

## Hafta 10
- Genel model ile ders geçmişli model karşılaştırması, aynı test (2014J), belirsizlik aralığı ve SHAP.
- Sisteme uyumlu özellik alt kümesi.
- Sentetik okul geçmişi üreticisi (mock veriye dokunmadan, ayrı dosya).
