# Ek analizler: ön kayıt

**Yazıldığı tarih:** 5 Kasım 2026. Bu dosya, ek analizler koşulmadan **önce** yazıldı. Koşudan önce md5 değeri alınır ve WEEK_11 raporuna yazılır; dosya koşudan sonra değiştirilmez. Sonuçlar ayrı bir dosyada, bu beklentilerin yanına konur.

Bu analizlerin hiçbiri okul sistemindeki kuralı değiştirmez. Test dönemi (2014J) daha önce birden çok kez görüldüğü için bütün sonuçlar **ek analiz (keşifsel)** olarak etiketlenir ve doğrulama (2014B) ile test (2014J) sonuçları her zaman yan yana raporlanır.

---

## 1. Düşünce haritası: buraya nasıl geldik?

| Adım | Ne bulduk | Neyi eksik ya da şüpheli bıraktı |
|---|---|---|
| H8 · UCI | Dönem notları finali neredeyse belirliyor; devamsızlık (G3=0 düzeltmesinden sonra) riskle ilişkili. | Bağlam yok, zaman yok. Erken uyarı kurulamıyor. |
| H9 · OULAD keşif | Risk seviyesi derse ve döneme göre değişiyor; öğrencinin erken izi riskle güçlü ilişkili. | Hepsi betimsel. |
| H10 · Model | Ders geçmişi tahmini iyileştirmedi; işe yarayan öğrencinin kendi izi ve sınıf içi sıralama. | **Çalışma doğrusal ilerledi:** tek kesim günü (60), tek hedef (başarısız ∪ bırakmış), tek özellik paketi ("öğrencinin izi" tek blok olarak). |
| H11 · Kural | İki sinyalli kural (not + etkinlik), modelin isabetlerinin büyük kısmını yakalıyor. | "Öğrencinin izi" tam olarak neyi yakalıyor? Notu düşen öğrenciyi mi, yoksa dersi çoktan bırakmış öğrenciyi mi? |

**Ana şüphe.** Hedef, "başarısız **ya da dersi bırakmış**" öğrencileri birlikte içeriyor. Dersi bırakan öğrenci doğal olarak sisteme girmeyi ve ödev teslim etmeyi de bırakır. Bu durumda etkinlik ve teslim sinyalleri, hedefin bir kısmını neredeyse **tanım gereği** yakalıyor olabilir: "devamsızlığı çok olan zaten kalır." Asıl zor ve asıl değerli soru, devam eden ama notu düşen öğrenciyi bulmak.

**Ek analizler bu şüpheyi sınar:**

| Analiz | Cevapladığı soru |
|---|---|
| E1 · Sinyal ayrıştırma | Hangi sinyal grubu tek başına ne kadar bilgi taşıyor? Yalnız notlarla ne kadar ileri gidilebilir? |
| E2 · Hedef ayrıştırma | Model, "başarısız" ile "bıraktı"yı aynı kolaylıkla mı buluyor? Kural kimi işaretliyor? |
| E3 · Ne kadar erken? | Erken uyarının bedeli: kesim günü öne çekildikçe başarı nasıl değişiyor? |
| E4 · Literatürle kıyas | Bizim sayılarımız neden yayınlardakinden düşük ve bu ne anlama geliyor? |
| E5 · Öğrenme eğrisi (isteğe bağlı) | Daha fazla veri sonucu değiştirir mi, yoksa sinyalin sınırına mı geldik? |

---

## 2. Ortak kurallar

