# Hafta 8 — Veri Bilimi I: Veri, EDA ve Özellik Mühendisliği

**Akıllı Okul Bilgi Sistemi — Staj Projesi · Hafta 8 / 12**

## Amaç ve kapsam

Hafta 10'daki risk entegrasyonuna temel oluşturmak için açık bir öğrenci başarı veri seti incelendi ve modellemeye hazır özellik setleri üretildi. Bu hafta **model eğitilmedi**; model karşılaştırması, çapraz doğrulama ve SHAP Hafta 9'da yapılacak. Uygulama kodu, mock veri ve eval bu haftanın kapsamı dışında tutuldu.

## Veri seti

| Özellik | Değer |
|---|---|
| Kaynak | Cortez & Silva (2008), UCI Machine Learning Repository, CC BY 4.0 |
| Toplam kayıt | 1044 (Matematik 395, Portekizce 649) |
| Eksik değer | 0 |
| İki derste ortak öğrenci | 366 (`student_key` ile) |
| Not ölçeği | 0–20 (G1, G2 dönem içi; G3 final) |

İndirilen dosyaların sha256 değerleri `data/raw/CHECKSUMS.txt` içinde tutuluyor ve her çalıştırmada doğrulanıyor.

## Hedef tanımı

`at_risk = 1` eğer `G3 < 10`. Bu eşik, sistemimizdeki geçme notuyla birebir aynı: `G3 × 5 < 50 = PASS_GRADE`.

| Ders | Geçme oranı | Risk oranı |
|---|---|---|
| Matematik | %67,1 | %32,9 |
| Portekizce | %84,6 | %15,4 |
| Toplam | %78,0 | %22,0 (230 öğrenci) |

## EDA bulguları

G3 ile en güçlü 10 ilişki (Pearson):

| Özellik | r |
|---|---|
| G2 | 0,91 |
| G1 | 0,81 |
| failures | −0,38 |
| Medu | 0,20 |
| studytime | 0,16 |
| Fedu | 0,16 |
| Dalc | −0,13 |
| age | −0,13 |
| Walc | −0,12 |
| traveltime | −0,10 |

- **Sızıntı riski:** G2 (0,91) ve G1 (0,81) finali neredeyse belirliyor. Bu yüzden iki özellik seti tanımlandı: **EARLY** (G1 ve G2 yok, dönem başı erken uyarı) ve **MIDTERM** (G1 var, G2 yok). G3 hiçbir sette yer almıyor; bu testlerle kontrol ediliyor.
- **Not dışı en güçlü sinyal** geçmiş başarısızlık (failures, −0,38). Anne/baba eğitimi ve çalışma süresi zayıf pozitif; alkol, yaş ve yol süresi zayıf negatif.
- **Devamsızlık (düzeltilmiş bulgu, bkz. Hata kaydı 1):** İlk analizde `absences` en güçlü 10 ilişkiye girmedi. Ancak 53 G3=0 kaydının tamamı 0 devamsızlık diliminde ve ilişkiyi bastırıyor. Bu kayıtlar hariç tutulunca devamsızlık anlamlı bir sinyal:

| Korelasyon (absences–G3) | G3=0 dahil | G3=0 hariç |
|---|---|---|
| Pearson | −0,05 | −0,22 |
| Spearman | −0,11 | −0,24 |

| Devamsızlık | Öğrenci (hariç) | Geçme oranı (dahil) | Geçme oranı (hariç) |
|---|---|---|---|
| 0 | 306 | %76,6 | %89,9 |
| 1–5 | 368 | %83,4 | %83,4 |
| 6–10 | 202 | %78,7 | %78,7 |
| 11–20 | 92 | %66,3 | %66,3 |
| 21+ | 23 | %52,2 | %52,2 |

  - Devamsızlık arttıkça geçme oranı düzenli düşüyor. Yine de 21+ grubunun yarısı geçiyor (n=23, küçük örneklem): devamsızlık tek başına karar verdirmez.
  - Sistemimiz için çıkarım: ham sayı yerine mazeretsiz devamsızlık kullanılmalı (Ali: 14 = 8 mazeretsiz + 6 mazeretli).

Üretilen grafikler (`data_science/reports/figures/`): `g3_distribution_by_subject.png`, `g1_g2_g3_scatter.png`, `absences_vs_g3.png`, `failures_vs_pass_rate.png`, `studytime_vs_g3.png`, `numeric_correlation_heatmap.png`. Sayısal özet: `data_science/reports/eda_summary.json`.

## Veri kalitesi ve kararlar

| Konu | Değer | Karar |
|---|---|---|
| G3 = 0 | 53 kayıt (%5,1) | Silinmedi; `g3_zero` bayrağı eklendi. Hepsinde devamsızlık 0; nedeni (sınava girmeme, ayrılma) belirtilmiyor. İlişki analizlerinde ayrıca hariç tutularak bakılmalı. |
| Ortak öğrenci | 366 | Literatürde 382 bildiriliyor; eşleştirme sütunları farklı. Hafta 9'da GroupKFold grubu olarak kullanılacak. |
| Eksik değer | 0 | Doldurma (imputation) gerekmedi. |

## Özellik mühendisliği

Türetilmiş özellikler:

- `parent_edu_max`: anne/baba eğitiminin büyüğü
- `alcohol_total`: Dalc + Walc
- `support_any`: okul veya aile desteği
- `has_failures`: geçmiş başarısızlık var mı
- `absences_log1p` ve `absence_bucket`

Ön işleme (`build_preprocessor`):

