# Hafta 10 — Veri Bilimi III: Ders bağlamı taşınır mı?

## Özet
Bu hafta, projenin başından beri taşıdığımız hipotezi test ettik: öğrencinin riski dersin bağlamına göre değişir ve bu bağlamı bilen bir model, yalnızca öğrenciye bakan bir modelden daha iyi tahmin eder.

Sonuç iki parçalı. **Desteklenen kısım:** dersler arası risk farkı büyük ve gerçek. **Desteklenmeyen kısım:** dersin geçmiş dönemlerinden üretilen özellikler, öğrenciyi kendi sınıfı içinde daha doğru sıralamaya katkı vermedi; test döneminde tahmini kötüleştirdi (ROC AUC farkı hgb −0,010 [−0,012; −0,007]). Bunun iki nedeni var: dersin taban oranı dönemden döneme kayıyor ve geçmiş sinyal çok az sayıda dönemden öğreniliyor.

Bu bulgular okul sistemi için somut bir tasarıma dönüştü: **sınıf içi ilk %20'yi bayraklayan, üç sinyalli, şeffaf bir kural.** Kural, modelin isabetlerinin %95–96'sını yakalıyor. Olasılık göstermiyor, notlu sınavı olmayan derste bayrak üretmiyor.

## 1. Neden bu deney?
Gerçek hayatta risk; derse, hocaya, hatta o hocanın o yılki tutumuna göre değişebilir. Aynı notlarla bir derste güvende olan öğrenci, finali zor geçen başka bir derste risk altında olabilir. Bu doğruysa yalnızca öğrenciye bakan genel bir model yanılır, bağlamı bilen bir model daha iyi sonuç vermelidir.

OULAD bu sorunun bir kısmını test etmeye izin veriyor:

| Boyut | OULAD karşılığı | Test edilebilir mi? |
|---|---|---|
| Ders | Modül kimliği ve dersin geçmiş dönemleri | Evet |
| Dönem | Sunum (2013B … 2014J): "o yılın koşulları"nın kaba karşılığı | Evet |
| Hoca | Veri setinde yok | Hayır |

Hoca boyutu bu veriyle test edilemedi; gelecek çalışmaya aktarıldı.

## 2. Deney tasarımı
"Bağlam işe yarıyor" demek için tek bir karşılaştırma yetmez: aynı kazancı yalnızca dersin adını bilmek de verebilir. Bu yüzden üç kol kurduk; iki ek kontrolü ise ilk sonuçlardan sonra ekledik.

| Set | Ne bilir? | Sorduğu soru |
|---|---|---|
| GENERAL | Öğrencinin ödev ve etkinlik izi (60. güne kadar) | Temel çizgi |
| GENERAL_MODULE | + dersin kimliği | Dersi tanımak yeter mi? |
| HISTORY | + dersin geçmiş dönemleri (ödev zorluğu, geçmiş risk oranı) | Dersin geçmişini bilmek işe yarar mı? |
| HISTORY_SLOT * | HISTORY, geçmiş risk oranı olmadan | Sorun tek bir sütunda mı? |
| GENERAL_REL * | Sınıf içi göreli konum (yüzdelik sıralar) | Bağlam sınıf içi sıra olarak taşınır mı? |

\* İlk test sonuçları görüldükten sonra eklendi; bu yüzden **keşifsel**. Bu noktadan sonra test dönemi donduruldu ve doğrulama dönemi ayrıca raporlandı.

**Protokol.** İki model türü (lojistik regresyon, HistGradientBoosting). Ayar yalnızca train içinde ve zamansal yapıldı: 2013J'de eğitilip 2014B'de log loss ile seçildi. Seçilen ayarla train'in tamamında (2013J + 2014B) eğitilen model, 2014J'de bir kez değerlendirildi. Belirsizlik için modül içinde tabakalı bootstrap kullanıldı (B = 1.000, seed 42); setler arası farklar aynı örneklemler üzerinde eşli olarak hesaplandı.

## 3. Bulgular

### 3.1 Ders geçmişi tahmini iyileştirmedi
| Set | hgb ROC AUC [%95] | logreg ROC AUC | Brier (hgb) |
|---|---|---|---|
| GENERAL | 0,792 [0,783–0,801] | 0,786 | 0,177 |
| GENERAL_MODULE | 0,799 [0,790–0,808] | 0,805 | 0,175 |
| HISTORY | 0,783 [0,773–0,792] | 0,773 | 0,190 |
| HISTORY_SLOT | 0,783 [0,774–0,793] | 0,775 | 0,190 |
| GENERAL_REL | 0,804 [0,795–0,813] | 0,792 | 0,169 |

