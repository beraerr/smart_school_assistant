# Hafta 8 — Veri Bilimi I

Bu hafta yalnızca veri, keşif ve özellik mühendisliği vardır. Sınıflandırıcı, regresyon veya başka bir model eğitilmez. `build_preprocessor` fit edilmemiş bir `ColumnTransformer` döndürür; fit Hafta 9'da çapraz doğrulama içinde yapılır.

## Kaynak

Cortez, P. ve Silva, A. (2008). *Using Data Mining to Predict Secondary School Student Performance*. A. Brito ve J. Teixeira (Ed.), Proceedings of 5th FUture BUsiness TEChnology Conference (FUBUTEC 2008), s. 5–12, Porto, Portugal. EUROSIS. ISBN 978-9077381-39-7.

UCI Machine Learning Repository, Student Performance, veri kümesi 320.  
https://archive.ics.uci.edu/dataset/320/student+performance  

Lisans: CC BY 4.0.

İndirilen dosya: https://archive.ics.uci.edu/static/public/320/student+performance.zip  
(`student-mat.csv`, `student-por.csv`; iç içe `student.zip` olabilir).

## Çalıştırma

Depo kökünden (`week-08`):

```bash
pip install -r requirements.txt
python -m data_science.download
python -m data_science.eda
python -m data_science.features
```

`download` CSV'ler diskteyse yeniden indirmez. `data/raw/CHECKSUMS.txt` sha256 tutar; sonraki çalıştırmada uyuşmazlık hata verir. Ham CSV'ler git dışındadır, checksum dosyası izlenir.

Çıktılar:

- `data_science/reports/figures/*.png` — ders bazında G3, G1–G2–G3 saçılımı, devamsızlık, failures ve geçme oranı, studytime, sayısal korelasyon ısı haritası
- `data_science/reports/eda_summary.json` — satır sayıları, ders bazında geçme oranı, G3=0 sayısı, G3 ile en yüksek |korelasyon|ün 10 özelliği, G1–G3 ve G2–G3 korelasyonu, ortak öğrenci sayısı, eksik değer sayısı
- `data_science/data/processed/features_early.parquet`
- `data_science/data/processed/features_midterm.parquet`

Geçme eşiği `PASS_THRESHOLD_20 = 10`. Bu, backend `PASS_GRADE = 50` ile aynı kuraldır: `G3 * 5 >= 50`. Hedef `at_risk = 1` yalnızca `G3 < 10` ise.

## Sızıntı

G2, final not G3 ile çok güçlü ilişkilidir. G2'yi özellik yapmak, sonucu dönem bitmeden neredeyse görmektir. G1 de birinci dönem notudur; dönem başı uyarısında yoktur.

- EARLY: G1 yok, G2 yok, G3 yok. Dönem başı erken uyarı.
- MIDTERM: G1 var, G2 yok, G3 yok.
- G3 hiçbir özellik setinde yoktur. `at_risk` ondan üretilir ve yalnızca etiket olarak parquet'te durur.

G3=0 satırları silinmez. UCI'de sıfır çoğu zaman sınava girmemeye karşılık gelir; `g3_zero` bunu işaretler. Bayrak hedefin fonksiyonudur (`G3 = 0` ise `at_risk = 1`), bu yüzden özellik setine girmez. Hafta 9 isterse bu satırları bayrağa bakarak ayırır.

`RANDOM_STATE = 42` Hafta 9 bölmeleri içindir. Bu hafta rastgele bir model veya örneklem yoktur.

## Ortak öğrenci

Aynı öğrenci matematik ve Portekizce dosyalarında ayrı satırdır. `student_key`, şu sütunların SHA-256 özetidir: `school`, `sex`, `age`, `address`, `famsize`, `Pstatus`, `Medu`, `Fedu`, `Mjob`, `Fjob`, `reason`, `nursery`, `internet`.

Ortak öğrenci sayısı, iki derste birden bulunan farklı `student_key` değerlerinin adedidir. Aynı profil bir ders dosyasında tekrarlanabildiği için bu sayı satır satır iç birleşimin uzunluğu değildir. Sayı literatürden kopyalanmaz; `load` çalışınca yazdırılır ve `eda_summary.json` içine konur.

Hafta 9'da bölme `GroupKFold` ile `student_key` üzerinde yapılmalıdır. Satır bazlı rastgele bölme, aynı öğrencinin bir dersini eğitime, diğer dersini teste koyar.
