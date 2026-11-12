# Ön kayıt eki 2: E3 dışlama kuralı

**Tarih:** 5 Kasım 2026. Bu ek, E3 koşulmadan **önce** yazıldı. `ek_analizler_on_kayit.md` ve `ek_analizler_on_kayit_eki.md` dosyaları değiştirilmedi. B8, B9 ve B10 ölçütleri ön kayıttaki metinle aynen kalır; karar kuralı `ek_analizler_on_kayit_eki.md` içindekiyle aynıdır (iki dönem tutar: tuttu; ikisi tutmaz: tutmadı; ayrışır: belirsiz).

## Tespit

`assessments.csv` ham verisine göre, Exam dışı notlu ödevi olan modül-dönemler:

- **14. gün:** yalnız BBB 2014B (ilk ödev günü 12). 2014J'de hiçbir modülün 14. güne kadar notlu ödevi yoktur (en erken gün 19).
- **30. gün:** EEE ve GGG notlu ödevsizdir (EEE'nin ilk ödevi gün 33, GGG'ninki gün 61).

E1/E2'deki `n_expected == 0` dışlaması 14. günde 2014J'nin tamamını ve 2014B'nin büyük kısmını silerdi; kesim günü kuralı ile "14. günde değerlendirme" birlikte sağlanamaz. Bu yüzden E3 için aşağıdaki kural, sonuçlar görülmeden önce yazılmıştır.

## E3 dışlama kuralı

1. E3'ün **ana görünümünde notlu ödev dışlaması uygulanmaz**; bütün modül-dönemler değerlendirilir. Gerekçe: "notlu ödevi olmayan sınıfta bayrak yok" okul sistemindeki kuralın kuralıdır; E3'ün sorusu modelin ne kadar erken görebildiğidir. 14. günde model yalnızca etkinlik ve kayıt bilgisiyle çalışır; B10 bunu ölçer.
2. Her kesimde, kesim gününe kadar notlu ödevi olmayan modül-dönemler **bilgi olarak listelenir** (dışlanmaz). Ayrıca her kesimde bu modül-dönemler hariç tutularak hesaplanmış **ikincil bir ROC AUC** da raporlanır (E1/E2 ile aynı mantık: doğrulama ve test dönemlerinde `n_expected == 0` modül-dönemler dışarıda, eğitim satırları kalır). Kesimin notlu ödevi olan modül-dönemi kalmadığında (ör. 14. gün testi) bu alan "tanımsız" yazılır ve nedeni belirtilir.
3. **60. gün bağlantısı:** 60. günün ikincil (dışlamalı) değeri E1 GENERAL (ve ETKİNLİK) ile birebir aynı olmalıdır; koşu bunu denetler, tutmazsa durur. Ana görünümün 60. gün değeri E1'den farklı olabilir: ana görünümde GGG dahildir.
4. **B8, B9, B10** ana (dışlamasız) değerlerle, sabit kohort (b) görünümünde değerlendirilir; ölçüt metinleri değişmez.
5. Kural tabanlı ölçü (rule2 %20 kesinlik) E3'te raporlanmaz; yalnızca modelin %20 sınıf içi kesinliği raporlanır.

## Sabit kohort

1. Sabit kohort (b) = doğrulama ve test dönemlerinde 120. günde hâlâ kayıtlı olan öğrenciler, **bütün** modül-dönemlerden. Notlu ödev dışlaması kohort tanımına girmez; bu satır kümesi her kesimde birebir aynıdır (test).
2. İkincil (notlu ödev dışlamalı) ROC AUC yalnızca (a) görünümünde raporlanır; (b) görünümünde raporlanmaz, çünkü dışlama kohortu kesimden kesime değiştirir.
3. B8, B9, B10 (b) görünümünün ana (dışlamasız) değerleriyle değerlendirilir.
4. Eğitim tarafı: her kesimde model, o kesimin kendi eğitim örneklemiyle (Hafta 10 protokolü) eğitilir; sabit kohort yalnızca **değerlendirme** satırlarını sabitler.

## Uygulama ayrıntıları

- **Görünümler:** (a) her kesimin kendi örneklemi, (b) sabit kohort. İki görünümde de GENERAL ve yalnız ETKİNLİK (hgb): doğrulama ve test ROC AUC (aralıklı) ve %20 sınıf içi kesinlik; satır ve pozitif sayıları rapora yazılır. Referans hedefe ek olarak KALDI ve BIRAKTI için GENERAL ROC AUC raporlanır; bu bir beklenti değildir.
- **Kohort örneklemi:** `dataset.build_features` ile aynı kuralla kurulur (`date_unregistration < 120` olanlar dışarıda). (b) görünümünde model (a) görünümündekiyle aynıdır; yalnızca değerlendirme satırları kohortla sınırlanır.
- **Ölçütlerin uygulanması:** ön kayıttaki ortak kurala göre (model: GENERAL, hgb) B8 ve B9 GENERAL test ROC AUC'si ile hesaplanır. B8'de "düşmez", düşüşün (önceki − sonraki) 0,01'i aşmaması demektir. B10'da "yakın", mutlak fark |GENERAL − ETKİNLİK| < 0,02 demektir.
- **Koşu:** `python -m data_science.oulad.ek --e3`. Ön kayıt md5 kontrolü (üç dosya) koşudan önce çalışır.
