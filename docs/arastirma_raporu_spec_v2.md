# Araştırma raporu: belirtim v2 (TR/EN)

Bu belge `docs/arastirma_sayfasi_spec.md` (v1) dosyasının yerine geçer. v1 tek sayfalık bir özetti; v2, üç notebook'u (01 UCI keşif, 02 OULAD keşif, 03 OULAD model) eksiksiz kapsayan, bölümlere ayrılmış, etkileşimli bir veri bilimi raporudur. v1'de yazılan metinler ve kartlar **1. Özet** bölümüne taşınır; silinmez.

Rapor tek başına bir portfolyo parçası olarak da okunabilmelidir: okul uygulamasını hiç görmemiş biri, yalnızca bu sayfadan çalışmanın sorusunu, yöntemini, hatalarını, sonucunu ve sınırını anlayabilmelidir.

---

## 0. İlkeler

1. **Dürüstlük önce gelir.** Sonuçlar mütevazıdır (test ROC AUC ≈ 0,79) ve öyle sunulur. Hatalar ve çürüyen hipotezler gizlenmez; ayrı bir bölümde, düzeltmeden önce ve sonra hâliyle gösterilir. Doğrulanmayan hiçbir açıklama bulgu olarak yazılmaz.
2. **Tek kaynak.** Her sayı ve her grafik verisi, notebook'ların çağırdığı `data_science` fonksiyonlarından gelir. Sayfa yalnızca paketi (`frontend/assets/arastirma/arastirma.json`) okur. Metinde elle yazılmış rakam yoktur; `{yol:biçim}` yer tutucuları kullanılır.
3. **Notebook'ta mantık kalmaz.** Paketleyici bir notebook hücresinde tanımlanmış bir hesaba ihtiyaç duyarsa, o hesap önce `data_science` altına taşınır ve notebook oradan çağırır (Hafta 8 devamsızlık analizinde yapılan gibi). Kopya yazılmaz.
4. **Nedensellik yok.** Birlikte görülen örüntü neden değildir; SHAP neden değildir. Bu, ilgili her grafiğin altında tek cümleyle hatırlatılır.
5. **Hoca bir neden değil, bir sonuçtur.** Rapor "hocanın etkisi yoktur" demez. "Bu verilerle hoca etkisi ölçülemez; ölçmek için şu veri gerekir; elimizdeki verilerle söyleyebileceğimiz şudur" der (bölüm 8).
6. **Erişim.** Girişsiz, okul verisine ve backend'e dokunmaz, model API'si yok. Adres `?sayfa=arastirma`; isteğe bağlı `&bolum=<kimlik>` doğrudan bölüm açar.
7. **Dil ve biçim.** TR/EN. Biçimler: `tam`, `yuzde`, `roc` (3 ondalık), `kor` (2 ondalık), `puan` (1 ondalık), `metin`.
8. **Grafik.** Altair (Streamlit ile gelir). Uygulama paleti. Renk tek başına anlam taşımaz. Her grafiğin görünür alt metni ve Altair `description` alanı vardır.

Palet (v1 ile aynı): vurgu `#C8102E`, koyu vurgu `#A50E24`, mürekkep `#1F2328`, ikincil `#5B6370`, kılavuz `#E1E4EA`, sarı vurgu `#E8A33D`, açık sarı `#F2C98A`. Setler: GENERAL `#1F2328`, GENERAL_MODULE `#5B6370`, HISTORY `#E8A33D`, HISTORY_SLOT `#F2C98A`, GENERAL_REL `#C8102E`. Dersler (UCI): Matematik `#1F2328`, Portekizce `#E8A33D`. Modüller (OULAD, 7 renk): `#1F2328 #C8102E #E8A33D #5B6370 #A50E24 #F2C98A #8C96A3`.

---

## 1. Sayfa iskeleti