- İkili kategoriler 0/1 olarak kodlandı.
- Nominal kategoriler one-hot ile kodlandı (`handle_unknown="ignore"`).
- Sıralı sütunlar olduğu gibi bırakıldı.
- Hat **fit edilmeden** döndürülüyor; Hafta 9'da CV katmanları içinde fit edilecek, böylece sızıntı oluşmayacak.

Çıktılar: `processed/features_early.parquet`, `processed/features_midterm.parquet`.

## Sistemimizle eşleme

| UCI özelliği | Bizim şemamız | Durum |
|---|---|---|
| G1 / G2 | Not ortalaması ÷ 5 | Türetilebilir |
| absences | Devamsızlık kayıtları (mazeret ayrımıyla) | Var |
| failures | — | Yok |
| studytime, Medu/Fedu, destek | — | Yok |

Sistemimiz yalnızca not ve devamsızlık tutuyor. Bu yüzden Hafta 10'daki risk göstergesi bir karar olarak değil, gerekçesiyle gösterilen bir **dikkat bayrağı** olarak tasarlanacak. Ayrıntılı eşleme: `data_science/feature_mapping.md`.

## Notebook'lar

- `notebooks/01_uci_eda.ipynb` (Türkçe) ve `notebooks/01_uci_eda_eng.ipynb` (İngilizce); HTML kopyaları `notebooks/html/` altında.
- Bölümler: veri seti, hedef tanımı, G3 dağılımı, korelasyonlar, sızıntı, devamsızlık analizi, özellik setleri, sonuç.
- Mantık `data_science` paketinden import ediliyor; sayılar markdown'a elle yazılmadı, hücre çıktılarından okunuyor. Notebook'lar baştan çalıştırılıp çıktılarıyla kaydedildi.

## Çalıştırma

```bash
python -m data_science.download
python -m data_science.eda
python -m data_science.features
```

## Doğrulama

```
233 passed, 1 warning
```

- Testler ağ kullanmıyor; 30 satırlık sentetik fixture CSV ile çalışıyor.
- İki notebook `jupyter nbconvert --execute` ile baştan hatasız çalıştı.
- Kontrol edilenler: hedef eşiği (G3=9 → 1, G3=10 → 0), setlerde G1/G2/G3 yokluğu, NaN üretmeyen dönüşüm ve bilinmeyen kategori.
- pytest uyarısı henüz incelenmedi.

## UCI'ın sınırları, hipotez ve yön değişikliği

**UCI'ın verdiği (genel risk sinyali):** Erken notlar finali güçlü yansıtıyor (G1–G3 r = 0,81). Geçmiş başarısızlık, not dışı en güçlü sinyal (r = −0,38). Devamsızlık, G3=0 hariç tutulunca anlamlı, ama tek başına belirleyici değil.

**UCI'ın veremediği (bağlam):** Veri tek bir öğretim yılı, iki ders ve iki okuldan oluşuyor. Ders, öğretmen veya sınav bağlamı yok; sınav tarihi ve sırası olmadığı için gerçek bir erken uyarı kurulamıyor. Örneklem de küçük: yaklaşık 678 tekil öğrenci, yaklaşık 230 riskli.

**Hipotez:** Risk, öğrencinin mutlak notundan çok dersin bağlamına göre değişir. Örneğin bir öğretmenin dönem sonu sınavı geçen yıl diğerlerinden zordu ve birçok öğrencinin notu düştü. İlk iki sınavı sınırda olan bir öğrencinin bu derste riski, aynı notlarla başka bir dersteki öğrenciden daha yüksektir.

**Karar:** UCI, genel (temel) model olarak kalır. Bağlam hipotezi daha büyük ve zamansal bir veri setinde, OULAD'da test edilir:

| Hafta | Adım |
|---|---|
| 8 | UCI: genel model temeli |
| 9 | OULAD: veri ve ders geçmişi özellikleri |
| 10 | Kıyas: genel model ile ders geçmişli model (zamansal test) |
| 11 | Doğrulanan özellik tarifinin sisteme uygulanması: risk sekmesi |

**İlkeler:** Risk, gerekçesiyle gösterilen bir dikkat bayrağıdır, karar değildir. Sistemde sosyokültürel özellik kullanılmaz; yalnızca not, mazeretsiz devamsızlık ve ders bağlamı kullanılır. OULAD'dan sisteme veri veya model taşınmaz, yalnızca doğrulanmış özellik tarifi taşınır.

## Hata kayıtları

**Hata kaydı 1: devamsızlık analizi**

- **Belirti:** İlk EDA'da devamsızlık G3 ile en güçlü 10 ilişkiye girmedi; "zayıf gösterge" sonucu çıkarıldı.
- **Kök neden:** 53 G3=0 kaydının tamamı 0 devamsızlık diliminde. Bu kayıtlar (olası sınava girmeme/ayrılma) ilişkiyi bastırıyordu.
- **Düzeltme:** Korelasyon ve dilim analizi G3=0 dahil/hariç ayrı hesaplandı (notebook, bölüm f).
- **Durum:** Doğrulandı. G3=0 hariç Pearson −0,22; geçme oranı dilimlerde %89,9'dan %52,2'ye düşüyor.

## Açık konular

- Hafta 6 hata 4 (pivotta sessiz ortalama): doğrulanacak.
- Hafta 7 eval: m5 (nedensellik tahmini) ve c4 (73,98 → "73") açık.
- pytest uyarısı incelenecek.
- Notebook görsellerinde alternatif metin eksik (6 görsel).

## Hafta 9 planı

- Daha büyük ve zamansal veri: OULAD (Open University Learning Analytics Dataset)
- Ders geçmişi özellikleri: öğrencinin notunun, dersin geçmiş ortalamasına göre konumu
- Zamansal bölme: 2013 dönemleriyle eğitim, 2014 ile test
- `02` numaralı notebook ile sunum
