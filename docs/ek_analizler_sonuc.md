# Ek analizler: sonuçlar (E1–E4)

**Koşular:** 5 Kasım 2026. E1/E2: `python -m data_science.oulad.ek`, 4 dk 24 sn (iki kez koşuldu, sonuçlar birebir aynı). E3: `python -m data_science.oulad.ek --e3`, 12 dk 49 sn. Çıktı: `data_science/oulad/reports/ek_metrics.json`.
**Ön kayıt:** `docs/ek_analizler_on_kayit.md` (md5 `eb367fbbed2308493c7ae67adc06c608`, 17:04), ek dosyası `docs/ek_analizler_on_kayit_eki.md` (17:39'da `20f75feb…`, koşudan önce bir kez güncellendi, 17:41'de `f8cb24beba8e53d103012467022b25be`). E3 için ikinci ek dosyası `docs/ek_analizler_on_kayit_eki2.md` (dışlama kuralı ve sabit kohort; koşudan önce yazıldı; md5 `docs/on_kayit_md5.txt` içinde). Koşu, ön kayıt dosyalarının son kaydını doğrulamadan başlamıyor; bir kez ilk kayda baktığı için durdu, kontrol "son kayıt" olarak düzeltildi, dosyalar değişmedi.
**Etiket:** Ek analiz (keşifsel). Test dönemi daha önce görüldü. Karar kuralı: iki dönemde de tutarsa "tuttu", ikisinde de tutmazsa "tutmadı", ayrışırsa "belirsiz". Bu sonuçlar okul sistemindeki kuralı değiştirmez.

Bütün değerler hgb, sınıf içi değerlendirmede GGG 2014B ve 2014J hariç. ROC AUC aralıkları ve eşli farklar JSON'da; burada nokta tahminleri.

---

## 1. Beklentiler

| # | Beklenti | Ölçüt | Doğrulama 2014B | Test 2014J | Sonuç |
|---|---|---|---|---|---|
| B1 | Hiçbir tek grup GENERAL'e ulaşmaz | Her tek grup ≤ GENERAL − 0,02 | NOT .771, TESLİM .760, ETKİNLİK .741; GENERAL .829 | .712, .735, .732; GENERAL .798 | **Tuttu** |
| B2 | Yalnız NOT en zayıf tek grup | NOT < TESLİM ve NOT < ETKİNLİK | NOT en **güçlü** tek grup | NOT en zayıf | **Belirsiz** |
| B3 | Etkinliksiz model çok geride kalmaz | GENERAL − NOT_TESLİM < 0,03 | .829 − .818 = .011 | .798 − .781 = .017 | **Tuttu** |
| B4 | BIRAKTI, KALDI'dan kolay | BIRAKTI ≥ KALDI + 0,03 | KALDI .843, BIRAKTI .805 | KALDI .815, BIRAKTI .778 | **Tutmadı (tersi)** |
| B5 | BIRAKTI'da ETKİNLİK tek başına güçlü | (GENERAL − ETKİNLİK) BIRAKTI'da daha küçük | BIRAKTI .143, KALDI .067 | BIRAKTI .079, KALDI .069 | **Tutmadı** |
| B6 | KALDI'da NOT'un payı artar | (NOT − ETKİNLİK) KALDI'da referanstan büyük | KALDI +.006, referans +.031 | KALDI −.006, referans −.020 | **Belirsiz** |
| B7 | Kural isabetlerinin çoğu bırakanlardan | Withdrawn / isabet > 0,5 | 285 / 956 = %29,8 | 503 / 1.245 = %40,4 | **Tutmadı** |

Özet: 2 tuttu, 3 tutmadı, 2 belirsiz.

## 2. Kural kimi yakalıyor? (B7'nin doğru okunuşu)

İsabetlerin bileşimi tek başına yanıltıcıdır, çünkü pozitiflerin bileşimi de dönemden döneme değişir. Doğru ölçü, her grubun ne kadarının yakalandığıdır:

| Dönem | Pozitif: Fail / Withdrawn | Kuralın yakaladığı Fail | Kuralın yakaladığı Withdrawn |
|---|---|---|---|
| Doğrulama 2014B | 1.578 / 945 | 671 → **%42,5** | 285 → **%30,2** |
| Test 2014J | 1.798 / 1.329 | 742 → **%41,3** | 503 → **%37,8** |

