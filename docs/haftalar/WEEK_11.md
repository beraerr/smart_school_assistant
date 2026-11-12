# Hafta 11 — Entegrasyon ve Sağlama

## Özet
Bu hafta dört hat üzerinde çalıştık. Okulun mock verisini MEB takvimine göre yeniden ürettik ve sisteme bir zaman kapısı ekledik: sistem artık demo "bugün"ünden sonraki veriyi görmüyor. Asistanı sıkılaştırdık: her sayı bir sorguya dayanmak zorunda, dayanaksız sayıda bir düzeltme turu ve geri dönüş var. SQL doğrulayıcıdaki iki açığı kapattık. Hafta 8–10'daki çalışmayı, okul sistemindeki risk kuralının gerekçesi olarak girişsiz bir araştırma sayfasında topladık.

Son olarak kendi sonucumuzu sorguladık: model gerçekten zorlanan öğrenciyi mi buluyor, yoksa dersi çoktan bırakmış olanı mı? 10 beklentiyi koşmadan önce yazıp md5 ile mühürledik, sonra iki dönemde sınadık. **Sonuç: 5 tuttu, 3 tutmadı, 2 belirsiz.** Şüphe çürüdü: model ve kural, başarısız olacak öğrenciyi bırakacak öğrenciden daha kolay ve biraz daha yüksek oranda buluyor. Sistemdeki kural değişmedi.

## 1. Veri ve zaman

### 1.1 Mock veri yeniden üretildi
Mock veri Hafta 7'den beri dondurulmuştu. Bu hafta dondurmayı kaldırdık; karar kaydı aşağıda.

