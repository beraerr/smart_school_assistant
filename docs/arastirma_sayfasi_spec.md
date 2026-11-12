# Araştırma sayfası: belirtim (TR/EN)

Bu belge, giriş ekranından açılan herkese açık "Araştırma" sayfasının içeriğini, grafiklerini ve veri kaynağını tanımlar. Uygulama üç görevde yapılır (bölüm 7). Metinlerdeki `{...}` alanları paketlenmiş JSON'dan doldurulur; sayfada elle yazılmış rakam yoktur.

## 1. İlkeler

1. **Tek kaynak.** Her sayı `data_science` raporlarından gelir. Sayfa, bunlardan üretilen tek bir paket dosyasını okur (`frontend/assets/arastirma/arastirma.json`). Paket, bir betikle yeniden üretilir ve bir test, paketin kaynaklarla aynı olduğunu doğrular.
2. **Dürüstlük.** Okul demosunun verisi sentetiktir; sayfada ondan bulgu çıkarılmaz ve bu açıkça yazılır. Test edilemeyen (hoca) "bilmiyoruz" diye yazılır. SHAP nedensellik değildir.
3. **Erişim.** Sayfa giriş gerektirmez, okul verisine veya backend'e erişmez, model API'sini çağırmaz. Adres: `?sayfa=arastirma`.
4. **Dil.** TR ve EN; giriş ekranındaki dil seçimi geçerli. Sayı biçimi: TR `0,792` ve `%82,0`; EN `0.792` ve `82.0%`. Korelasyonlar (`kor`): iki ondalık, eksi işareti "−"; TR `0,81` / `−0,38`, EN `0.81` / `−0.38`.
5. **Grafikler.** Altair (Streamlit ile gelir; yeni bağımlılık yok). Etkileşim yalnızca veri gerçekten varsa. Statik PNG yalnızca etkileşimli karşılığı olmayan yerde.

## 2. Paket dosyası: `arastirma.json`

Üretici: `scripts/arastirma_paketi.py`. Girdiler: `data_science/reports/eda_summary.json`, `data_science/oulad/reports/{model_metrics,explain,rule_metrics,rule2_metrics}.json`, `figures/week10/figures.json`, `figures/week11/figures.json`. Türetilmiş alanlar üreticide hesaplanır (aşağıda formülü verilenler); sayfada aritmetik yapılmaz.

| Anahtar | Kaynak / formül |
|---|---|
| `uci.total`, `uci.mat`, `uci.por` | eda_summary.row_counts |
| `uci.pass_mat`, `uci.pass_por` | eda_summary.pass_rate_by_subject |
| `uci.g3_zero` | eda_summary.g3_zero_count |
| `uci.corr_g1`, `uci.corr_g2`, `uci.corr_failures` | eda_summary (top_abs_correlation_with_g3) |
| `uci.absence.*` | **Görev 0** ile eda_summary'e eklenecek: pearson/spearman (G3=0 dahil, hariç) ve dilimler `[{bucket, n_excl, pass_all, pass_excl}]` |
| `oulad.n_rows_raw`, `oulad.n_rows_sample`, `oulad.n_vle_rows`, `oulad.n_courses` | Mevcut `data_science.oulad` fonksiyonlarıyla (load/dataset/validate) hesaplanır. Hesaplanamıyorsa DUR. |
| `oulad.split` | `[{part, presentations, rows, risk_rate, has_history}]`, aynı yolla |
| `test.n`, `test.n_positive` | explain.capacity.rows[flag_rate=0.2].global |
| `test.module_rates` | model_metrics.calibration.rows (set=GENERAL): `{module: positive_rate}` |
| `test.module_rate_min/max` (+ modül adı) | yukarıdakinin en küçüğü/büyüğü |
| `sets.roc_val[set][model]`, `sets.roc_test[set][model]` (+ low/high) | model_metrics.validation.rows, test_metrics |
| `sets.paired.HISTORY_GENERAL[model]` | model_metrics.paired_differences.*.HISTORY-GENERAL.roc_auc |
| `sets.within_module_mean[set]` | model_metrics.modules.mean (test) ve validation.modules (doğrulama, modül ağırlıksız ortalama) |
| `calibration` | model_metrics.calibration.rows (tamamı) |
| `lomo.rows`, `lomo.mean` | model_metrics.lomo |
| `capacity` | explain.capacity.rows (tamamı, modül satırları dahil) |
| `shap.features` | explain.shap.features |
| `shap.dependence` | explain.shap.dependence; her özellik için sabit tohumla (42) 3.000 noktalık örnek; örnek boyutu pakete yazılır |
| `rule.periods` | rule2_metrics.periods |
| `rule.capture_rule2[period]` | rule2 n_hit ÷ model n_hit |
| `rule.gap_rule2[period]` | (model precision − rule2 precision) × 100, puan |
| `rule.excluded` | rule_metrics.excluded |
| `figures.captions` | figures_week10/11.json (başlık ve alt metinler TR/EN) |