E�li fark HISTORY − GENERAL (ROC AUC): hgb −0,010 [−0,012; −0,007], logreg −0,013 [−0,015; −0,012]. Aralıklar 0'ı içermiyor; Brier de kötüleşiyor.

### 3.2 Hata mı, bulgu mu?
Sonuç hipotezin tersine çıkınca önce kodu sorguladık:
- **Ödev eşlemesi doğru.** Ödevler dönemler arasında aynı sırayla geliyor, yalnızca birkaç gün kaymış.
- **Geçmiş risk oranı train'de yalnızca 8 farklı değer alıyor.** Model bu sütunu 13.639 satırdan değil, 8 sunumdan öğreniyor.
- **Risk zamanla düştü.** Train'de %42,6, testte %38,3. Örneğin BBB'de geçmiş oran 0,42, testteki gerçek oran 0,339.

Kod hatası yok; bulgu gerçek.

### 3.3 Bağlam taban oranda var, ama kayıyor
![Test döneminde modül bazında gerçek oran ve ortalama tahmin](figures/fig02_oran_kaymasi_tr.png)

*Her satır bir modüldür. Noktalar gerçek oranı ve genel, modül bilgili ve geçmişli setlerin ortalama tahminini gösterir. Noktalı çizgiler aynı modüldeki değerleri birleştirir.*

AAA'da gerçek oran 0,256 iken GENERAL 0,476, HISTORY 0,574 tahmin ediyor; dersin kimliği (0,287) bu farkı düzeltiyor. BBB'de üç set de 0,52–0,57 arası tahmin ediyor, gerçek oran 0,339. Geçmiş risk oranı test döneminde tahmini yukarı çekiyor. **Karar:** sistemde mutlak olasılık gösterilmez.

### 3.4 Testte önde olan set, doğrulamada sonda
![Doğrulama ve testte sıralama değişiyor: beş set için ROC AUC](figures/fig01_roc_egim_tr.png)

*Her çizgi bir özellik setinin doğrulama ve test ROC AUC değerini birleştirir. Kalın çizgiler genel ve göreli genel setlerdir; diğerleri incedir. Yalnızca test noktasında yüzde doksan beş aralık vardır. Doğrulama noktasında aralık yoktur.*

GENERAL_REL testte en yüksek (0,804), doğrulamada en düşük (0,782) ROC AUC'ye sahip. Bu set test sonuçlarına bakılarak tasarlanmıştı. Bağımsız dönemde tutmaması, testteki kazancın büyük ölçüde o döneme özgü olduğunu gösteriyor. **Karar:** GENERAL_REL benimsenmedi. **Ders:** test setine bakarak yapılan tasarım, şans eseri kazananı seçebilir.

### 3.5 Sınıf içinde setler neredeyse aynı
| Set | Modül içi ROC AUC, test 2014J | Modül içi ROC AUC, doğrulama 2014B |
|---|---|---|
| GENERAL | 0,796 | 0,810 |
| GENERAL_MODULE | 0,797 | 0,811 |
| HISTORY | 0,793 | 0,811 |
| HISTORY_SLOT | 0,794 | 0,811 |
| GENERAL_REL | 0,800 | 0,795 |

Değerler modüller arası ağırlıksız ortalamadır (hgb); modül bazındaki n ve pozitif sayıları notebook 03'te. Farklar binde birkaç düzeyinde ve sıralama dönemden döneme değişiyor. **Kimin riskli olduğunu bulmada hiçbir bağlam tarifi iki dönemde tutarlı katkı vermedi.** Bağlamın etkisi sınıf içi sıralamada değil, dersler arası seviyede, yani taban oranda.

### 3.6 Görülmemiş ders
![Eğitimde görülmeyen derste ortalama tahmin ve gerçek oran](figures/fig03_gorulmemis_ders_tr.png)

*Her satır, eğitimde hiç görülmeyen bir derstir. Noktalar gerçek oranı ve genel ile göreli genel setlerin ortalama tahminini gösterir. Vurgulu satır, kesim gününe kadar notlu ödevi olmayan derstir.*

Her ders sırayla eğitimden çıkarıldı (leave-one-module-out). Ortalama ROC AUC: GENERAL 0,784, GENERAL_MODULE 0,785, GENERAL_REL 0,787, HISTORY 0,782. Dersin kimliği yeni bir derse taşınamıyor; farklar küçük ve bu analizde aralık hesaplanmadı.

GGG'de model riski ~0,93 tahmin ediyor; gerçek oran 0,36. GGG'nin 60. güne kadar notlu ödevi yok ve model "henüz ödev yok" durumunu "ödev teslim etmedi" gibi okuyor (Hafta 9, veri notu 1). **Kural:** sınavı yapılmamış derste bayrak gösterilmez.