İki dönemde de kural, başarısız olacak öğrencileri bırakacak öğrencilerden biraz daha yüksek oranda yakalıyor.

## 3. Bulgular

**Bulgu 1: Ana şüphe yanlıştı, hem de tersine.** Başlangıç şüphesi, modelin ve kuralın işi kolay olan "dersi bırakanları" etkinlik izinden bulduğuydu. Veri tersini gösterdi: 60. günde, dersi sürdürüp başarısız olacak öğrenciyi bulmak, bırakacak öğrenciyi bulmaktan iki dönemde de yaklaşık 0,04 ROC AUC daha kolay; kural da başarısız olacakları biraz daha yüksek oranda yakalıyor.

**Bulgu 2: Bırakmanın erken izi etkinlikte değil, teslimde (hipotez).** BIRAKTI için yalnız ETKİNLİK en zayıf tek grup (doğrulama .662, test .698); testte en güçlü tek grup TESLİM (.751). Açıklama önerisi: 60. günde bu öğrenciler sisteme hâlâ giriyor; kopuşun ilk işareti tıklamanın azalması değil, ödevin teslim edilmemesi. Bu açıklama bu analizle sınanmadı; E3 (kesim günü eğrisi) kısmen sınar.

**Bulgu 3: Tek bir sinyal grubuna güvenilmez.** Doğrulamada en güçlü tek grup NOT, testte en zayıf (B2 belirsiz). Tek grubun gücü dönemden döneme değişiyor; kararlı olan yalnızca kombinasyon (B1). Hafta 10'daki "testte birinci, doğrulamada sonuncu" dersinin küçük bir tekrarı.

**Bulgu 4: Etkinlik olmadan da yakın bir sonuç alınıyor.** Not ve teslim davranışı birlikte, tam modelin iki dönemde .011 ve .017 gerisinde (B3). Okul için anlamı: risk işaretinin asıl taşıyıcısı devamsızlık değil, not ve ödev kaydı. Okul sisteminde "girilmeyen/teslim edilmeyen ödev" karşılığı bugün yok; bu çalışma, onun en değerli eksik sinyal olduğunu gösteriyor.

## 4. Okul sistemi için anlamı (değişiklik değil, not)

- Sistemdeki kural değişmez. Bu analizler kuralın neyi yakaladığını açıklar.
- Kural "kopmuş öğrenci dedektörü" değildir: başarısız olacak öğrencileri de en az o kadar yakalar.
- Gelecek çalışma: okul şemasına ödev/teslim kaydı eklenirse, Hafta 10'daki üç sinyalli kurala dönmek önceden yazılmış ölçütlerle yeniden sınanabilir.

## 5. Sınırlar

- Keşifsel: test dönemi daha önce görüldü; tek doğrulama dönemi var.
- Farklar nokta tahminleriyle yazıldı; ROC AUC aralıkları ve eşli farkların aralıkları raporda gösterilecek. B4'teki 0,04'lük fark, Hafta 10'daki tam test kümesi aralık genişliğinin (±0,009) birkaç katı; ancak KALDI ve BIRAKTI alt kümeleri daha küçük olduğundan kendi aralıklarıyla okunmalı.
- KALDI ve BIRAKTI, karşı grubu dışarıda bırakarak kuruldu; gerçek kullanımda iki grup birlikte gelir.
- Bulgu 2'deki açıklama bir hipotezdir.
- NOT_TESLİM setinde KAYIT yok; B3'teki fark ETKİNLİK ile birlikte KAYIT'ı da kapsar.

## 6. E3 · Ne kadar erken?

**Koşudan önce fark edilen sorun ve kararı (ek dosya 2):** 14. güne kadar notlu ödevi olan tek modül-dönem BBB 2014B; 2014J'de en erken notlu ödev 19. günde. E1/E2'deki "notlu ödevi olmayan modül-dönem hariç" kuralı 14. günde test kümesini boşaltırdı. Bu kural okul sisteminin bayrak kuralıdır, modelin değerlendirme kuralı değildir; E3'ün ana görünümünde uygulanmadı, dışlamalı değerler ikincil olarak raporlandı. Sabit kohort: doğrulama ve test dönemlerinde 120. günde hâlâ kayıtlı öğrenciler (bütün modül-dönemler); modeller her kesimde kendi eğitim örneklemiyle eğitildi, kohort yalnızca değerlendirme satırlarını sabitler.