## 3. Giriş ekranındaki bağlantı

Kırmızı paneldeki üçüncü özellik (denetim 5.9 düzeltmesiyle):

- TR başlık: **Açık veriyle sınanmış kural**
  TR gövde: OULAD'da modellerle karşılaştırılan iki sinyalli kuralın okul verisindeki karşılığı.
- EN title: **A rule tested on open data**
  EN body: The school-data counterpart of a two-signal rule compared against models on OULAD.

Özelliklerin altında, panel stiline uygun bağlantı: **Araştırmayı incele →** / **Explore the research →** (`?sayfa=arastirma`). Bağlantı sayfayı yeniden yüklemez: bağlantı gibi görünen bir düğmedir; tıklanınca `sayfa=arastirma` sorgu parametresi eklenir ve sayfa yeniden çizilir, oturum ve dil korunur. Araştırma sayfasındaki "Girişe dön" ve marka da aynı biçimde düğmedir ve parametreyi kaldırır.

## 4. Sayfa düzeni

Üst şerit: logo + "Akıllı Okul" (tıklanınca girişe döner), sağda dil seçici ve **Girişe dön** / **Back to sign in**. Sayfa genişliği en fazla 960 px, ortalı. Bölümler arasında ince ayraç. Her grafiğin altında `figures.json` alt metni (varsa) ya da bu belgedeki açıklama.

Renkler (uygulama paleti): kural (2 sinyal) `#C8102E`, kural (3 sinyal) `#A50E24`, model `#1F2328`, gerçek oran siyah nokta, ikincil `#5B6370`, kılavuz çizgileri `#E1E4EA`, vurgu `#E8A33D`. Setler: GENERAL `#1F2328`, GENERAL_MODULE `#5B6370`, HISTORY `#E8A33D`, HISTORY_SLOT `#F2C98A`, GENERAL_REL `#C8102E`.

### 4.0 Giriş (hero)

TR başlık: **Dikkat bayrağının arkasındaki araştırma**
TR alt başlık: Okul sistemindeki risk sekmesi bir tahmin modelinden değil, açık veriyle sınanmış şeffaf bir kuraldan gelir. Bu sayfa o kurala nasıl varıldığını, neyin işe yaradığını, neyin yaramadığını ve neyi hâlâ bilmediğimizi gösterir.

EN title: **The research behind the attention flag**
EN subtitle: The school system's risk tab does not come from a prediction model but from a transparent rule tested on open data. This page shows how we arrived at that rule, what worked, what did not, and what we still do not know.