### 3.7 Model neye dayanıyor?
![Modelin en çok dayandığı özellikler](figures/fig05_shap_tr.png)

*Sol panel özelliklerin ortalama mutlak SHAP değerini karşılaştırır. Sağ panel en yüksek ortalama mutlak değere sahip özelliğin gözlenen değerini SHAP ile birlikte gösterir. Pozitif SHAP, modelin tahmini riski artırdığı yönü gösterir; nedensel bir etki değildir.*

GENERAL hgb için TreeExplainer, testin tamamı (8.837 satır). Ortalama |SHAP| (log-odds): `n_unsubmitted` 0,586, `score_mean` 0,462, `vle_days_to_cutoff` 0,443. Okul sistemindeki karşılıkları: girilmeyen sınav, not ortalaması ve devam. SHAP modelin davranışını anlatır; "teslim etmemek riske yol açar" anlamına gelmez.

### 3.8 Karar kuralı: sınıf içi ilk %20
![Bayrak oranına göre kesinlik: genel ve sınıf içi sıralama](figures/fig04_kapasite_tr.png)

*Çizgiler bayrak oranı değiştikçe kesinliği gösterir. Biri öğrencileri birlikte sıralar, diğeri her modülün içinde sıralar. Kesikli çizgi seçilen bayrak oranını, açık bant sınıf içi sıralamanın önde olduğu aralığı gösterir.*

%20 bayrak oranında kesinlik: global sıralamada 0,797, sınıf içi sıralamada 0,818. Sınıf içi sıralama %10–35 aralığında önde; %5'te global önde (0,984 / 0,962); %45'ten sonra ikisi eşit. Sınıf içi sıra taban oran kaymasından etkilenmez ve her öğretmene eşit izleme kapasitesi verir. Bedeli de var: düşük riskli sınıflarda isabet düşer (AAA 0,62).

### 3.9 Sisteme köprü: şeffaf kural ile model
Kural, hiçbir sonuca bakılmadan önceden sabitlendi:
- Her sınıfta üç sinyalin yüzdelik sırası alınır: girilmeyen ödev sayısı, not ortalaması (ters) ve aktif gün sayısı (ters).
- Üçünün ortalamasına göre sınıf içi ilk %20 bayraklanır.
- Notlu ödevi olmayan derste bayrak yoktur.
- Kural eğitilmez ve sonuç bilgisini (`at_risk`) kullanmaz.

| Dönem | Kural kesinlik | Model (GENERAL hgb) kesinlik | İsabet kural / model |
|---|---|---|---|
| 2014B | 0,900 | 0,934 | 975 / 1.012 |
| 2014J | 0,787 | 0,829 | 1.283 / 1.352 |

Sınıf içi %20 bayrak; GGG her iki dönemde de hariç. Model iki dönemde de önde; 11 modül-dönemin 11'inde modül içi ROC AUC'si daha yüksek (fark 0,001–0,029). Kural ise modelin isabetlerinin %95–96'sını yakalıyor.

Okul sisteminde, hangi öğrencinin sonunda başarısız olduğunu gösteren etiketli bir geçmiş yok; dolayısıyla sistemde model zaten bir seçenek değildi. Bu karşılaştırmayla ölçtüğümüz şey, **şeffaflığın bedeli**: yaklaşık 4 puan kesinlik. Karşılığında öğretmen her bayrağın gerekçesini okuyabiliyor ve OULAD'dan sisteme hiçbir veri ya da model taşınmıyor.

## 4. Kararlar
| Karar | Kanıt |
|---|---|
| HISTORY reddedildi | İki model türünde eşli fark negatif, aralık 0'ı içermiyor |
| GENERAL_REL benimsenmedi | Doğrulamada en düşük; testteki kazanç keşifsel |
| Referans model: GENERAL hgb | Sade, iki dönemde istikrarlı, her derse taşınabilir |
| Olasılık gösterilmez | Taban oran dönemden döneme kayıyor |
| Sınıf içi ilk %20 | Kapasite eğrisi: %10–35'te sınıf içi önde |
| Sistemde şeffaf 3 sinyalli kural | Okulda etiket yok; bedeli ~4 puan kesinlik |
| Sınavsız derste bayrak yok | GGG: görülmemiş derste ~0,93 tahmin |