- **Neden:** Eski mock'ta notlar okul açılmadan önceye düşüyordu; tarih sorularının demoda karşılığı yoktu. Ayrıca üretici bazı koşulları öğrenci adına göre özel kodla sağlıyordu.
- **Ne yapıldı:** `scripts/mock_uret.py` deterministik (seed 20260914), 14.09.2026–25.06.2027 öğretim yılı. 6 sınıf × 6 öğrenci, 6 öğretmen, 1.440 not (dönem başına 2 performans + 2 yazılı), 6.444 devamsızlık satırı (179 okul günü). md5 `de7da13d07102011882382e467968e24`.
- **Güvenceler:** Devamsızlık profil parametreleriyle üretiliyor; isimle dallanmayı bir AST testi yasaklıyor. Demo hikâyeleri (bayraklı ve bayraksız öğrenciler, yıl ortalaması 50'nin altında bir öğrenci) bir üretim kapısıyla korunuyor.
- Eski mock arşivde: `database/archive/mock_data_hafta07-11.json`.

### 1.2 Zaman kapısı
| Bileşen | Ne yapar? |
|---|---|
| `backend/app/services/takvim.py` | MEB 2026–2027: 1. dönem 14.09–22.01, ara tatiller 16–20.11 ve 8–12.03, yarıyıl 25.01–05.02, 2. dönem 08.02–25.06; resmî tatiller ve bayramlar |
| `DEMO_TODAY` (`.env`) | Demonun "bugün"ü; boşsa Europe/Istanbul tarihi |
| `app.today` + RLS | Notlar ve devamsızlık için kısıtlayıcı (RESTRICTIVE) politikalar |
| `student_rank` | Tarih koşulu; sıralamada boş değerler sona |
| Risk penceresi | Risk, içinde bulunulan dönemin penceresinden hesaplanır |

**Bir sızıntı kapandı.** `students.total_absences` yıl sonu toplamını taşıyordu: ekimde haziranın devamsızlığı görünüyordu ve attendance tablosuyla tutmuyordu. Sütun kaldırıldı. Devamsızlık her yerde attendance'tan, mazeretli ve mazeretsiz ayrı hesaplanıyor.

## 2. Asistan ve SQL doğrulayıcı

### 2.1 Asistan
- **Tarih bloğu:** Her istekte bugün, dönem, görünür veri aralığı ve takvim özeti modele verilir.
- **Sayı denetimi:** Türetilmiş sayılar SQL'de hesaplanır (LAG izinli). Önceki asistan mesajlarındaki sayılar izinli. Dayanaksız sayı çıkarsa reddedilen sayılar listelenir ve bir ek araç hakkı verilir (toplam en çok 4).
- **Geri dönüş:** Düzeltme turu da başarısızsa cevap yerine sorgu sonuçları gösterilir (arayüzde sorgu bölümü açık gelir).
- **Loglar:** `ungrounded_number`, `assistant_fallback`, `run_sql_exception` olayları yapılandırılmış log olarak yazılır.
- **Bilinen sınır:** abs() eşleşmesinde yön kontrol edilmiyor.

### 2.2 SQL doğrulayıcı
| Sorun | Etkisi | Düzeltme |
|---|---|---|
| AND, CASE, NULLIF fonksiyon sanılıyordu | Geçerli sorgular reddediliyor, asistan "Kayıtlara ulaşamadım" diyordu | Operatörler fonksiyon denetiminden ayrıldı; NULLIF izinli |
| CTE içinde DELETE geçebiliyordu (denetim 6.2) | Salt okunur güvencesi delinebiliyordu | CTE ve alt sorgular dahil her yerde DML, DDL, INTO ve kilit reddi |

Doğrulayıcı yalnızca public şemaya izin veriyor. Yeni bir test, asistan talimatındaki her örnek SQL'in doğrulayıcıdan geçtiğini sınıyor.

## 3. Arayüz
- Logo kenar menü başlığında; Türksat footer'ı sabit; üst çubukta Demo, Rol, Dil ve Çıkış tek ölçü sistemiyle aynı kutu stilinde.
- Girişte kenar menü açık geliyor; giriş ekranındaki önizleme kartının yerine "Araştırmayı incele →" düğmesi geldi (oturum ve dil korunur).
- Rol bazlı örnek soru önbelleği ile favicon ve config.toml görevinin durumu kesin değil; Hafta 12'de doğrulanacak.

## 4. Araştırma sayfası (`?sayfa=arastirma`)
Okul sistemindeki risk sekmesi bir tahmin modelinden değil, açık veriyle sınanmış şeffaf bir kuraldan gelir. Bu sayfa o kurala nasıl varıldığını, neyin işe yaradığını ve neyin hâlâ bilinmediğini gösterir.

![Araştırma sayfasının Özet sekmesi](figures/ekran_ozet_tr.png)

*Özet sekmesi. Ekran görüntüsü %20 biçim düzeltmesinden önce alındı.*

- Girişsiz; okul verisine ve backend'e dokunmaz. Sentetik okul verisinden bulgu çıkarılmaz.
- 11 sekme: Özet, Veri setleri, UCI keşif, OULAD keşif, Modelleme, Karar kuralı, Ek analizler, Hoca etkisi, Sisteme köprü, Hatalar ve düzeltmeler, Sınırlar ve kaynaklar. Her sekmede "Bu bölümde" kutusu var.
- Tek paket: `scripts/arastirma_paketi.py` → `frontend/assets/arastirma/arastirma.json` + 52 görsel. Metinlerdeki sayılar elle yazılmıyor; yer tutucular paketten çözülüyor (`coz`), türetilen değerler (`turev.*`) sayfa katmanında hesaplanıyor.
- Notebook 01, 02 ve 03'teki hücre içi hesaplar pakete taşındı (`data_science/absence.py`, `oulad/eda.py`, `oulad/model_tables.py`); çıktılar birebir aynı.

## 5. Ek analizler: kendi sonucumuzu sınadık

### 5.1 Şüphe
![Araştırma sayfasındaki düşünce haritası](figures/ekran_harita_tr.png)

*Düşünce haritası: H8–H11 durakları, E1–E4 soruları ve şüphe kutusu.*

Hedefimiz "başarısız ya da bırakmış". Bırakan öğrenci sisteme girmeyi ve ödev teslim etmeyi de bırakır; model belki yalnızca bunu görüyor. Bu doğruysa risk sekmesi zorlanan öğrenciyi değil, çoktan gitmiş olanı gösterir. Dört soru sorduk: bilgi hangi sinyalde (E1), kim daha kolay bulunuyor (E2), ne kadar erken (E3), literatür ne diyor (E4).

### 5.2 Ön kayıt
![Koşmadan önce yazılan 10 beklenti](figures/fig07a_beklentiler_once_tr.png)

*B1–B10 beklentileri koşudan önce yazıldı ve md5 ile mühürlendi. Bu grafikte sonuçlar gösterilmez: her kartta "?" ve gri şerit vardır.*

10 beklentiyi sayısal ölçütleriyle yazdık ve dosyaların md5'ini kaydettik: `ek_analizler_on_kayit.md` (eb367fbb…), `_eki.md` (koşudan önce bir kez güncellendi: 20f75feb… → f8cb24be…), `_eki2.md` (5cd0e828…, E3 dışlama kuralı ve sabit kohort). Analiz kodu (`data_science/oulad/ek.py`) son kayıt tutmazsa çalışmıyor. **Karar kuralı:** bir beklenti doğrulama (2014B) ve testte (2014J) ikisinde de sağlanırsa tuttu, ikisinde de sağlanmazsa tutmadı, dönemler ayrışırsa belirsiz.

Sinyal grupları: NOT (`score_mean`, `score_weighted_mean`), TESLİM (`n_expected`, `n_submitted`, `n_unsubmitted`, `delay_mean`, `n_banked`), ETKİNLİK (`vle_*`), KAYIT (`date_registration`).

### 5.3 Şüphe çürüyor (E2)
![Başarısız olacak öğrenciyi bulmak, bırakacak öğrenciyi bulmaktan kolay](figures/fig03_hedef_ayristirma_tr.png)

*Üç pano üç hedefi gösterir: referans (Fail veya Withdrawn), KALDI (Fail; Withdrawn dışarıda) ve BIRAKTI (Withdrawn; Fail dışarıda). Dolu nokta test, içi boş nokta doğrulama ROC AUC değeridir (hgb).*

"Başarısız" ile "bıraktı"yı ayrı ayrı tahmin ettik. GENERAL hgb ROC AUC: KALDI 0,843 (doğrulama) ve 0,815 (test); BIRAKTI 0,805 ve 0,778. Bırakanların daha kolay bulunacağını bekliyorduk (B4): **tutmadı**. BIRAKTI'da en güçlü tek grup etkinlik değil, teslim (test 0,751): B5 de tutmadı.

![Kural, başarısız olacakları bırakacaklardan biraz daha yüksek oranda yakalıyor](figures/fig04_kural_yakalama_tr.png)

*İki sinyalli kuralın sınıf içi ilk %20 bayraklarındaki isabetler final_result'a göre ayrılır; her çubuk, o gruptaki pozitiflerin kuralca yakalanan oranıdır.*

Kural, başarısız olacakların %42,5'ini (671 / 1.578, doğrulama) ve %41,3'ünü (742 / 1.798, test) yakalıyor; bırakacakların %30,2'sini (285 / 945) ve %37,8'ini (503 / 1.329). Testteki isabetlerin 742'si Fail, 503'ü Withdrawn: kuralın isabetlerinin çoğu bırakanlardan gelmiyor (B7 **tutmadı**).

### 5.4 Bilgi nerede? (E1)
![Tek bir sinyal grubu yetmiyor](figures/fig02_sinyal_gruplari_tr.png)

*Her satır bir özellik setidir (hgb, referans hedef). Dolu nokta test ROC AUC değerini ve yüzde doksan beş aralığını, içi boş nokta doğrulama değerini gösterir.*

Test ROC AUC: NOT 0,712, TESLİM 0,735, ETKİNLİK 0,732, NOT + TESLİM 0,780, GENERAL 0,798. Hiçbir tek grup tam modele ulaşmıyor (B1 tuttu). Not ve teslim birlikte tam modelin 0,011 (doğrulama) ve 0,017 (test) gerisinde (B3 tuttu). En güçlü tek grup dönemden döneme değişiyor (B2 belirsiz). **Okul için:** risk işaretinin asıl taşıyıcısı devamsızlık değil, not ve ödev kaydı. Okulda bugün teslim kaydı yok; bu çalışma onun en değerli eksik sinyal olduğunu gösteriyor.

### 5.5 Ne kadar erken? (E3)
![Erken uyarının bedeli](figures/fig05_erkenlik_tr.png)

*Sabit kohortta kesim gününe göre ROC AUC (hgb, referans hedef): düz çizgi test, kesikli çizgi doğrulama. Sabit kohort: 120. günde hâlâ kayıtlı 14.059 öğrenci.*

Aynı hattı 14, 30, 60, 90 ve 120. günler için koştuk. Test GENERAL: 0,675, 0,711, 0,788, 0,821, 0,864. Başarı her adımda arttı (B8), kazancın çoğu erken geldi (B9). 14. günde etkinlik neredeyse tek başına tam model kadar (0,669 ve 0,675; B10). 60. gün seçimi geriye dönük gerekçelendi: kazancın çoğunun alındığı ve hâlâ müdahale için zaman olan nokta.

Koşmadan önce fark ettik: 14. günde test döneminde hiçbir derste notlu ödev yok. "Notlu ödevi olmayan sınıfta bayrak yok" kuralı okul sisteminin kuralıdır, modelin değerlendirme kuralı değil; bu yüzden E3'te uygulanmadı. Karar, sonuçlar görülmeden `_eki2.md` dosyasına yazıldı.

![Geç bırakanları erken görmek daha zor](figures/fig06_erkenlik_hedef_tr.png)

*Sabit kohortta KALDI ve BIRAKTI için GENERAL ROC AUC. BIRAKTI burada 120. günden sonra bırakanlardır; erken bırakanlar bu grafikte yoktur.*

14. günde KALDI 0,692, BIRAKTI 0,628; fark 120. günde daralıyor (0,870 ve 0,849).

### 5.6 Literatürle kıyas (E4)
Yayınlarda OULAD için %90'ın üzerinde değerler görülüyor; bizim 60. gün test değerimiz ROC AUC 0,792. Bu sayılar doğrudan karşılaştırılamaz: tahmin anı, bölme yöntemi, hedef ve demografik özellik kullanımı çalışmadan çalışmaya değişiyor.

| Çalışma | Tahmin anı | Demografik | Bildirilen değer |
|---|---|---|---|
| Bu çalışma | 30. gün, sabit kohort | Yok | ROC AUC 0,711 |
| Wu, Jia ve Pham (2026) | 28. gün, zamansal | Yok | ROC AUC 0,709 |
| Wu vd. (2026) | 28. gün, öğrenciye göre gruplanmış | Var | ROC AUC 0,775 |
| Adnan vd. (2021) | Dersin %20'si | Var | Kesinlik 0,79 |

En yakın tasarım Wu vd. (2026): erken bir sabit gün, kesimden önce bırakanların dışlanması, zamansal doğrulama ve demografik özelliksiz bir model. Sayılar çok yakın, ama kurgular birebir aynı değil; bu bir doğrulama değil, sayılarımızın bu protokol ailesi için makul aralıkta olduğunun işareti. Wu vd.'de de bırakmayı tahmin etmek (0,697) başarısızlığı tahmin etmekten (0,720) daha zor: B4'teki sonucumuz bağımsız olarak tekrarlanıyor (B11, nitel; örnek küçük). Adnan vd. (2021) ve *Scientific Reports* (2025) için bölme türünü doğrulayamadık.

### 5.7 Sonuç
![Önceden yazılan 10 beklenti: 5 tuttu, 3 tutmadı, 2 belirsiz](figures/fig07_beklentiler_tr.png)

*Her kartta sonuç hem renkle hem metinle yazılıdır.*

| Sonuç | Beklentiler |
|---|---|
| Tuttu | B1, B3, B8, B9, B10 |
| Tutmadı | B4, B5, B7 |
| Belirsiz | B2, B6 |
| Destekleniyor (nitel) | B11 |

Tutmayan üç beklenti, "model yalnızca bırakanı buluyor" şüphesinin üç ayağıydı.

### 5.8 Ne değişti, ne değişmedi
- **Değişti:** Şüphe çürüdü; sistemin neyi yakaladığını biliyoruz. 60. gün seçimi gerekçelendi. Okul için en değerli eksik sinyal belirlendi: ödev teslim kaydı.
- **Değişmedi:** Sistemdeki kural. Ek analizler anlamak için yapıldı; bir değişiklik önerisi yeni bir ön kayıtla ayrıca sınanır.
- **Hoca etkisi:** Ölçülemez; iki veri setinde de hoca bilgisi yok. Sistem ona duyarsız kuruldu (sınıf içi göreli sıra). Ölçmek için gereken veri listelendi. Öğretmen sıralama aracı olmamalı.

## 6. Kararlar
| Karar | Gerekçe |
|---|---|
| Mock dondurması kaldırıldı | Takvim uyumu ve tarih sorularının demo değeri |
| `total_absences` kaldırıldı | Yıl sonu sızıntısı ve attendance ile tutarsızlık |
| Asistanda dayanaksız sayı yok | Sayı denetimi, düzeltme turu, geri dönüş |
| Araştırma sayfası girişsiz ve okul verisinden bağımsız | Sentetik okul verisinden bulgu çıkarılmaz |
| Ek analizler kuralı değiştirmez | Değişiklik önerisi yeni ön kayıtla sınanır |
| Hoca etkisi sonuç olarak yazılır | Ölçülemez; sistem ona duyarsız; öğretmen sıralama aracı değil |

## 7. Hata kayıtları
Hafta başındaki kayıtlar (H11-1..7): mock md5, kimlik tahmini, uydurma sayı, ek tur, Streamlit önbellek, örnek soru sözleşmesi, sticky üst çubuk. Ayrıntıları hafta başındaki kayıtlarda. Haftanın geri kalanında eklenenler:

| Hata | Kök neden | Düzeltme |
|---|---|---|
| Notlar okul açılmadan önceydi | Mock takvimden bağımsız üretilmişti | Takvime oturan deterministik yeniden üretim |
| Üretici isme göre düzeltiyordu | Koşullar tek bir öğrenci için özel kodla sağlanıyordu | Profil parametreleri; isimle dallanma yasağı testi |
| `total_absences` sızıntısı | Yıl sonu toplamı her tarihte görünüyordu; attendance ile tutarsızdı | Sütun kaldırıldı; devamsızlık attendance'tan |
| "Kayıtlara ulaşamadım" çıkmazı | Doğrulayıcı AND, CASE, NULLIF'i fonksiyon sanıyordu | Operatör kümesi ayrıldı; NULLIF eklendi |
| CTE içinde DELETE (denetim 6.2) | Denetim CTE içini kapsamıyordu | Her yerde DML, DDL, INTO, kilit reddi |
| Asistan sayıları | `distinct_counts` izinli kümeye girmiyordu; önceki tur sayıları HTTP üzerinden izinli değildi; ay adı + sayı yanlış maskeleniyordu | Düzeltildi |
| Kırılgan arayüz testleri | Kartlar kenar çizgisiyle, sekmeler kısa etiketlerle bulunuyordu | Testler kendi işaretleriyle buluyor |
| Notebook'ta hücre içi hesap | 01, 02, 03'teki hesaplar defterde yapılıyordu | Pakete taşındı; çıktılar birebir aynı |
| `.venv` kopyası ve yanlış Jupyter çekirdeği | Kopyalanan ortam week08'in Python'unu gösteriyordu | `staj-week11` çekirdeği; `explain.json`'un TreeExplainer ile üretildiği doğrulandı |
| feature_list "okul karşılığı" | Hafta 9 sınıflandırması hatalıydı (at_risk ve teslim sayaçları "not") | Düzeltildi |
| feature_group `vle_click_*` | Dinamik sütunlar grup dışında kalıyordu; mevcut kesim testi yakaladı | Önek kuralı ve yeni test |
| Ön kayıt kontrolü | İlk md5 kaydına bakıyordu | Son kayda bakıyor |
| Yapı testi kırıldı | Metin yamasından sonra yer tutucular çözülmeden aranıyordu | Test, sayfanın çözücüsüne (`coz`) bağlandı |
| UCI TR görselleri İngilizce | TR notebook'ta grafik etiketleri İngilizce kalmıştı; test görselin içeriğine bakmıyordu | Bilinen sınır; çizim kodu Hafta 12'de pakete taşınacak |

**Açık:** `explain.py` `_attribute` içinde `except Exception` ile sessiz yöntem değişimi (bugünkü çıktıyı etkilemedi); düzeltilecek.

## 8. Bilinen sınırlar
- UCI ve OULAD keşif grafiklerinin TR sürümleri İngilizce ya da noktalı ondalık; Modelleme ve Karar kuralı grafiklerinde de TR biçimleyici uygulanmıyor.
- Grup ataması iki kaynakta (`dataset.py` önek kuralı, `ek.py` sabit `GROUP_OF`); ileride tek `group_of()`. `ek.py` şimdi değiştirilmiyor; değişirse ek analizler yeniden koşulur.
- Grafik çıktıları `data_science/oulad/reports/` altında; proje kökündeki `reports/` ile tutarsız.
- Ek analizler keşifseldir; tek doğrulama dönemi var.

## 9. Çıktılar ve doğrulama
- **Kod:** `data_science/oulad/ek.py`, `figures.py` (`--rule2 --ek`), `scripts/arastirma_paketi.py`, `scripts/mock_uret.py`, `backend/app/services/takvim.py`, `backend/app/core/bugun.py`; raporlar `data_science/oulad/reports/ek_metrics.json` ve `figures/week11/` (8 grafik, TR/EN).
- **Belgeler:** `docs/ek_analizler_on_kayit*.md`, `docs/on_kayit_md5.txt`, `docs/ek_analizler_sonuc.md`, `docs/metin_yamasi.json`.
- **Testler:** Tam paket 7 Kasım'da 1.210 passed, 3 skipped. 8 Kasım'daki metin ve arayüz düzeltmelerinden sonra frontend testleri geçti.
- **Paket farkı:** Eski anahtarların değeri değişmedi; tek yeni anahtar `rule.flag_rate`, kuralın kendi sabitinden (`rule.py` `FLAG_RATE`) geliyor.
- **Parquet:** 7 Kasım'da yanlışlıkla bir kez yeniden yazıldı; 26.403 satır, bölme sayıları ve oranları aynı; ek analizler yeniden koşuldu, e1, e2, e3 ve beklentiler birebir aynı.

```
python -m data_science.oulad.ek
python -m data_science.oulad.ek --e3
python -m data_science.oulad.figures --rule2 --ek
python scripts/arastirma_paketi.py
python -m pytest -q
```

## 10. Açık konular
- `get_risk` aracı; "sorulan ayda veri yoksa baştan söyle" cilası; Türkçe ondalık virgül tutarlılığı.
- Denetim temizliği (düşük riskli bulgular, `notebooks/_figtmp_*`, `explain.py`).
- Araştırma sayfası: etkileşimli grafikler (S2–S5), mobil ve erişilebilirlik (S6).
- Hafta 6 hata 4; Hafta 7 m5 ve c4; pytest Starlette uyarısı.

## 11. Hafta 12
- Deploy öncesi güvenlik: SECRET_KEY, giriş sayacı, soru uzunluğu sınırı, log maskeleme, `.env.example`, `.gitignore`; eval'in yeni veriyle ve DEMO_TODAY ile yeniden koşulması.
- Contabo VPS'te Docker deploy: temiz ortamda bütün notebook'lar yeniden koşulup çıktıları karşılaştırılacak; çizim kodu pakete taşınacak.
- README, KVKK kapsamı, demo; gelecek çalışmalar: ödev teslim kaydı, veli için kıyassız bayrak, alt grup denetimi, hoca etkisi için gereken veri.