Üç özet kartı:
1. TR: **%{rule.capture_rule2.2014J}** · Şeffaf kural, test döneminde modelin isabetlerinin bu kadarını yakalıyor. EN: **{…}%** · On the test term, the transparent rule catches this share of the model's hits.
2. TR: **{rule.gap_rule2.2014J} puan** · Şeffaflığın bedeli: kesinlikte modelin gerisinde kalınan fark (sınıf içi %20). EN: **{…} points** · The price of transparency: the precision gap to the model (top 20% within class).
3. TR: **Bilmiyoruz** · Hocanın etkisi: iki veri setinde de hoca bilgisi yok, test edilemedi. EN: **Unknown** · Teacher effect: neither dataset records the teacher, so it could not be tested.

Uyarı kutusu (amber, ikon yok):
TR: Okul demosundaki öğrenciler ve notlar sentetiktir. Bu sayfadaki bütün bulgular yalnızca iki açık veri setinden gelir; okul verisinden bulgu çıkarılmamıştır.
EN: The students and grades in the school demo are synthetic. Every finding on this page comes from two open datasets; no findings are drawn from the school data.

### 4.1 Soru

TR: Bir öğrencinin zorlandığını, iş işten geçmeden ve gerekçesiyle söyleyebilir miyiz? Ve risk yalnızca öğrenciye mi bağlı, yoksa derse, hocaya, o yılın koşullarına göre de değişir mi? Gerçek hayatta aynı notlarla bir derste güvende olan öğrenci, finali zor geçen başka bir derste risk altında olabilir. Bu doğruysa, yalnızca öğrenciye bakan bir yaklaşım yanılır.

EN: Can we tell that a student is struggling early enough, and with a reason? And does risk depend only on the student, or also on the course, the teacher, and that year's conditions? In real life, a student who is safe in one course with certain grades may be at risk with the same grades in another course whose final was harder. If so, an approach that looks only at the student will be wrong.

### 4.2 İki veri seti

İki kart yan yana (dar ekranda alt alta).

Kart 1, TR: **UCI Student Performance** · Portekiz'de iki lise, iki ders (Matematik, Portekizce), tek öğretim yılı. {uci.total} kayıt; notlar 0–20 (G1, G2 dönem içi, G3 final). Kaynak: Cortez ve Silva (2008), CC BY 4.0.
EN: Two Portuguese high schools, two subjects (Mathematics, Portuguese), one school year. {uci.total} records; grades 0–20 (G1, G2 in term, G3 final). Source: Cortez & Silva (2008), CC BY 4.0.

Kart 2, TR: **OULAD** · Open University (Birleşik Krallık), uzaktan eğitim. {oulad.n_courses} ders-dönem, {oulad.n_rows_raw} öğrenci-ders kaydı, {oulad.n_vle_rows} çevrim içi etkinlik satırı; 2013–2014. Kaynak: Kuzilek, Hlosta ve Zdrahal (2017), CC BY 4.0.
EN: Open University (UK), distance learning. {oulad.n_courses} course-presentations, {oulad.n_rows_raw} student-course records, {oulad.n_vle_rows} online activity rows; 2013–2014. Source: Kuzilek, Hlosta & Zdrahal (2017), CC BY 4.0.

Altında tek cümle, TR: İkisi de bir Türk lisesi değil. Bu yüzden sisteme veri ya da model taşınmadı; yalnızca sınanmış bir kuralın tarifi taşındı.
EN: Neither is a Turkish high school. So no data or model was carried into the system; only the recipe of a tested rule was.

### 4.3 UCI: ilk bulgular ve ilk hata

TR: Erken notlar finali güçlü biçimde yansıtıyor (G1 ile G3 arasında r = {uci.corr_g1}). Not dışındaki en güçlü işaret geçmiş başarısızlık (r = {uci.corr_failures}). Devamsızlık ise ilk analizde zayıf görünüyordu; bu bir hataydı.
EN: Early grades strongly reflect the final (r = {uci.corr_g1} between G1 and G3). The strongest non-grade signal is past failure (r = {uci.corr_failures}). Absence looked weak in the first analysis; that was a mistake.

