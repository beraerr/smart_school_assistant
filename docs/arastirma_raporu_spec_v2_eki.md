# Araştırma raporu: spec v2 eki — Ek analizler sekmesi

Bu ek `docs/arastirma_raporu_spec_v2.md` ile birlikte okunur; çakışırsa bu ek geçerlidir. Veriler paketteki `ek.*`, `figures.captions.week11` ve mevcut alanlardan gelir. Metinlerde elle yazılmış rakam yoktur; `{...}` alanları S görevlerinde paket anahtarlarına bağlanır (v1/v2'deki gibi, eşlemesi raporlanır).

## 1. Sekme sırası (hikâye omurgası)

| Kimlik | TR | EN | Omurgadaki yeri |
|---|---|---|---|
| ozet | Özet | Summary | Giriş |
| veri | Veri setleri | Datasets | Zemin |
| uci | UCI keşif | UCI exploration | Sezgi ve ilk hata |
| oulad | OULAD keşif | OULAD exploration | Bağlam hipotezi |
| model | Modelleme | Modelling | İlk cevap ve yöntem kararı |
| kural | Karar kuralı | Decision rule | Kurala geçiş |
| **ek** | **Ek analizler** | **Further analyses** | **Dönüm noktası: kendi çalışmamızı sorgulamak** |
| hoca | Hoca etkisi | Teacher effect | Sonuç: ne ölçülebilir, ne ölçülemez |
| sistem | Sisteme köprü | Bridge to the system | Uygulamadaki karşılığı |
| hatalar | Hatalar ve düzeltmeler | Errors and fixes | Güvenilirlik |
| kaynak | Sınırlar ve kaynaklar | Limits and sources | Kapanış |

Özet sekmesindeki "Araştırma yolculuğu" (Z1) zaman çizelgesine beşinci durak eklenir:

| Durak | TR | EN |
|---|---|---|
| H11+ | **Kendimizi sorguladık.** "Çalışma çok doğrusal; model belki yalnızca dersi bırakanı buluyor" şüphesi 10 beklentiyle önceden yazıldı, md5 ile mühürlendi ve sınandı. Şüphe çürüdü. | **We questioned ourselves.** The suspicion that the work was too linear and the model might only find students who drop out was written as 10 expectations, sealed with md5, and tested. The suspicion did not hold. |

Özet sekmesindeki "Gösterebildiklerimiz" listesine eklenir:
- TR: Model ve kural, dersi bırakacak öğrenciden çok, devam edip başarısız olacak öğrenciyi biraz daha yüksek oranda buluyor.
- EN: The model and the rule find students who will stay and fail at a somewhat higher rate than students who will drop out.

## 2. Ek analizler sekmesi (`ek`)

**Bu bölümde**, TR: Buraya kadar çalışma tek bir hat üzerinde ilerledi: tek bir kesim günü, tek bir hedef, tek bir özellik paketi. Bu sekmede kendi sonucumuzu sorguladık: model gerçekten zorlanan öğrenciyi mi buluyor, yoksa yalnızca dersi çoktan bırakmış olanı mı? Beklentilerimizi koşmadan önce yazdık ve mühürledik; sonra sınadık.
EN: Until here the work moved along a single line: one cutoff day, one target, one feature bundle. In this tab we questioned our own result: does the model really find struggling students, or only those who have already dropped out? We wrote our expectations before running anything, sealed them, and then tested them.

### 2.1 Düşünce haritası (statik akış, HTML/Altair)

Dört kutu ve oklar; her kutuda "Ne bulduk" ve "Neyi eksik bıraktı" iki satırı (ön kayıt bölüm 1 tablosundan). Son kutunun altında vurgulu satır:
TR: **Şüphe:** Hedef "başarısız ya da bırakmış". Bırakan öğrenci sisteme girmeyi ve ödev teslim etmeyi de bırakır; model belki yalnızca bunu görüyor.
EN: **The suspicion:** The target is "failed or withdrew". A student who withdraws also stops logging in and submitting; perhaps that is all the model sees.

Akışın sağında dört soru kartı (E1–E4), ön kayıt bölüm 1'deki "Cevapladığı soru" metinleriyle.

### 2.2 Ön kayıt (etkileşimli açılış)

Metin, TR: Analizleri koşmadan önce 10 beklentiyi sayısal ölçütleriyle yazdık ve dosyaların md5 değerini kaydettik. Analiz kodu, bu dosyalar kayıttan sonra değiştiyse çalışmayı reddediyor. Bir beklenti ancak iki dönemde de (doğrulama ve test) tutarsa "tuttu", ikisinde de tutmazsa "tutmadı" sayıldı; dönemler ayrışırsa "belirsiz".
EN: Before running the analyses we wrote 10 expectations with numeric criteria and recorded the files' md5 values. The analysis code refuses to run if those files changed after registration. An expectation counted as "held" only if it held in both periods (validation and test), "did not hold" if it failed in both, and "inconclusive" if the periods disagreed.

**Görsel P1 (etkileşimli):** fig07a'nın kart düzeni (10 kart; kimlik, kısa ad). Kartların üstünde tek düğme: TR "Sonuçları göster" / EN "Reveal results". Basılınca kartlar sonuç metni ve renkle (fig07 düzeni) açılır; tekrar basınca kapanır. Varsayılan: kapalı. Kartın üzerine gelince ön kayıttaki tam beklenti metni ve ölçüt görünür.

**Mühür tablosu (açılır):** `ek.pre_registration`: dosya, md5, zaman, sırayla. Altında TR: "Ek dosya koşudan önce bir kez güncellendi; iki kayıt da duruyor." EN eşdeğeri.

Açılış sonrası özet satırı: TR "{tuttu} tuttu, {tutmadı} tutmadı, {belirsiz} belirsiz." (sayılar `ek.summary`).

### 2.3 Şüphe çürüyor (E2)

Metin, TR: İlk soru: kim daha kolay bulunuyor? "Başarısız" ile "bıraktı"yı ayrı ayrı tahmin ettik. Beklentimiz bırakanların daha kolay bulunacağıydı (B4). Tersi çıktı: iki dönemde de başarısız olacak öğrenciyi bulmak daha kolay.
EN: First question: who is easier to find? We predicted "failed" and "withdrew" separately. We expected withdrawals to be easier (B4). The opposite held: in both periods, students who will fail are easier to find.

**Görsel X1 (etkileşimli, fig03 karşılığı):** üç pano (referans, KALDI, BIRAKTI); satırlar GENERAL, NOT, TESLİM, ETKİNLİK; test dolu + aralık, doğrulama boş; dönem gösterimi aç/kapa.

**Görsel X2 (etkileşimli, fig04 karşılığı):** dönem başına iki çubuk, `ek.recall_by_outcome`; çubuk etiketi "%yakalama · n / pozitif". Altında TR: "Kural, bırakanların da yaklaşık üçte birini yakalıyor; ama başarısız olacakları biraz daha yüksek oranda buluyor. Bu bir 'kopmuş öğrenci dedektörü' değil."

Bulgu kutusu TR: **Model ve kural işi kolay olanı yapmıyor.** Dersi sürdürüp başarısız olacak öğrenciyi, bırakacak öğrenciden daha kolay ve biraz daha yüksek oranda buluyorlar.

### 2.4 Bilgi nerede? (E1)

Metin, TR: Öğrencinin izini dört gruba ayırdık: notlar, ödev teslim davranışı, çevrim içi etkinlik ve kayıt tarihi. Hiçbir grup tek başına tam modele ulaşmıyor (B1). Not ve teslim birlikte ise tam modele çok yaklaşıyor (B3). Hangi tek grubun en güçlü olduğu ise dönemden döneme değişiyor (B2 belirsiz): tek bir sinyale güvenmek, Modelleme sekmesindeki "testte birinci, doğrulamada sonuncu" dersinin küçük bir tekrarı olurdu.
EN: equivalent.

**Görsel X3 (etkileşimli, fig02 karşılığı):** setler × ROC AUC; model seçici (hgb / logreg); dönem gösterimi.
Bulgu kutusu TR: **Okul için:** Risk işaretinin asıl taşıyıcısı devamsızlık değil, not ve ödev kaydı. Okulda bugün teslim kaydı yok; bu çalışma onun en değerli eksik sinyal olduğunu gösteriyor.

### 2.5 Ne kadar erken? (E3)

Metin, TR: Erken uyarının bir bedeli var: ne kadar erken uyarırsak, o kadar az bilgiyle uyarırız. Aynı hattı 14, 30, 60, 90 ve 120. günler için koştuk. Başarı her adımda arttı (B8), kazancın çoğu ilk iki ayda geldi (B9) ve 14. günde elde yalnızca etkinlik vardı (B10).
EN: equivalent.

Koşudan önceki karar kutusu (sarı), TR: "Koşmadan önce fark ettik: 14. günde test döneminde hiçbir derste notlu ödev yok. 'Notlu ödevi olmayan sınıfta bayrak yok' kuralı okul sisteminin kuralıdır, modelin değerlendirme kuralı değil; bu yüzden E3'te uygulanmadı. Karar, sonuçlar görülmeden ek bir ön kayıt dosyasına yazıldı."

**Görsel X4 (etkileşimli, fig05 karşılığı):** x = kesim günü, y = ROC AUC; GENERAL ve ETKİNLİK; görünüm seçici: "Sabit kohort" (varsayılan) / "Her kesimin kendi örneklemi"; dönem gösterimi; GENERAL ile ETKİNLİK arası taralı ve "not ve teslim katkısı" etiketi; 60. gün dikey çizgi "seçilen kesim". Kesim gününe gelince satır sayısı ve pozitif sayısı.
**Görsel X5 (etkileşimli, fig06 karşılığı):** KALDI ve BIRAKTI; altında kalıcı not: TR "Sabit kohortta 'bırakan' = 120. günden sonra bırakan."

Bulgu kutusu TR: **60. gün geriye dönük olarak gerekçelendi.** Kazancın çoğu 14 ile 60. gün arasında geliyor; 60. gün, kazancın çoğunun alındığı ve hâlâ müdahale için zaman olan nokta.

### 2.6 Başkaları ne buldu? (E4)

Metin, TR: Yayınlarda OULAD için %90'ın üzerinde değerler görülüyor; bizim test değerimiz yaklaşık 0,79. Fark büyük ölçüde zaman noktasından, bölme yönteminden ve demografik özellik kullanımından geliyor. En yakın tasarımdaki bağımsız bir çalışma (Wu, Jia ve Pham, 2026) hem sayılarımızla aynı aralıkta hem de "bırakmak daha zor" bulgusunu kendi verisinde tekrarlıyor.
EN: equivalent.

**Tablo L1 (statik):** `docs/ek_analizler_sonuc.md` bölüm 7'deki tablo (çalışma, tahmin anı, bölme, hedef, demografik özellik, bildirilen değer); "doğrulanmadı" hücreleri gri ve öyle yazılı. Altında beş gözlem kısa hâliyle ve kaynakça. Bu tablodaki sayılar dış kaynaklardan geldiği için paket yer tutucusu kullanılmaz; S görevinde metin sabiti olarak `arastirma_metin.py`'ye yazılır ve kaynak satırıyla birlikte durur. (Bu, "metinde elle rakam yok" kuralının tek istisnasıdır; istisna kodda yorumla belirtilir.)

### 2.7 Kapanış: ne değişti, ne değişmedi

İki sütun.
- TR **Değişti:** Şüphemiz çürüdü; sistemin neyi yakaladığını artık biliyoruz. 60. gün seçimi gerekçelendi. Okul için en değerli eksik sinyal belirlendi: ödev teslim kaydı.
- TR **Değişmedi:** Sistemdeki kural. Ek analizler bir şeyi düzeltmek için değil, anlamak için yapıldı; bir değişiklik önerisi çıkarsa yeni ve önceden yazılmış ölçütlerle ayrıca sınanır.
EN eşdeğeri.

## 3. Hatalar ve düzeltmeler sekmesine eklenen kartlar

| # | Başlık TR / EN | Tür |
|---|---|---|
| 9 | Notebook 02 ve 03'te hesaplar hücrelerin içindeydi / Analysis logic lived inside notebook 02 and 03 cells | Yeniden üretilebilirlik |
| 10 | Sanal ortam kopyalanmıştı; notebook başka ortamda çalışıyordu / The virtual environment was a copy; notebooks ran in another environment | Yeniden üretilebilirlik |
| 11 | Ön kayıt kontrolü ilk kayda bakıyordu / The pre-registration check read the first record | Yöntem (koşu durdu, dosyalar değişmedi) |
| 12 | Ana şüphe çürüdü / The main suspicion did not hold | Yorum (hata değil, çürüyen hipotez) |

Kart 9 "Sonra" TR: "Fonksiyonlar `data_science` paketine taşındı; notebook'lar yeniden çalıştırıldı ve 14/14 ve 10/10 kod hücresinin çıktısı birebir aynı çıktı."
Kart 10 "Sonra" TR: "Ortamın kendi çekirdeği kaydedildi; notebook 03 doğru ortamda yeniden çalıştırıldı ve çıktılar aynı çıktı. `explain.json`'un TreeExplainer ile üretildiği doğrulandı."
Kart 12 "Sonra" TR: "B4, B5 ve B7 tutmadı. Çalışmanın en önemli bulgularından biri bu oldu."

## 4. Görevler (spec v2 bölüm 13'e ek)

- **S1 (iskelet):** 11 sekme bu ekteki sırayla; Ek analizler sekmesinin bütün metinleri, kutuları, L1 tablosu ve mühür tablosu S1'e dahildir.
- **S5'e ek:** P1 (açılışlı beklenti kartları), X1–X5.