**Sağlama:** 60. günün dışlamalı değeri E1 GENERAL ile birebir aynı (.829 / .798); dışlamasız değeri Hafta 10 GENERAL ile aynı (.814 / .792). 120. günde iki görünüm tanım gereği aynı.

**Sabit kohort, GENERAL ve yalnız ETKİNLİK (hgb, ROC AUC):**

| Kesim günü | 14 | 30 | 60 | 90 | 120 |
|---|---|---|---|---|---|
| GENERAL doğrulama | .666 | .744 | .813 | .862 | .889 |
| GENERAL test | .675 | .711 | .788 | .821 | .864 |
| ETKİNLİK doğrulama | .670 | .684 | .735 | .776 | .819 |
| ETKİNLİK test | .669 | .689 | .727 | .746 | .790 |

| # | Beklenti | Ölçüt | Doğrulama | Test | Sonuç |
|---|---|---|---|---|---|
| B8 | Başarı kesim günüyle artar | Hiçbir adımda 0,01'den fazla düşüş yok | Her adım artış | Her adım artış | **Tuttu** |
| B9 | Kazancın çoğu erken | (14→60) > (60→120) | +.147 > +.076 | +.113 > +.076 | **Tuttu** |
| B10 | 14. günde erken başarıyı ETKİNLİK taşır | \|GENERAL − ETKİNLİK\| < 0,02 | .004 | .006 | **Tuttu** |

**Hedeflere göre (sabit kohort, GENERAL, ROC AUC; doğrulama / test):**

| Kesim | Referans | KALDI | BIRAKTI | KALDI − BIRAKTI (test) |
|---|---|---|---|---|
| 14 | .666 / .675 | .688 / .692 | .590 / .628 | .064 |
| 30 | .744 / .711 | .755 / .727 | .722 / .696 | .031 |
| 60 | .813 / .788 | .827 / .808 | .776 / .763 | .045 |
| 90 | .862 / .821 | .875 / .828 | .820 / .800 | .028 |
| 120 | .889 / .864 | .898 / .870 | .864 / .849 | .021 |

Test kohortu: 8.261 öğrenci, 2.804 pozitif; KALDI 1.977, BIRAKTI 827 pozitif.

**Önemli okuma notu:** Sabit kohort 120. günde hâlâ kayıtlı öğrencilerden oluştuğu için buradaki BIRAKTI pozitifleri **120. günden sonra** bırakan, yani geç bırakan öğrencilerdir. Bu tablo erken bırakanlar hakkında bir şey söylemez.

**Bulgu 5: Erken uyarının bedel eğrisi.** 14. günde sinyal zayıf (test .675), 120. günde güçlü (.864). Kazancın büyük kısmı 14 ile 60. gün arasında geliyor; 60. gün, kazancın çoğunun alındığı ve hâlâ müdahale için zaman olan nokta. Hafta 9'da tek bir seçimle belirlenen kesim günü, bu eğriyle geriye dönük olarak gerekçelendi.

**Bulgu 6: Önce etkinlik, sonra not ve teslim.** 14. günde etkinlik tek başına tam modelle aynı; GENERAL − ETKİNLİK farkı testte .006'dan (14. gün) .061'e (60. gün) ve .075'e (90 ve 120. gün) çıkıyor. Not ve teslim bilgisi, ilk ödevler oluştukça asıl taşıyıcı oluyor.

**Bulgu 7: Geç bırakanlar her kesimde daha zor.** KALDI her kesimde BIRAKTI'dan kolay; fark en büyük 14. günde (test .064) ve 120. güne doğru azalıyor (.021). En büyük sıçrama BIRAKTI'da 14 → 30 arasında (doğrulama +.132, test +.068), yani ilk ödevlerin geldiği dönemde. Bu, Bulgu 2 ("bırakmanın erken izi teslimde") ile **uyumlu**, ama onu kanıtlamaz: aynı dönemde etkinlik verisi de birikiyor.