**Grafik U1 (etkileşimli): devamsızlık dilimine göre geçme oranı.** Çubuk grafik, x: dilim (0, 1–5, 6–10, 11–20, 21+), y: geçme oranı. Üstte iki seçenekli düğme: "G3=0 dahil" / "G3=0 hariç" (EN: "Including G3=0" / "Excluding G3=0"). Çubukların üstünde öğrenci sayısı. Altında korelasyon satırı seçime göre değişir: Pearson {uci.absence.pearson_*}, Spearman {uci.absence.spearman_*} (`kor` biçimi).

Grafik altı kutu, TR: **Hata kaydı.** {uci.g3_zero} öğrencinin final notu 0 ve hepsinin devamsızlığı 0 görünüyordu: büyük olasılıkla sınava girmeyen ya da ayrılan öğrenciler. Bu kayıtlar ilişkiyi bastırıyordu. Hariç tutulunca devamsızlık arttıkça geçme oranının düzenli düştüğü görüldü. Yine de en yüksek dilimdekilerin yarısı geçiyor: devamsızlık tek başına karar verdirmez.
EN: **Error record.** {uci.g3_zero} students had a final grade of 0 and all showed zero absences: most likely students who did not sit the exam or left. These records suppressed the relationship. Once excluded, the pass rate falls steadily as absences rise. Still, half of those in the highest band pass: absence alone does not decide.

Kapanış, TR: UCI'da ders, hoca ya da sınav tarihi yok; gerçek bir erken uyarı kurulamıyor. Bağlam sorusu için daha büyük ve zamansal bir veriye geçtik.
EN: UCI has no course context, teacher, or exam dates, so a real early warning cannot be built. For the context question we moved to a larger, time-ordered dataset.

### 4.4 OULAD: erken uyarı düzeni

TR: Her öğrenci-ders için yalnızca dersin **60. gününe kadar** olan bilgiyi kullandık: o güne kadar teslim edilen ödevler ve çevrim içi etkinlik. Hedef, dersi başarısız bitirmek ya da bırakmak. Modeller geçmiş dönemlerle eğitildi, gelecek bir dönemde bir kez sınandı; gelecekten bilgi sızmasın diye her sınır testlerle korundu.
EN: For each student-course we used only information up to **day 60** of the course: assignments submitted by then and online activity. The target is failing or withdrawing. Models were trained on past terms and tested once on a future term; every boundary was guarded by tests so that no future information leaked.

**Grafik O1 (statik, Altair): zaman çizelgesi.** Yatay şerit, `oulad.split` satırlarından: geçmiş (2013B) → eğitim (2013J + 2014B) → test (2014J); her parçada satır sayısı ve risk oranı. 2014B üzerinde ayrıca "doğrulama" etiketi.

### 4.5 Risk derse, zamana ve hocaya göre değişir mi?

Bölüm girişi, TR: Deneyde beş özellik seti, iki model türüyle karşılaştırıldı: yalnızca öğrencinin izi (GENERAL), buna dersin kimliği (GENERAL_MODULE), dersin geçmiş dönemleri (HISTORY) ve iki kontrol seti. Cevap dört parçalı.
EN: The experiment compared five feature sets with two model types: the student's own trace only (GENERAL), plus the course identity (GENERAL_MODULE), plus the course's past terms (HISTORY), and two control sets. The answer has four parts.

Dört kısa kart (ikon yok, başlık + 2 cümle):

1. TR **Ders: evet.** Test döneminde dersin risk oranı %{test.module_rate_min} ({min modül}) ile %{test.module_rate_max} ({max modül}) arasında değişiyor. Dersin kimliğini bilmek tahminin seviyesini düzeltiyor.
   EN **Course: yes.** On the test term, a course's risk rate ranges from {min}% ({module}) to {max}% ({module}). Knowing the course identity corrects the level of the prediction.