## 5. Hipotezin cevabı
- **Desteklenen:** Dersler arası risk farkı büyük ve gerçek. Dersin kimliği, test döneminde kalibrasyonu ve genel sıralamayı iyileştiriyor.
- **Desteklenmeyen:** Dersin geçmişini bilmek, öğrenciyi sınıfı içinde daha doğru sıralamaya katkı vermiyor. Geçmiş risk oranı zamanla kayıyor ve az sayıda dönemden öğreniliyor.
- **Test edilemeyen:** Hoca ve hocanın o yılki tutumu (OULAD'da yok). Okul verisinde sonuç etiketleri biriktikçe test edilebilir.

Kısaca: risk derse göre değişiyor, ama bu bilgi dersin geçmişinden öğrenciye taşınmıyor. İşe yarayan, öğrenciyi kendi sınıfı içinde değerlendirmek.

## 6. Açıklama kaydı
Bulguları yorumlarken iki açıklama önerdik; ikisi de kontrolde tutmadı. Doğrulanmayan hiçbir açıklama sonuç olarak yazılmadı.

| Tahmin | Kontrol | Sonuç |
|---|---|---|
| Kötüleşmenin kaynağı yalnızca geçmiş risk oranı | O sütun çıkarıldı (HISTORY_SLOT): sonuç aynı kaldı | Yanlış: geçmiş ödev özellikleri de genelleşmiyor |
| GENERAL_REL yalnızca seviyeyi kaçırıyor, sıralaması sağlam | Doğrulamada sıralama (ROC AUC) ölçüldü: en düşük | Yanlış: set benimsenmedi |

## 7. Hata kayıtları
**Hata 1 — grafik alt metni**
- Belirti: görülmemiş ders grafiğinin alt metni, vurgulu satırı "eğitimde yer almayan ders" olarak tanımlıyordu.
- Kök neden: bu analizde her satır eğitimde görülmeyen bir ders. GGG'nin vurgulanma nedeni farklı: 60. güne kadar notlu ödevi yok.
- Düzeltme: başlık, alt metin (TR/EN) ve GGG satırına açıklama notu güncellendi.
- Durum: doğrulandı (figures.json ve yeniden üretilen grafik kontrol edildi).

## 8. Sınırlılıklar
- Tek kurum (Open University), tek ülke.
- Fail ve Withdrawn aynı sınıfta; ikisi farklı süreçler olabilir.
- Yalnızca bir doğrulama dönemi var; dönemler arası istikrar iki noktadan değerlendirildi.
- LOMO sonuçlarında belirsizlik aralığı hesaplanmadı.
- Test dönemi birden çok kez görüldü. Bu yalnızca değerlendirme amaçlıydı; sonradan eklenen setler bu yüzden keşifsel olarak işaretlendi.
- SHAP nedensellik değildir.
- Kuralın ilk sinyali olan "girilmeyen sınav"ın okul şemasındaki karşılığı henüz doğrulanmadı.

## 9. Çıktılar ve doğrulama
- **Kod:** `data_science/oulad/` altında `model.py`, `relative.py`, `explain.py`, `figures.py`, `rule.py`; raporlar `data_science/oulad/reports/` altında (`model_metrics.json`, `explain.json`, `rule_metrics.json`, `figures/week10/`). `shap==0.54.1` requirements.txt'ye eklendi.
- **Notebook:** `notebooks/03_oulad_model.ipynb`, `03_oulad_model_eng.ipynb` ve `notebooks/html/` altındaki HTML'ler. Notebook'ta model, metrik ya da grafik kodu yok; her şey paketten çağrılıyor ve aynı PNG'ler bu raporda ve sunumda kullanılıyor.
- **Testler:** 266 passed, 1 warning.
- **Notebook çalıştırma:** kullanıcı terminalinde baştan çalıştı (iki notebook toplam 3 dk 42 sn); hata hücresi 0. HTML'ler notebook'lardan sonra üretildi ve alt metin uyarısı yok. OZET hücresindeki değerler ham çıktılarla birebir aynı.

```
python -m data_science.oulad.model --lomo
python -m data_science.oulad.explain
python -m data_science.oulad.figures
python -m data_science.oulad.rule
python -m pytest -q | tail -3          # 266 passed, 1 warning
```

## 10. Açık konular
- `n_unsubmitted` ↔ "girilmeyen sınav": okul şemasında doğrulanacak (kuralın ilk sinyali).
- pytest uyarısı (StarletteDeprecationWarning, httpx) giderilmedi.
- Alternatif metin: notebook 03'te çözüldü; 01 ve 02'de açık.
- Hafta 6 hata 4; Hafta 7 m5 ve c4 açık.

## 11. Hafta 11
- Risk sekmesi = şeffaf kural: sınıf içi ilk %20, her bayrakta gerekçe metni; olasılık yok; sınavı olmayan derste bayrak yok.
- Asistana `get_risk` aracı: RLS'ye uyar, nedensellik uydurmaz.
- Veri Bilimi sekmesi (notebook özetleri), testler, Docker, güvenlik.