## 7. E4 · Literatürle kıyas

**Yöntem:** Yalnızca makalenin kendisinden ya da yayıncının resmî özetinden doğrulanan değerler alındı. Doğrulanamayan alanlar "doğrulanmadı" olarak bırakıldı; özet sitelerinden ya da başka çalışmaların aktarımından sayı alınmadı. Tablo bir sıralama değildir: metrikler, hedefler ve kesim noktaları farklı olduğu için sayılar birbirinin yerine konamaz.

| Çalışma | Tahmin anı | Bölme | Hedef | Demografik özellik | Bildirilen değer |
|---|---|---|---|---|---|
| **Bu çalışma** | 60. gün (E3: 14–120) | Zamansal: 2013J ile eğitim, 2014B doğrulama, 2014J test | Başarısız ∪ bırakmış; kesimden önce kaydını silenler dışarıda | Yok | ROC AUC test .792 (60. gün, GGG dahil); sabit kohortta 30. gün .711 |
| **Wu, Jia ve Pham (2026)**, *Frontiers in Education* 11 | 28. gün | Öğrenciye göre gruplanmış rastgele 80/20 ve ayrıca zamansal (2013 → 2014) | Başarısız ∪ sonradan bırakmış; 28. günden önce kaydını silenler dışarıda | Var (9 arka plan/idari özellik) ve yok, ikisi de raporlanmış | ROC AUC: tüm özellikler .775, yalnız davranış .750 (gruplanmış bölme); zamansal: .747 (tüm, RF), .709 (yalnız davranış, HistGB) |
| **Adnan vd. (2021)**, *IEEE Access* 9 | Dersin %0, 20, 40, 60, 80, 100'ü | Doğrulanmadı | Withdrawn / Fail / Pass / Distinction (çok sınıflı ve birleştirilmiş varyantlar) | Var | RF ortalama kesinlik: %20'de .79, %100'de .92 (doğruluk %20'de .79, %100'de .91) |
| ***Scientific Reports* (2025)**, "Accurate multi-category student performance forecasting at early stages of online education using neural networks" | Dersin yaklaşık %20'si | Doğrulanmadı | Distinction / Fail / Pass / Withdrawn | Var (demografik, ödev, tıklama) | Doğruluk %92 (yaklaşık %20'de) |

**Gözlem 1: Zaman noktası sayıyı belirliyor.** Adnan vd.'de başarı dersin %0'ından %100'üne doğru düzenli artıyor; bu, bizim E3 eğrisiyle (B8, B9) aynı biçim. Dersin tamamına ya da geç bir pencereye ait bir değer, 60. gündeki bir değerle karşılaştırılamaz.

**Gözlem 2: En yakın kurgu bağımsız olarak benzer sayılar veriyor.** Wu vd. (2026) bizimkine en yakın tasarım: erken bir sabit gün, kesimden önce bırakanların dışlanması, zamansal doğrulama ve demografik özelliksiz bir model. Zamansal aktarımdaki yalnız davranış modeli (.709, 28. gün) ile bizim 30. gün sabit kohort değerimiz (.711) çok yakın. Kurgular birebir aynı değil: test kümesi, kohort tanımı ve özellikler farklı. Bu bir doğrulama değil, sayılarımızın bu protokol ailesi için makul aralıkta olduğunun işareti.

**Gözlem 3: "Bırakmak daha zor" bulgusu bağımsız olarak tekrarlanıyor.** Wu vd.'de 28. günde hâlâ kayıtlı öğrenciler arasında sonradan bırakmayı tahmin etmek (.697), başarısızlığı tahmin etmekten (.720) daha zor; bırakmayan öğrenciler içinde başarısızlığı geçmeden ayırmak ise en kolay görev (.783). Bu, bizim B4'te ön kayda aykırı çıkan sonucumuzla aynı yönde. Aynı çalışmada bırakma tahmininin ödev teslim bilgisine, başarısızlık tahmininin etkinliğe daha çok dayandığı raporlanıyor; bu da bizim Bulgu 2 hipotezimizle ("bırakmanın erken izi teslimde") uyumlu. İki çalışma da nedensellik iddia etmiyor.