2. TR **Zaman: kayıyor.** Dersin geçmiş risk oranı, yeni dönemde tahmini yanlış yöne çekti; dersin geçmişini eklemek sonucu kötüleştirdi (ROC AUC farkı {sets.paired.HISTORY_GENERAL.hgb} [{low}; {high}]). Bu yüzden sistem mutlak olasılık göstermez.
   EN **Time: it drifts.** A course's past risk rate pulled predictions the wrong way in the new term; adding the course history made results worse (ROC AUC difference {…} [{low}; {high}]). That is why the system shows no absolute probability.
3. TR **Sınıf içi sıra: bağlam katkı vermedi.** "Bu sınıfta kim daha riskli?" sorusunda hiçbir bağlam tarifi iki dönemde tutarlı bir katkı yapmadı. İşe yarayan, öğrenciyi kendi sınıfı içinde değerlendirmek.
   EN **Ranking within a class: context did not help.** For "who is more at risk in this class?", no context recipe helped consistently across two terms. What works is judging each student within their own class.
4. TR **Hoca: bilmiyoruz.** İki veri setinde de hoca bilgisi yok; bu boyut test edilemedi. Okul sisteminde sonuç bilgisi biriktikçe sınanabilir.
   EN **Teacher: unknown.** Neither dataset records the teacher, so this could not be tested. It can be tested as outcome data accumulates in the school system.

**Grafik C1 (etkileşimli): dersler arası seviye.** Her satır bir modül (test 2014J). Siyah nokta gerçek oran; renkli noktalar seçilen setlerin ortalama tahmini (`calibration`). Üstte çoklu seçim: GENERAL, GENERAL_MODULE, HISTORY (varsayılan üçü açık). Aynı modüldeki noktalar ince çizgiyle birleşir. Fareyle üzerine gelince: modül, set, gerçek oran, ortalama tahmin, n.
Alt metin: figures.json → fig02_oran_kaymasi.

**Grafik C2 (etkileşimli): doğrulamada ve testte sıralama.** Eğim grafiği, x: Doğrulama 2014B / Test 2014J, y: ROC AUC; her çizgi bir set (`sets.roc_val`, `sets.roc_test`). Üstte model seçimi: HistGradientBoosting / Lojistik regresyon. Test noktasında %95 aralık (yalnızca hgb için veri varsa). GENERAL ve GENERAL_REL kalın.
Alt metin: figures.json → fig01_roc_egim.

### 4.6 Bilimsel dürüstlük: testte birinci, doğrulamada sonuncu

TR: Testte en iyi görünen set (GENERAL_REL, test ROC AUC {sets.roc_test.GENERAL_REL.hgb}) test sonuçlarına bakılarak tasarlanmıştı. Bağımsız doğrulama döneminde en düşük sonucu verdi ({sets.roc_val.GENERAL_REL.hgb}). Benimsemedik. Test sonucuna bakarak yapılan tasarım şans eseri kazananı seçebilir; bu noktadan sonra test dönemini dondurduk ve sonradan eklenen setleri "keşifsel" diye işaretledik.
EN: The set that looked best on test (GENERAL_REL, test ROC AUC {…}) had been designed after looking at test results. It scored lowest on the independent validation term ({…}). We did not adopt it. Design guided by test results can pick a lucky winner; from then on we froze the test term and marked later sets as "exploratory".

Tablo (statik metin, sayı yok), TR başlık: **Doğrulanmayan açıklamalar**
| Tahmin | Kontrol | Sonuç |
|---|---|---|
| Kötüleşmenin kaynağı yalnızca geçmiş risk oranı | O sütun çıkarıldı: sonuç aynı kaldı | Yanlış: geçmiş ödev özellikleri de genelleşmiyor |
| GENERAL_REL yalnızca seviyeyi kaçırıyor, sıralaması sağlam | Doğrulamada sıralama ölçüldü: en düşük | Yanlış: set benimsenmedi |