- Model: GENERAL seti ve hgb; ayar protokolü Hafta 10 ile aynı (2013J'de eğit, 2014B'de log loss ile seç, 2013J + 2014B ile yeniden eğit, 2014J'de değerlendir). Lojistik regresyon yalnızca E1'de ikinci model olarak raporlanır.
- Metrikler: ROC AUC (genel ve modül içi ortalama), %20 sınıf içi kesinlik ve yakalama; bootstrap aralıkları Hafta 10 ile aynı yöntemle (B = 1.000, seed 42, modül içi tabakalı).
- GGG her iki dönemde hariç (60. güne kadar notlu ödev yok), Hafta 11 kuralıyla tutarlı.
- Sosyokültürel sütun kullanılmaz.
- "Tuttu / tutmadı" kararı yalnızca aşağıdaki ölçütlerle verilir. Ölçüt sonradan değiştirilmez; ölçütün yanlış kurulduğu sonradan anlaşılırsa bu ayrı bir not olarak yazılır.

---

## 3. E1 · Sinyal ayrıştırma

**Gruplar** (GENERAL sütunları, `feature_list.md` üzerinden; her sütun tam olarak bir gruba):
- **NOT:** notlardan türeyen sütunlar (ör. score_mean, score_weighted_mean).
- **TESLİM:** ödev teslim davranışı (ör. n_expected, n_submitted, n_unsubmitted, delay_mean ve benzerleri).
- **ETKİNLİK:** sanal öğrenme ortamı sütunları (vle_*).
- **KAYIT:** kayıt tarihi.
Grup ataması koşudan önce koda yazılır ve test edilir. Bir sütunun grubu belirsizse koşu durur.

**Setler:** yalnız NOT, yalnız TESLİM, yalnız ETKİNLİK, NOT + TESLİM (etkinliksiz), GENERAL (hepsi, referans).

**Beklentiler:**
- **B1.** Hiçbir tek grup GENERAL'e ulaşmaz. Ölçüt: her tek grubun test ROC AUC'si GENERAL'den en az 0,02 düşük.
- **B2.** Yalnız NOT en zayıf tek gruptur: 60. güne kadar notu olmayan öğrenciler (train'de yaklaşık beşte bir) bu sette bilgisiz kalır. Ölçüt: yalnız NOT'un test ROC AUC'si, yalnız TESLİM ve yalnız ETKİNLİK'ten düşük.
- **B3.** Etkinliksiz model (NOT + TESLİM), GENERAL'in çok gerisinde kalmaz. Ölçüt: fark 0,03'ten küçük. (Tutarsa: okulda devamsızlık bilgisi olmasa da notlar ve ödev davranışı işin büyük kısmını taşır.)

---

## 4. E2 · Hedef ayrıştırma

**Hedefler:**
- **KALDI:** Fail = 1; Pass ve Distinction = 0; Withdrawn dışarıda.
- **BIRAKTI:** Withdrawn = 1; Pass ve Distinction = 0; Fail dışarıda.
- Referans: mevcut hedef (Fail ∪ Withdrawn).

Her hedef için GENERAL ve E1'in tek grup setleri ayrı ayrı eğitilir.

**Beklentiler:**
- **B4.** BIRAKTI, KALDI'dan daha kolay bulunur. Ölçüt: GENERAL'in test ROC AUC'si BIRAKTI'da KALDI'dan en az 0,03 yüksek.
- **B5.** BIRAKTI'da ETKİNLİK tek başına güçlüdür. Ölçüt: yalnız ETKİNLİK ile GENERAL arasındaki fark BIRAKTI'da, KALDI'dakinden küçük.
- **B6.** KALDI'da NOT'un payı artar. Ölçüt: KALDI'da yalnız NOT ile yalnız ETKİNLİK arasındaki ROC AUC farkı, referans hedeftekinden NOT lehine daha büyük.
- **B7.** İki sinyalli kural, isabetlerinin çoğunu bırakanlardan alır. Ölçüt: kuralın %20 bayraklarındaki isabetlerin yarısından fazlası Withdrawn (test dönemi; doğrulama da raporlanır).

**Yorum çerçevesi (önceden):** B4 ve B7 tutarsa, rapor bunu bir başarı olarak değil bir uyarı olarak yazar: kural en kolay grubu, yani çoktan kopmuş öğrenciyi buluyor; devam eden ama notu düşen öğrenci daha zor bulunuyor. Okulda "dersi bırakma" yok; okuldaki karşılığı uzun devamsızlık. Bu, okul sisteminin bayraklarının da önemli ölçüde devamsızlıktan geleceğini ve not sinyalinin asıl değerli ama daha zayıf sinyal olduğunu gösterir.

---

## 5. E3 · Ne kadar erken?

**Kesim günleri:** 14, 30, 60 (mevcut), 90, 120. Her kesimde örneklem ve özellikler mevcut fonksiyonlarla aynı kurallarla yeniden üretilir.

**Karşılaştırılabilirlik:** Kesim günü değiştikçe örneklem de değişir (o güne kadar bırakanlar çıkar). İki görünüm raporlanır: (a) her kesimin kendi örneklemi, (b) sabit kohort: 120. günde hâlâ kayıtlı öğrenciler, her kesimde aynı.

**Beklentiler:**
- **B8.** Başarı kesim günüyle artar. Ölçüt: (b) görünümünde test ROC AUC'si 14 → 120 boyunca hiçbir adımda 0,01'den fazla düşmez.
- **B9.** Kazancın büyük kısmı erken gelir. Ölçüt: (b) görünümünde 14 → 60 artışı, 60 → 120 artışından büyük.
- **B10.** 14. günde notlu ödev neredeyse yoktur; erken başarının çoğunu ETKİNLİK taşır. Ölçüt: 14. günde yalnız ETKİNLİK seti GENERAL'e 0,02'den yakın.

---

## 6. E4 · Literatürle kıyas

Hesap yok. Tablo: çalışma, kesim/pencere, bölme türü (zamansal/rastgele), hedef, demografik özellik kullanımı, metrik ve değer. Yalnızca birincil kaynaktan doğrulanan sayılar girer; özet sitelerden alınan sayı girmez. Amaç bir sıralama değil, bizim kurgumuzun (60. gün, zamansal bölme, sosyokültürel özellik yok) yayınlardaki farklı kurgularla neden karşılaştırılamaz olduğunu göstermek.

**Beklenti (B11, nitel):** Yüksek değer bildiren çalışmaların çoğu dersin tamamına ya da daha geç bir pencereye ait veriyi, rastgele bölmeyi ya da demografik özellikleri kullanır.

---

## 7. E5 · Öğrenme eğrisi (isteğe bağlı)

Train'in %10, 25, 50, 75 ve 100'üyle (modül içi tabakalı, seed 42) GENERAL hgb; test ROC AUC.

**Beklenti (B12):** %50'den sonra artış 0,01'den küçük; yani darboğaz veri miktarı değil sinyalin kendisi.

---

## 8. Raporlama

- Her beklenti için: beklenti, ölçüt, doğrulama sonucu, test sonucu, **tuttu / tutmadı / belirsiz**.
- Tutmayan beklentiler silinmez; rapordaki "Ek analizler" sekmesinde ve "Hatalar ve düzeltmeler" bölümündeki açıklama kaydının devamı olarak gösterilir.
- Sonuçlar okul sistemindeki kuralı değiştirmez; değişiklik önerisi çıkarsa ayrı bir karar olarak, yeni ve önceden yazılmış ölçütlerle ele alınır.