- Üst şerit (v1'deki gibi): marka düğmesi, dil seçici, "Girişe dön".
- Başlık bloğu: rapor başlığı, tek cümlelik alt başlık, "Okuma süresi ~20 dk" etiketi.
- **Bölüm gezinmesi:** `st.tabs` ile 10 sekme. Sekme etiketleri kısa (aşağıda). Seçili sekme `&bolum=` ile adres çubuğuna yazılır ve doğrudan açılabilir.
- Her bölümün yapısı:
  1. **Bu bölümde** kutusu (2–3 cümle: soru ve cevabın tek cümlesi).
  2. Metin + görseller.
  3. **Bulgu** kutuları (kırmızı sol kenar, en fazla 2 cümle).
  4. Varsa **Hata ve düzeltme** kutusu (sarı sol kenar; bölüm 9'a bağlantı).
  5. **Ham tablolar** açılır bölümü: notebook'taki tabloların aynısı, `st.dataframe` + CSV indir düğmesi.
- Sayfa sonu: "Bu raporu kaynak koduyla birlikte yeniden üretmek için" kısa satırı ve bölüm 10'a bağlantı.

Sekmeler:

| Kimlik | TR | EN |
|---|---|---|
| ozet | Özet | Summary |
| veri | Veri setleri | Datasets |
| uci | UCI keşif | UCI exploration |
| oulad | OULAD keşif | OULAD exploration |
| model | Modelleme | Modelling |
| kural | Karar kuralı | Decision rule |
| sistem | Sisteme köprü | Bridge to the system |
| hoca | Hoca etkisi | Teacher effect |
| hatalar | Hatalar ve düzeltmeler | Errors and fixes |
| kaynak | Sınırlar ve kaynaklar | Limits and sources |

---

## 2. Paket v2: `arastirma.json` eklemeleri

v1 anahtarları aynen kalır. Aşağıdakiler eklenir. "Kaynak" sütunu, notebook'un o tabloyu/grafiği üretirken çağırdığı fonksiyondur; paketleyici aynısını çağırır. Fonksiyon notebook içinde tanımlıysa (ör. 02'deki `rate_by_bin`, `print_rate_table`, `LABELS`) önce pakete taşınır (ilke 3).

### 2.1 UCI (`uci.*`)

| Anahtar | İçerik | Kaynak (notebook 01) |
|---|---|---|
| `uci.pass_threshold_20`, `uci.pass_grade_100` | 10 ve 50 | hücre 4 |
| `uci.g3_zero_by_subject` | `{mat, por}` | hücre 6 (`add_derived_columns`) |
| `uci.g3_hist` | `[{subject, g3, n}]`, g3 = 0..20 | hücre 6 histogramının verisi |
| `uci.top_corr` | eda_summary.top_abs_correlation_with_g3 | hücre 8 |
| `uci.corr_matrix` | `{columns: [...], values: [[...]]}` | hücre 9 (`NUMERIC_COLUMNS`) |
| `uci.grades` | `[{subject, g1, g2, g3}]`, 1.044 satır (UCI CC BY 4.0; atıf sayfada) | hücre 11 saçılımının verisi |
| `uci.feature_sets` | `{early: [...], midterm: [...]}` | hücre 15 (`feature_columns`) |
| `uci.absence` | v1'deki gibi | `data_science.absence` |

### 2.2 OULAD keşif (`oulad.*`)

| Anahtar | İçerik | Kaynak (notebook 02) |
|---|---|---|
| `oulad.zip_sha256` | arşiv sağlama değeri | hücre 2 |
| `oulad.tables` | `[{table, rows, cols}]`, studentVle dahil | hücre 2 |
| `oulad.sample` | `{cutoff_day, rows_before, rows_removed, rows_kept}` | hücre 5 |
| `oulad.final_result` | `[{final_result, n, at_risk}]` | hücre 5 |
| `oulad.split` | v1'deki gibi | hücre 7 |
| `oulad.risk_pivot` | `[{module, presentation, n, rate}]` | hücre 10 |
| `oulad.hist_vs_current` | `[{module, presentation, n, rate, hist_rate}]` | hücre 13 |
| `oulad.slot_means` | `[{module, presentation, assessment_type, slot, n, mean_score}]` | hücre 16 |
| `oulad.signals` | `{n_unsubmitted, vle_clicks, score_mean, score_vs_hist}`; her biri `[{bin, n, rate}]`, yalnız train | hücre 20, 23, 26, 29 (`rate_by_bin`) |
| `oulad.data_notes.ggg` | `[{presentation, n_rows, n_expected_min, n_expected_max, score_mean_missing, vle_clicks_positive}]` | hücre 32 |
| `oulad.data_notes.bbb_zero_weight` | ağırlığı 0 olan TMA'yı tek teslim eden öğrenci sayısı | WEEK_09 veri notu 2'nin hesabı (paket fonksiyonu; yoksa DUR) |
| `oulad.feature_map` | `[{feature, group, school_tr, school_en}]` | hücre 34 (`read_feature_catalog`) |

### 2.3 Model (`model.*`)

| Anahtar | İçerik | Kaynak |
|---|---|---|
| `model.presentations` | `[{presentation, split, n, n_positive}]` | notebook 03 hücre 4 |
| `model.selected_params` | model_metrics.selected_params | JSON |
| `model.test_metrics` | 5 set × 2 model × 6 metrik `{estimate, low, high}` | JSON |
| `model.paired` | 5 karşılaştırma × 2 model × 3 metrik | JSON |
| `model.validation_rows` | set × model × metrik (doğrulama) | JSON |
| `model.module_roc` | `[{set, module, period, n, n_positive, roc_auc}]` (doğrulama ve test) | JSON (validation.modules, modules) |
| `model.base_rate` | `[{module, n, n_positive, hist_module_risk_rate, positive_rate, train_n, ...}]` ve `hist_rate_distinct_train` | notebook 03 hücre 10 |
| `model.calibration`, `model.lomo` | JSON'dakiler | JSON |
| `model.within_module` | JSON within_module | JSON |
| `rule.roc_auc` | rule_metrics.roc_auc | JSON |

### 2.4 Doğrulama

Paketleyici testleri v1'deki gibi (determinizm, senkron, anahtar varlığı) ve ek olarak: notebook OZET hücrelerinde basılan her değer paketle aynı (01, 02, 03); `oulad.signals.n_unsubmitted` 0/1/2/3 dilimlerinin oranları notebook 02 hücre 20 çıktısıyla aynı; `uci.g3_hist` toplamı 1.044; `model.base_rate` train'deki farklı geçmiş oran sayısı 8.

---

## 3. Bölüm: Özet (`ozet`)

v1'deki hero, üç özet kartı, sentetik veri uyarısı ve "Soru" metni burada kalır. Eklenenler:

**Cevapladıklarımız / cevaplayamadıklarımız** (iki sütun):

TR sol başlık **Bu verilerle gösterebildiklerimiz**:
- Öğrencinin kendi izinden (ödev, not, etkinlik) dersin 60. gününde anlamlı bir erken uyarı kurulabiliyor; sınıf içi sıralama başarısı ROC AUC ≈ {sets.within_module_mean.GENERAL.test:roc}.
- Dersler arasında risk seviyesi gerçekten farklı ve dönemden döneme kayıyor.
- Eğitilmeyen, sonuca bakmayan iki sinyalli bir kural, modelin isabetlerinin %{rule.capture_rule2.2014J:yuzde}'ini yakalıyor.

TR sağ başlık **Gösteremediklerimiz**:
- Hocanın etkisi: iki veri setinde de hoca bilgisi yok (bölüm 8).
- Herhangi bir sinyalin nedensel etkisi: bütün bulgular ilişkiseldir.
- Bir Türk lisesine doğrudan genelleme: veriler Portekiz liseleri ve İngiltere'de uzaktan eğitimden.

EN left **What these data let us show** / right **What they do not** (aynı maddeler, İngilizce):
- From a student's own trace (assignments, grades, activity) a meaningful early warning can be built at day 60 of a course; within-class ranking performance is ROC AUC ≈ {…}.
- Risk levels genuinely differ between courses and drift from term to term.
- An untrained two-signal rule that never looks at outcomes catches {…}% of the model's hits.
- The teacher effect: neither dataset records the teacher (section 8).
- The causal effect of any signal: every finding is associational.
- Direct generalisation to a Turkish high school: the data come from Portuguese high schools and UK distance learning.

**Görsel Z1: Araştırma yolculuğu** (statik Altair ya da HTML zaman çizelgesi, 4 durak). Her durakta: hafta, soru, yapılan, karar.

| Durak | TR | EN |
|---|---|---|
| H8 | **Soru doğdu.** UCI'da erken notlar finali belirliyor, devamsızlık ilk bakışta zayıf göründü (hata). Ders ve sınav bağlamı yok. *Karar:* bağlam için zamansal bir veri setine geç. | **The question.** In UCI early grades drive the final; absence first looked weak (an error). No course or exam context. *Decision:* move to a time-ordered dataset. |
| H9 | **Veri kuruldu.** OULAD, 60. gün kesimi, sızıntısız zamansal bölme, ders geçmişi özellikleri. *Karar:* model yok, önce betimleme. | **The data.** OULAD, day-60 cutoff, leak-free temporal split, course-history features. *Decision:* no model yet, describe first. |
| H10 | **Hipotez sınandı.** Ders geçmişi tahmini iyileştirmedi; test sonucuna göre tasarlanan set doğrulamada çöktü. *Karar:* sınıf içi %20, mutlak olasılık yok, şeffaf kural. | **The test.** Course history did not improve prediction; a set designed after seeing test results collapsed on validation. *Decision:* within-class 20%, no absolute probability, transparent rule. |
| H11 | **Kurala dönüştü.** Okulda "girilmeyen ödev" karşılığı yok; iki sinyalli kural önceden yazılmış ölçütle sınandı ve kabul edildi. | **The rule.** The school has no "missed assignment" equivalent; a two-signal rule was tested against pre-written criteria and accepted. |

---

## 4. Bölüm: Veri setleri (`veri`)

**Bu bölümde**, TR: Çalışma iki açık veri setine dayanıyor. Biri küçük ve zengin öğrenci bilgisi taşıyan bir lise verisi, diğeri büyük ve zamansal bir uzaktan eğitim verisi. Hangisinin hangi soruya cevap verebildiği, sonuçları anlamanın anahtarı.
EN: The study rests on two open datasets: a small high-school dataset with rich student information, and a large, time-ordered distance-learning dataset. Which one can answer which question is the key to reading the results.

**Tablo D0: Yan yana karşılaştırma** (statik, sayılar paketten):

| Boyut | UCI Student Performance | OULAD |
|---|---|---|
| Kurum ve yer | İki lise, Portekiz | Open University, Birleşik Krallık |
| Eğitim türü | Yüz yüze lise | Uzaktan, üniversite |
| Zaman | Tek öğretim yılı | 2013–2014, dört dönem (sunum) |
| Büyüklük | {uci.total:tam} öğrenci-ders kaydı | {oulad.n_rows_raw:tam} öğrenci-ders kaydı, {oulad.n_vle_rows:tam} etkinlik satırı |
| Birim | Öğrenci × ders | Öğrenci × modül × sunum |
| Hedef | Final notu < 10 / 20 | Başarısız ya da dersi bırakmış |
| Zamansal sinyal | Yok (yalnızca dönem notları) | Var (günlük etkinlik, ödev tarihleri) |
| Ders bağlamı | İki ders | {oulad.n_courses:tam} ders-dönem, 7 modül |
| Hoca bilgisi | Yok | Yok |
| Sosyokültürel bilgi | Var (kullanılmadı) | Var (kullanılmadı) |
| Cevaplayabildiği | Hangi öğrenci bilgisi finalle ilişkili? | Erken uyarı mümkün mü; ders ve zaman bağlamı tahmini değiştirir mi? |
| Cevaplayamadığı | Erken uyarı (sınav tarihi yok), bağlam | Hoca etkisi, lise genellemesi |
| Lisans | CC BY 4.0 | CC BY 4.0 |

EN tablo: aynı satırlar İngilizce (Institution and place; Type of education; Time; Size; Unit; Target; Temporal signal; Course context; Teacher information; Socio-cultural information; Can answer; Cannot answer; Licence).

Altında TR: Sosyokültürel sütunlar iki veride de vardı ama hiçbir aşamada kullanılmadı: okul sisteminde bu bilgiler tutulmuyor ve bir risk işaretinin aile ya da çevre bilgisine dayanması etiketleme riski taşır.
EN: Socio-cultural columns existed in both datasets but were never used: the school system does not hold them, and a risk flag based on family or background would risk labelling students.

**Görsel D1: OULAD tabloları** (yatay çubuk, log ölçek, `oulad.tables`). Alt metin: "Yedi tablonun satır sayısı, logaritmik ölçek. En büyüğü günlük etkinlik kayıtları." / EN eşdeğeri.

**Görsel D2: Örneklem hunisi** (`oulad.sample`): tüm kayıtlar → 60. günden önce bırakanlar çıkarıldı → örneklem. Yanında TR not: "60. günden önce kaydını silenler çıkarıldı, çünkü o gün geldiğinde artık uyarılacak bir öğrenci yok. Sonra bırakanlar örneklemde kaldı ve riskli sayıldı." EN eşdeğeri.

**Görsel D3: Final sonuçları** (yığılmış çubuk, `oulad.final_result`): Distinction, Pass (riskli değil) / Fail, Withdrawn (riskli). Renk + etiket.

**Görsel D4: Bölme** (v1'deki O1 zaman çizelgesi; buraya taşınır). `model.presentations` ile her sunumun n ve pozitif sayısı da fareyle görünür.

---

## 5. Bölüm: UCI keşif (`uci`)

**Bu bölümde**, TR: Küçük bir lise verisinde finali neyin belirlediğine baktık. İki bulgu ve bir hata çıktı: dönem notları finali neredeyse belirliyor (bu yüzden erken uyarıda kullanılamazlar), geçmiş başarısızlık not dışındaki en güçlü işaret ve devamsızlık ilk analizde yanlışlıkla zayıf göründü.
EN: In a small high-school dataset we looked at what drives the final grade. Two findings and one error emerged: term grades nearly determine the final (so they cannot serve an early warning), past failure is the strongest non-grade signal, and absence wrongly looked weak in the first analysis.

**U1: Derse göre geçme oranı** (çubuk, `uci.pass_mat/por`; eşik notu: "Geçme: 20 üzerinden {uci.pass_threshold_20:tam}, okulun 100'lük sisteminde {uci.pass_grade_100:tam}").

**U2: Final notu dağılımı** (histogram, `uci.g3_hist`; ders seçici: Tümü / Matematik / Portekizce; G3 = 0 çubuğu sarı vurgulu ve fareyle "{n} kayıt; hepsinde devamsızlık 0").
Bulgu TR: Final notu 0 olan {uci.g3_zero:tam} kayıt (Matematik {uci.g3_zero_by_subject.mat:tam}, Portekizce {uci.g3_zero_by_subject.por:tam}) dağılımın geri kalanından kopuk duruyor: bunlar büyük olasılıkla bir not değil, sınava girmemek ya da ayrılmak.
EN: The {…} records with a final grade of 0 (Mathematics {…}, Portuguese {…}) sit apart from the rest of the distribution: most likely they are not a grade but a missed exam or a dropout.

**U3: En güçlü on ilişki** (yatay çubuk, işaretli, `uci.top_corr`; pozitif mürekkep, negatif kırmızı + işaret etiketi).

**U4: Korelasyon ısı haritası** (`uci.corr_matrix`, -1..1 ıraksak ölçek, fareyle değer). Alt metin TR: "Sayısal sütunların birbirleriyle Pearson korelasyonu. Dönem notları (G1, G2) finalle (G3) neredeyse aynı bilgiyi taşıyor."

**U5: Sızıntı** (saçılım, `uci.grades`; seçici: G1 → G3 / G2 → G3; noktalar hafif titreşimli; köşegen çizgi; ders rengi). Bulgu TR: G2 ile G3 arasında r = {uci.corr_g2:kor}. Dönem sonu notunu bilen bir model finali "tahmin etmez", neredeyse okur. Bu yüzden iki özellik seti tanımlandı: EARLY ({early sayısı} sütun, dönem notu yok) ve MIDTERM (yalnız G1).
EN: Between G2 and G3, r = {…}. A model that knows the end-of-term grade does not "predict" the final, it nearly reads it. So two feature sets were defined: EARLY ({n} columns, no term grades) and MIDTERM (G1 only).

**U6: Devamsızlık** (v1'deki U1 grafiği, dahil/hariç seçicili). Hata kutusu: v1 metni + "Bölüm 9, Hata 1".

**Tablo U7: Özellik setleri** (iki sütunlu liste, `uci.feature_sets`; sosyokültürel olanlar gri ve "sistemde kullanılmaz" etiketiyle).

Ham tablolar: korelasyonlar, devamsızlık dilimleri (dahil/hariç), G3=0 sayıları.

Bölüm sonu TR: UCI'ın cevaplayamadığı soru bağlamdı: tek yıl, iki ders, sınav tarihi yok. Bu yüzden bağlam hipotezi OULAD'a taşındı.

---

## 6. Bölüm: OULAD keşif (`oulad`)

**Bu bölümde**, TR: Model kurmadan önce veriye baktık. Risk seviyesi derse ve döneme göre belirgin biçimde değişiyor; öğrencinin kendi izindeki erken sinyaller ise riskle çok güçlü ve düzenli bir ilişki gösteriyor. Bu bölümdeki her şey betimseldir; neden ileri sürmez.
EN: Before modelling we looked at the data. Risk levels vary clearly by course and term, while early signals in the student's own trace show a strong, orderly relationship with risk. Everything here is descriptive; nothing claims a cause.

**O1: Modül × dönem risk ısı haritası** (`oulad.risk_pivot`; boş kesişim gri; fareyle n ve oran). Bulgu TR: En düşük oran {min modül-dönem} (%{…}), en yüksek {max} (%{…}). Aynı modülün dönemleri arasındaki fark ise en fazla birkaç puan. (Değerler paketten: üretici `risk_pivot`'tan min/max ve modül içi en büyük fark alanlarını türetir.)

**O2: Geçmiş oran ve bu dönemin oranı** (saçılım, `oulad.hist_vs_current`; x = önceki dönemlerin oranı, y = bu dönemin oranı; y = x çizgisi; modül rengi; fareyle modül-dönem, n). Alt metin TR: "Noktalar çizginin altındaysa ders o dönem geçmişinden daha iyi gitmiştir. Noktaların çoğu çizginin altında: risk zamanla düştü."

**O3: Aynı ödevin dönemler arası ortalaması** (küçük çoklu grafik, modül başına bir pano, `oulad.slot_means`; x = sunum, y = ortalama not, çizgi = yuva). Alt metin: notebook 02 hücre 17 metni.

**O4: Erken sinyaller** (tek grafik + sinyal seçici; `oulad.signals`; x = dilim, y = risk oranı, çubuk üstünde n; "eksik" dilimi ayrı ve gri). Seçenekler ve altındaki tek cümleler:
- Teslim edilmeyen ödev / Unsubmitted assignments. TR: "Tek bir ödevi teslim etmemek, risk oranını %{0 dilimi} düzeyinden %{1 dilimi} düzeyine çıkarıyor."
- Tıklama (etkinlik) / Clicks. TR: "En az etkin beşte birlik grupta risk %{ilk}, en etkin grupta %{son}."
- Ortalama not / Average score. TR: "Notu boş olanların riski (%{eksik}) orta dilimlerden yüksek: not almamış olmak da bir işaret."
- Geçmiş nota göre fark / Score versus course history. TR: "Aynı ödevin geçmiş ortalamasının altında kalanlar daha riskli."
Bulgu TR: Dört sinyalin hepsi riskle düzenli bir ilişki gösteriyor. Ama bu ilişkiler birbirinden bağımsız değil; hangisinin ne kadar katkı verdiğini ancak model ve SHAP söyleyebilir (bölüm 7).
Nedensellik notu (her seçenekte): "Birlikte görülen örüntüdür, neden değildir."

**Veri notları kutusu** (`oulad.data_notes`): GGG'nin iki döneminde 60. güne kadar notlu ödev yok; BBB 2014J'de ağırlığı sıfır olan bir ödev. TR/EN metni WEEK_09 veri notları 1–2'den, sayılar paketten. Bu kutunun bağlantısı: bölüm 7, Görülmemiş ders.

**Tablo O5: Özellik → okul karşılığı** (`oulad.feature_map`, `{feature, group, school_tr, school_en}`; okul karşılığına göre gruplu: not, devamsızlık, ders bağlamı).

Ham tablolar: tablo boyutları, final sonuçları, risk pivotu, geçmiş-şimdi, yuva ortalamaları, dört sinyal tablosu, GGG özeti.

---

## 7. Bölüm: Modelleme (`model`)

**Bu bölümde**, TR: Beş özellik setini iki model türüyle, aynı test döneminde bir kez karşılaştırdık. Dersin geçmişini bilmek tahmini iyileştirmedi, kötüleştirdi; testte en iyi görünen set ise bağımsız doğrulamada sonuncu oldu. Sonuçlar mütevazı ama tutarlı: işe yarayan, öğrencinin kendi izi.
EN: We compared five feature sets with two model types, once, on the same test term. Knowing the course history did not improve prediction; it made it worse. The set that looked best on test came last on independent validation. The results are modest but consistent: what works is the student's own trace.

**Tablo M0: Özellik setleri** (v1 4.5 girişindeki tanımlar + notebook 03 hücre 2 metni; "keşifsel" etiketi HISTORY_SLOT ve GENERAL_REL'de).

**Görsel M1: Protokol** (statik şema): 2013J'de eğit → 2014B'de ayar seç (log loss) → 2013J + 2014B ile yeniden eğit → 2014J'de bir kez değerlendir; bootstrap B = 1.000, modül içi tabakalı, eşli. Seçilen ayarlar fareyle (`model.selected_params`).

**M2: Metrik matrisi** (ısı haritası; satır = set, sütun = model; metrik seçici: ROC AUC, PR AUC, Brier, log loss, %20 kesinlik, %20 yakalama; "düşük daha iyi" metriklerde ölçek ters ve başlıkta yazılı; hücrede değer, fareyle %95 aralık). Altında tam tablo (açılır).

**M3: Eşli farklar** ("forest" grafiği; `model.paired`; satır = karşılaştırma, nokta = fark, çizgi = %95 aralık, 0 dikey çizgisi; model ve metrik seçici). Bulgu TR: HISTORY − GENERAL farkı iki model türünde de sıfırın altında ve aralık sıfırı içermiyor: ders geçmişi tahmini kötüleştiriyor.

**M4: Doğrulama → test** (v1'deki C2 eğim grafiği).

**M5: Modül bazında sıralama** (nokta grafiği; `model.module_roc`; satır = modül, x = ROC AUC, iki dönem iki şekil; set seçici). Bulgu TR: Sınıf içinde setler arasındaki fark binde birkaç düzeyinde ve dönemden döneme sırası değişiyor.

**M6: Taban oran ve kayma** (v1'deki C1 kalibrasyon grafiği).

**M7: Geçmiş oran neden yanılttı?** (`model.base_rate`; modül başına üç nokta: geçmiş oran, train'deki oran, testteki oran; ok yönü). Bulgu TR: Model geçmiş risk oranını {satır sayısı} satırdan değil, yalnızca {model.hist_rate_distinct_train:tam} farklı dönem değerinden öğreniyor; üstelik risk zamanla düştü. Sonuç: geçmiş oran yeni dönemde tahmini yukarı itiyor.

**M8: Görülmemiş ders** (v1'deki L1 grafiği; ek seçici: ROC AUC / ortalama tahmin).

**M9: SHAP** (v1'deki S1 + S2).

**Dürüstlük kutusu** (v1 4.6 metni ve tablosu burada; bölüm 9'a bağlantı).

Ham tablolar: test metrikleri, eşli farklar, doğrulama, modül ROC, taban oran, LOMO, SHAP.

---

## 8. Bölüm: Karar kuralı (`kural`)

v1 4.9 (K1 kapasite kaydırıcısı) ve 4.10 (R1) burada. Eklenen:

**R2: Kural ile modelin modül bazında sıralaması** (saçılım; `rule.roc_auc`; x = kural ROC AUC, y = model ROC AUC; y = x çizgisi; nokta = modül-dönem). Bulgu TR: Model her modül-dönemde önde, ama fark küçük: noktalar çizginin hemen üstünde. Şeffaflığın bedeli bir sıçrama değil, düzenli ve küçük bir kayıp.
EN: The model leads in every module-term, but narrowly: the points sit just above the line. The price of transparency is not a jump but a small, steady loss.

K1 canlı cümlesi EN: "At {oran} flagged, within-class ranking marks {n_flagged} students; {precision} of them really struggled, and {recall} of the struggling students were caught."

---

## 9. Bölüm: Sisteme köprü (`sistem`)

v1 4.11 (eşleme tablosu ve paragraf). Eklenen kısa metin, TR: Sistemde model yok, çünkü okulda "bu öğrenci sonunda başarısız oldu" bilgisi tutulmuyor; model eğitecek etiket yok. Taşınan yalnızca tarif: hangi iki sinyalin, hangi yönde, sınıf içinde nasıl sıralanacağı ve kaç öğrencinin işaretleneceği. Okulun demo verisi sentetiktir ve bu rapordaki hiçbir sonuç ondan çıkarılmamıştır.
EN: There is no model in the system, because the school does not record "this student eventually failed"; there is no label to train on. Only the recipe is carried over: which two signals, in which direction, how they are ranked within a class, and how many students are flagged. The school's demo data is synthetic, and no result in this report is drawn from it.

---

## 10. Bölüm: Hoca etkisi (`hoca`)

Bu bölümün amacı bir eksikliği gizlemek değil, **sonucun kendisi** olarak sunmaktır.

**Bu bölümde**, TR: Gerçek hayatta öğretmenler fark yaratır; aynı ders, farklı bir öğretmenle farklı sonuç verebilir. Bu çalışmanın başındaki soru da buydu. Burada bu verilerle hoca etkisini neden ölçemediğimizi, ölçmek için neyin gerektiğini ve elimizdeki verilerin bu konuda neyi gösterip neyi gösteremediğini açıkça yazıyoruz.
EN: In real life teachers make a difference; the same course can turn out differently with a different teacher. That was the question this study started from. Here we state plainly why these data cannot measure a teacher effect, what it would take to measure one, and what our data do and do not show about it.

**10.1 Neden ölçemiyoruz?** TR: Bir öğretmenin etkisini görmek için, aynı dersi aynı öğretmenden alan birçok öğrenci grubunu yıllar boyunca izlemek ve bunları başka öğretmenlerin gruplarıyla, öğrencilerin başlangıç düzeyini hesaba katarak karşılaştırmak gerekir. Ancak o zaman "bu fark öğretmenden mi, o yılın öğrencilerinden mi, dersin içeriğinden mi, sınavın zorluğundan mı?" sorusu ayrılabilir. İki veri setimizde de hangi öğrencinin hangi öğretmenden ders aldığı yok. OULAD'da ders ve dönem var; ama bir ders-dönem, öğretmeni, materyali, sınavı ve o dönemin öğrencilerini tek bir pakette taşıyor.
EN: To see a teacher's effect, one needs to follow many groups of students taking the same course from the same teacher across years, and compare them with other teachers' groups while accounting for students' starting level. Only then can "is this difference due to the teacher, that year's students, the course content, or the exam difficulty?" be separated. Neither dataset records which student was taught by which teacher. OULAD has course and term; but a course-term carries the teacher, the material, the exam and that term's students in one bundle.

**Görsel H1: Neyi ayırabildik?** (katmanlı şema, 5 satır; durum etiketi + renk + metin; renk tek başına anlam taşımaz):

| Katman | Durum | TR açıklama | EN |
|---|---|---|---|
| Öğrencinin kendi izi | Gösterildi | Erken sinyaller riskle güçlü ve tutarlı ilişkili; sınıf içi sıralama iki dönemde tutuyor. | Shown: early signals relate strongly and consistently to risk; within-class ranking holds across two terms. |
| Ders | Gösterildi (seviye) | Dersler arasında risk seviyesi farklı. Ama bu fark kimin sıralamasının değişeceğini belirlemiyor. | Shown (level): risk levels differ between courses, but this does not change who ranks as at risk. |
| Zaman (dönem) | Gösterildi (kayma) | Aynı dersin riski dönemden döneme kayıyor; geçmiş, geleceği güvenilir biçimde taşımıyor. | Shown (drift): a course's risk drifts between terms; the past does not reliably carry into the future. |
| Ders × dönem paketi | Ölçüldü, ayrıştırılamadı | Öğretmen, materyal, sınav ve öğrenci grubu birlikte; bunları birbirinden ayırmak mümkün değil. | Measured, not separable: teacher, material, exam and cohort together; they cannot be told apart. |
| Öğretmen | Ölçülemedi | Veri yok. | Not measurable: no data. |

**10.2 Elimizdeki verilerle söyleyebileceğimiz** TR: Ders-dönem düzeyindeki toplam farkı ölçebildik; hoca etkisi, eğer varsa, bu paketin içinde bir yerde. Bu farkın üst sınırını (O1, M6) ve zamanla ne kadar kaydığını (O2, M7) gösterdik. Bu yüzden sistemi hoca etkisine **duyarsız** kurduk: her sınıf kendi içinde sıralanıyor, mutlak bir eşik ya da olasılık yok. Bir öğretmenin sınıfı genel olarak daha yüksek ya da düşük notlar alıyorsa, bu bayrakların sayısını değiştirmiyor; her öğretmene sınıfının yaklaşık beşte biri kadar izleme kapasitesi düşüyor. Hoca etkisini ölçemedik, ama sistemin ona dayanmamasını sağladık.
EN: We could measure the total difference at the course-term level; any teacher effect lies somewhere inside that bundle. We showed the upper bound of that difference (O1, M6) and how much it drifts over time (O2, M7). So we built the system to be **insensitive** to teacher effects: each class is ranked within itself, with no absolute threshold or probability. If one teacher's class scores higher or lower overall, that does not change the number of flags; every teacher gets follow-up capacity for about one fifth of the class. We could not measure the teacher effect, but we made sure the system does not depend on it.

**Tablo H2: Gerçek bir çalışma için gereken veri**

| Gereken | UCI | OULAD | Okul sistemi (bugün) | Okul sistemi (yıllar içinde) |
|---|---|---|---|---|
| Öğrenci–öğretmen eşleşmesi | Yok | Yok | Sınıf öğretmeni var; ders öğretmeni yok | Ders öğretmeni eklenebilir |
| Aynı öğretmen, birden çok yıl | Yok | Yok | Yok (tek yıl) | Birikir |
| Öğrencinin başlangıç düzeyi | Kısmen (önceki başarısızlık) | Kısmen (önceki deneme) | Yok | Önceki yıl notları |
| Sonuç etiketi (geçti/kaldı) | Var | Var | Yok | Birikir |
| Aynı sınav, farklı öğretmen | Yok | Yok | Yok | Ortak sınavlarla mümkün |

EN tablo: Requirement; Student–teacher link; Same teacher across years; Student's starting level; Outcome label; Same exam, different teachers (sütunlar: UCI, OULAD, School system today, School system over years).

**10.3 Etik not** TR: Öğretmen etkisi ölçülebilir hâle gelse bile, bu bir öğretmen sıralaması aracı olmamalıdır. Küçük sınıflarda ve az yılda bu tahminler çok gürültülüdür; tek başına karar dayanağı olamaz. Okul asistanı da "hangi öğretmen daha başarılı" sorusuna not ortalamasıyla cevap vermez.
EN: Even if teacher effects became measurable, this should not become a tool for ranking teachers. With small classes and few years these estimates are very noisy and cannot be the sole basis for a decision. The school assistant likewise does not answer "which teacher is better" with grade averages.

Bölüm sonu Bulgu kutusu, TR: **Bu verilerle hoca etkisi hakkında söylenebilecek en dürüst cümle: ölçemiyoruz, ama ders-dönem düzeyindeki bütün bağlam farkının sistemin bayraklarını bozmadığını gösterebiliyoruz.**
EN: **The most honest sentence these data allow about the teacher effect: we cannot measure it, but we can show that the whole course-term context difference does not distort the system's flags.**

---

## 11. Bölüm: Hatalar ve düzeltmeler (`hatalar`)

**Bu bölümde**, TR: Bir analizin güvenilirliği, hatalarını nasıl bulduğuyla ölçülür. Aşağıdaki her kayıt belirtiyi, kök nedeni, düzeltmeyi ve düzeltmeden sonra neyin değiştiğini gösterir.
EN: An analysis is as trustworthy as the way it finds its own mistakes. Each record below shows the symptom, the root cause, the fix, and what changed afterwards.

Kart yapısı: başlık · hafta · tür etiketi (Veri / Yöntem / Yorum / Yeniden üretilebilirlik) · Belirti · Kök neden · Düzeltme · Sonra · bağlantılı görsel. Kayıtlar (metinler WEEK raporlarından; sayılar paketten):

| # | Başlık TR / EN | Tür | Bağlantı |
|---|---|---|---|
| 1 | Devamsızlık zayıf sanıldı / Absence looked weak | Veri | U6 (dahil/hariç seçici bu kaydın "önce/sonra" görünümüdür) |
| 2 | Testten esinlenen set doğrulamada çöktü / A test-inspired set collapsed on validation | Yöntem | M4 |
| 3 | "Kaynak yalnızca geçmiş oran" tahmini / "Only the past rate" guess | Yorum | M3 (HISTORY_SLOT satırı) |
| 4 | "GENERAL_REL yalnız seviyeyi kaçırıyor" tahmini / "GENERAL_REL only misses the level" guess | Yorum | M4, M5 |
| 5 | Ders geçmişi hipotezi desteklenmedi / Course-history hypothesis not supported | Yöntem (hata değil, çürüyen hipotez) | M3, M7 |
| 6 | Görülmemiş ders grafiğinin alt metni yanlış / Wrong caption on the unseen-course chart | Yorum | M8 |
| 7 | Kuralın ilk sinyalinin okulda karşılığı yok / The rule's first signal has no school counterpart | Yöntem | R1 |
| 8 | Analiz mantığı notebook hücresindeydi / Analysis logic lived in a notebook cell | Yeniden üretilebilirlik | — |

Kart 5'in "Sonra" alanı TR: "Hipotezin yarısı tuttu (ders seviyesi), yarısı tutmadı (ders geçmişinin sıralamaya katkısı). İkisi de rapora yazıldı."
Kart 8 TR: "Belirti: Rapor 'mantık paketten çağrılır' diyordu, ama devamsızlık analizi notebook hücresinde tanımlıydı. Düzeltme: fonksiyonlar `data_science.absence` modülüne taşındı; notebook oradan çağırıyor; Hafta 8 değerleri testle doğrulandı."

---

## 12. Bölüm: Sınırlar ve kaynaklar (`kaynak`)

v1 4.12 ve 4.13 metinleri. Eklenenler:
- Notebook'lar: `notebooks/html/` altındaki altı HTML dosyası için indirme düğmeleri (TR/EN); dosyalar pakete değil `frontend/assets/arastirma/notebooks/` altına kopyalanır ve senkron testine girer.
- Kaynakça: Cortez ve Silva (2008); Kuzilek, Hlosta ve Zdrahal (2017); scikit-learn, SHAP (sürümleri requirements'tan).
- Yazar satırı: "Ensar Bera Ergin · Türksat A.Ş. yaz stajı · 2026".

---

## 13. Görevler

Paket:
- **P1 (UCI):** 2.1 anahtarları. Notebook 01 hücrelerinde tanımlı hesap varsa önce pakete taşınır.
- **P2 (OULAD keşif):** 2.2 anahtarları. Notebook 02'de tanımlı `rate_by_bin`, `print_rate_table`, `LABELS` ve benzerleri önce pakete taşınır; notebook oradan çağırır; çıktılar değişmez (notebook yeniden çalıştırılıp OZET karşılaştırılır).
- **P3 (model):** 2.3 anahtarları + 2.4 doğrulamaları.

Sayfa:
- **S1 (iskelet):** sekmeler, `&bolum=`, bütün metinler (TR/EN), kutular, statik tablolar, ham tablo açılırları ve CSV, mevcut v1 bölümlerinin taşınması. Grafik fonksiyonları boş.
- **S2:** Özet, Veri setleri, UCI grafikleri (Z1, D1–D4, U1–U6).
- **S3:** OULAD keşif grafikleri (O1–O4).
- **S4:** Modelleme grafikleri (M1–M9).
- **S5:** Karar kuralı, Hoca etkisi, Hatalar (K1, R1, R2, H1, hata kartları).
- **S6:** Cila: mobil, erişilebilirlik, notebook indirme, yükleme süresi (paket bir kez okunur; büyük veri yalnızca ilgili sekmede çizilir).

Her görev v1'deki yasaklar ve test ilkeleriyle: metinde elle rakam yok, her yer tutucu çözülür, sayfa backend'e dokunmaz, TR/EN istisnasız çizilir.