EN başlık: **Explanations that did not hold**
| Guess | Check | Result |
|---|---|---|
| The drop came only from the past risk-rate column | That column was removed: the result stayed the same | Wrong: past assignment features do not generalize either |
| GENERAL_REL only misses the level; its ranking is sound | Ranking was measured on the validation term: lowest | Wrong: the set was not adopted |

Kapanış cümlesi, TR: Doğrulanmayan hiçbir açıklama sonuç olarak yazılmadı. EN: No explanation that failed its check was reported as a finding.

### 4.7 Hiç görülmemiş bir ders

TR: Her ders sırayla eğitimden çıkarılıp yalnızca onda sınandı. Dersin kimliği yeni bir derse taşınamıyor; sıralama başarısı setler arasında neredeyse aynı (ortalama ROC AUC {lomo.mean.GENERAL} – {lomo.mean.GENERAL_REL}). Asıl uyarı GGG'de: o derste 60. güne kadar notlu ödev yok, model "henüz ödev yok" durumunu "ödev teslim etmedi" gibi okuyup riski çok yüksek tahmin ediyor. Sistemdeki karşılığı: notu olmayan sınıfta bayrak gösterilmez.
EN: Each course was held out of training in turn and tested on its own. The course identity does not transfer to a new course; ranking performance is almost the same across sets (mean ROC AUC {…} – {…}). The real warning is GGG: it has no graded assignment before day 60, so the model reads "no assignment yet" as "did not submit" and predicts very high risk. In the system: no flag is shown in a class with no grades.

**Grafik L1 (etkileşimli):** her satır bir modül; siyah nokta gerçek oran, renkli noktalar GENERAL ve GENERAL_REL ortalama tahmini (`lomo.rows`). GGG satırı `#E8A33D` zeminle vurgulu. Alt metin: fig03_gorulmemis_ders.

### 4.8 Model neye dayanıyor?

TR: Modelin en çok dayandığı üç işaret: teslim edilmeyen ödev sayısı, not ortalaması ve son etkinlikten bu yana geçen süre. Bu, modelin davranışını anlatır; "ödev teslim etmemek başarısızlığa yol açar" anlamına gelmez.
EN: The three signals the model relies on most: number of unsubmitted assignments, grade average, and time since last activity. This describes the model's behaviour; it does not mean that not submitting causes failure.

**Grafik S1 (statik Altair):** yatay çubuk, ortalama |SHAP| (`shap.features`, ilk 8).
**Grafik S2 (etkileşimli):** seçilen özellik için gözlenen değer – SHAP saçılımı (`shap.dependence`); özellik seçici ilk üç özellik. Altında bilgi satırı, TR: "{n_sample} noktalık sabit örnek (toplam {n_total})", EN: "Fixed sample of {n_sample} points (out of {n_total})"; ikisi de `tam` biçimi, değerler `shap.dependence`'tan. Alt metin: fig05_shap.

### 4.9 Kaç öğrenciye bayrak? (en güçlü etkileşimli bölüm)

TR: Bir öğretmenin izleyebileceği öğrenci sayısı sınırlı. Bayrak oranını değiştirerek kesinlik (bayraklananların ne kadarı gerçekten zorlandı) ile yakalama (zorlananların ne kadarı bayraklandı) arasındaki dengeyi görebilirsin. Öğrencileri tüm okulda birlikte sıralamak ile her sınıfın içinde sıralamak karşılaştırılıyor.
EN: A teacher can only follow so many students. Move the flag rate to see the trade-off between precision (how many flagged students really struggled) and recall (how many struggling students were flagged). Ranking everyone together is compared with ranking inside each class.