**Gözlem 4: Notlu ödevi olmayan dersler.** Wu vd.'de başka derslere en kötü aktarılan iki ders, tahmin penceresinde notlu ödevi olmayan GGG ve EEE. Bizim 60. günde GGG'yi notlu ödevsiz olduğu için bayrak kuralından dışlamamız ve E3'te 14. günde test döneminde hiç notlu ödev bulunmaması aynı yapısal soruna işaret ediyor.

**Gözlem 5 (hipotez): Bırakmanın neden bazı çalışmalarda "kolay" göründüğü.** *Scientific Reports* (2025) çalışması Withdrawn sınıfının erken aşamalarda yüksek isabetle bulunduğunu raporluyor. Bizim ve Wu vd.'nin tasarımında, tahmin anından önce kaydını silen öğrenciler çıkarılıyor; çünkü onların sonucu o an zaten belli. Bu öğrenciler örneklemde kalırsa "bırakan" sınıfının bir kısmı tanım gereği kolaylaşır. Çalışmanın örneklem kuralını doğrulamadığımız için bu bir açıklama önerisidir, tespit değildir.

**B11 (nitel beklenti):** "Yüksek değer bildiren çalışmaların çoğu dersin tamamına ya da daha geç bir pencereye ait veriyi, rastgele bölmeyi ya da demografik özellikleri kullanır." İncelenen iki yüksek değerli çalışma (Adnan vd., *Scientific Reports* 2025) demografik özellik kullanıyor; Adnan vd.'de en yüksek değerler dersin sonuna ait. Bölme türü doğrulanamadı. Wu vd. ise protokolün değeri nasıl değiştirdiğini kendi verisinde gösteriyor: kayıt düzeyinde rastgele bölme, test kayıtlarının %15,7'sinde aynı öğrencinin eğitimde de bulunmasına yol açardı; zamansal aktarımda değer .775'ten .747'ye iniyor. **Sonuç: destekleniyor, ancak örnek küçük (3 çalışma) ve bir alan (bölme türü) iki çalışmada doğrulanamadı.**

**Okul sistemi için not:** Wu vd. de demografik özellik kullanmamanın bedelini yaklaşık .024 AUC olarak ölçüyor ve bunun bir mahremiyet tercihi olduğunu, kendi başına adalet sağlamadığını vurguluyor. Bizim sistemimizde sosyokültürel özellik hiç kullanılmıyor; bu tercih aynı gerekçeyle savunulabilir, ama bir alt grup denetiminin yerini tutmaz. Gelecek çalışmalara eklenecek.

**Kaynaklar**
- Wu, M., Jia, J. ve Pham, T. T. (2026). Early warning of academic risk from the first four weeks of online learning activity and assessment performance: a leakage-controlled, demographic-data-minimizing study on the OULAD benchmark. *Frontiers in Education*, 11. doi:10.3389/feduc.2026.1917092
- Adnan, M. vd. (2021). Predicting at-risk students at different percentages of course length for early intervention using machine learning models. *IEEE Access*, 9, 7519–7539. doi:10.1109/ACCESS.2021.3049446
- Accurate multi-category student performance forecasting at early stages of online education using neural networks (2025). *Scientific Reports*. https://www.nature.com/articles/s41598-025-00256-3

## 8. Toplam

| Sonuç | Beklentiler |
|---|---|
| Tuttu (5) | B1, B3, B8, B9, B10 |
| Tutmadı (3) | B4, B5, B7: "model kolay olanı, kopanı buluyor" şüphesinin üç yüzü |
| Belirsiz (2) | B2, B6: tek sinyal grubunun gücü dönemler arasında yer değiştiriyor |
| Nitel (B11) | Destekleniyor; örnek küçük (3 çalışma), bölme türü iki çalışmada doğrulanamadı |

## 9. Sıradaki

- Grafikler: E1–E3 için figures.py üzerinden TR/EN PNG (sunum ve WEEK_11) ve rapor sayfasında etkileşimli karşılıkları.
- Rapor: "Ek analizler" sekmesi bu dosyayı ve ön kaydı yan yana gösterir; tutmayan beklentiler silinmez.