**Grafik K1 (etkileşimli):** kaydırıcı: bayrak oranı %5–%50, adım %5, varsayılan %20 (`capacity`). Sol: iki çizgi (genel / sınıf içi) kesinlik; ikinci sekme ya da seçenek: yakalama. Seçili orana dikey kesikli çizgi. Sağ: seçili oranda modül bazında kesinlik çubukları (sınıf içi). Kaydırıcının altında canlı cümle, TR: "%{oran} bayrakta sınıf içi sıralama {n_flagged} öğrenciyi işaretliyor; bunların %{precision}'i gerçekten zorlandı ve zorlananların %{recall}'i yakalandı." EN eşdeğeri. Model: GENERAL hgb, test 2014J (grafik başlığında yazılı).

Altında TR: %20'yi seçtik: sınıf içi sıralama %10–35 aralığında önde, her öğretmene eşit izleme kapasitesi veriyor ve dersin taban oranındaki kaymadan etkilenmiyor. Bedeli: riskin düşük olduğu sınıflarda isabet de düşüyor.
EN: We chose 20%: within-class ranking leads between 10% and 35%, gives every teacher equal follow-up capacity, and is unaffected by drift in a course's base rate. The cost: in low-risk classes, precision drops too.

### 4.10 Modelden kurala

TR: Okulda "bu öğrenci sonunda başarısız oldu mu" bilgisini tutan bir geçmiş yok; bu yüzden sistemde model eğitmek zaten mümkün değildi. Biz de soruyu tersinden sorduk: eğitilmeyen, sonuca bakmayan, sonucu görmeden önce sabitlenmiş şeffaf bir kural modelin ne kadar gerisinde kalır? Önce üç sinyalli bir kural sınandı; okul verisinde "girilmeyen sınav" karşılığı olmadığı için iki sinyalli sürüme (not ortalaması ve aktif gün) geçildi ve o da aynı ölçütle önceden yazılmış kurallarla sınandı.
EN: The school keeps no history of "did this student eventually fail", so training a model in the system was never an option. So we asked the reverse: how far behind the model does a transparent rule fall, one that is not trained, never looks at outcomes, and was fixed before seeing results? A three-signal rule was tested first; since the school data has no equivalent of "missed assignment", we moved to a two-signal version (grade average and active days), tested against criteria written in advance.

**Grafik R1 (etkileşimli):** gruplu çubuk, x: modül, y: kesinlik (sınıf içi %20); üç seri: 3 sinyal, 2 sinyal, model (`rule.periods`). Üstte dönem seçimi: Doğrulama 2014B / Test 2014J. Toplam satırı ayrı bir "Tümü" çubuğu olarak. Fareyle: n, bayrak, isabet, kesinlik. Altında `rule.excluded` notu, TR: "GGG iki dönemde de hariç: 60. güne kadar notlu ödev yok." EN not: "GGG is excluded in both terms: it has no graded assignment before day 60." Alt metin: fig01_sinyal_kesinlik.

### 4.11 Sistemdeki karşılığı

Tablo, TR:
| OULAD sinyali | Okuldaki karşılığı | Yön |
|---|---|---|
| Not ortalaması (60. güne kadar) | Dönem içi not ortalaması | Düşük olan riskli |
| Aktif gün sayısı | Mazeretsiz devamsızlık | Az aktif gün / çok devamsızlık riskli |
| Teslim edilmeyen ödev | Okulda karşılığı yok | Kullanılmıyor |

Tablo, EN:
| OULAD signal | School counterpart | Direction |
|---|---|---|
| Grade average (up to day 60) | In-term grade average | Lower is riskier |
| Active days | Unexcused absences | Fewer active days or more absences is riskier |
| Unsubmitted assignments | No counterpart in the school data | Not used |

Altında TR: Her sınıfta iki sinyalin sınıf içi sırası alınır, ortalamaya göre sınıfın yaklaşık beşte biri işaretlenir. Olasılık ya da puan gösterilmez; her bayrağın gerekçesi yazılır. Risk yalnızca öğretmen ve müdüre açıktır.
EN: In each class, the two signals are ranked within the class and about one fifth of the class is flagged by their average. No probability or score is shown; every flag comes with its reason. Risk is visible only to teachers and the principal.

### 4.12 Sınırlar ve bilmediklerimiz

Madde listesi yerine kısa paragraflar (iki sütun, dar ekranda tek):
TR: Tek kurum, tek ülke ve uzaktan eğitim; bir Türk lisesine doğrudan genellenemez. Başarısız olmak ve dersi bırakmak aynı sınıfta toplandı; farklı süreçler olabilir. Yalnızca bir doğrulama dönemi var. Görülmemiş ders analizinde belirsizlik aralığı hesaplanmadı. SHAP nedensellik değildir. Okuldaki iki sinyal OULAD sinyallerinin birebir aynısı değil, en yakın karşılığıdır. Hocanın etkisi test edilemedi.
EN: Single institution, single country, and distance learning; the findings cannot be generalized directly to a Turkish high school. Failing and withdrawing were grouped into one class; they may be different processes. There is only one validation term. No uncertainty intervals were computed for the unseen-course analysis. SHAP is not causation. The school's two signals are not identical to the OULAD signals, only their closest counterparts. The teacher effect could not be tested.

### 4.13 Yeniden üretim

TR: Bütün sayılar ve grafikler aynı kod paketinden üretilir; notebook'lar bu paketi çağırır, kod kopyalamaz. Çalıştırma komutları ve notebook adları: `01_uci_eda`, `02_oulad_eda`, `03_oulad_model` (TR/EN). Kaynakça: Cortez & Silva (2008); Kuzilek, Hlosta & Zdrahal (2017).
EN: All numbers and charts are produced from the same code package; the notebooks call this package instead of copying code. Commands and notebook names: 01_uci_eda, 02_oulad_eda, 03_oulad_model (TR/EN). References: Cortez & Silva (2008); Kuzilek, Hlosta & Zdrahal (2017).
Kod bloğu: `python -m data_science.oulad.model`, `…explain`, `…figures`, `…rule`, `python scripts/arastirma_paketi.py`.

## 5. Erişilebilirlik ve görünüm

- Her grafiğin metin karşılığı: Altair `description` ve altında görünür alt metin.
- Renk tek başına anlam taşımaz: seriler etiket ya da gösterge ile ayrılır.
- Mobilde grafikler tam genişlik, iki sütunlu bölümler tek sütun.
- Açık/koyu tema: uygulamanın mevcut tema değişkenleri; grafik arka planı şeffaf.

## 6. Kapsam dışı

Okul verisiyle analiz, model çalıştırma, backend uç noktası, yeni bağımlılık, giriş gerektiren içerik, sayfada aritmetik.

## 7. Görevler

- **Görev 0 (data_science):** `data_science.eda` devamsızlık analizini (dahil/hariç korelasyonlar ve dilim tablosu) `eda_summary.json`'a yazsın; değerler WEEK_08'deki tablo ile aynı olmalı (test). Mevcut alanlar değişmez.
- **Görev 1 (paket):** `scripts/arastirma_paketi.py` + `frontend/assets/arastirma/arastirma.json`. Testler: deterministik (iki çalıştırma aynı bayt); paket, kaynaklardan yeniden üretilen pakete eşit (senkron testi); bölüm 2'deki her anahtar var; türetilmiş alanlar formülle doğrulanır.
- **Görev 2 (sayfa):** `frontend/arastirma.py` (sayfa), `frontend/arastirma_metin.py` (TR/EN metinler, `{...}` alanlarıyla), giriş ekranı bağlantısı ve 3. özellik metni, `?sayfa=arastirma` yönlendirmesi (girişsiz). Testler: TR ve EN sayfa istisnasız çizilir; metinlerdeki her `{...}` paketten çözülür, çözülmeyen alan yok; sayfa api_client'ı hiç çağırmaz; giriş ekranında bağlantı var; giriş yapmış kullanıcı da sayfaya erişebilir; sayı biçimi TR virgül / EN nokta.
