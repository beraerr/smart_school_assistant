"""Araştırma sayfasının TR/EN metinleri (docs/arastirma_sayfasi_spec.md bölüm 3 ve 4;
docs/arastirma_raporu_spec_v2.md bölüm 3–12; docs/arastirma_raporu_spec_v2_eki.md bölüm 1–3).

Metinler belirtimden birebir alınmıştır. `{yol:bicim}` alanları paketlenmiş JSON'dan
(`assets/arastirma/arastirma.json`) doldurulur; sayfada paket değeri olan hiçbir rakam elle
yazılmaz. Elle kalan rakamlar yıl, lisans, gün sayısı, ölçek, kimlik (B1, E3, H8, G3, md5) ve
notebook adı gibi sabit adlardır; testte anahtar bazında açık bir izin listesiyle sınanır
(frontend/tests/test_arastirma_metin_yamasi.py). İstisna: `ek_l1` ve `ek_e4_metin` dış
kaynaklı literatür sayıları içerir (bkz. ilgili anahtarlardaki yorum). `turev.*` yolları
paketten sayfa katmanında türetilir (bkz. `arastirma.turev`).
Biçimler: tam, yuzde, yuzdetam, roc, kor, puan, metin (bkz. `arastirma.bicimle`). Yüzde işaretini
metin değil biçimleyici koyar.

`EKSIK_EN`: İngilizce karşılığı henüz olmayan anahtarlar. Boş olmalıdır; sayfa listedeki
blokları İngilizce çizmez.
"""

import re

BICIMLER = frozenset({"tam", "yuzde", "yuzdetam", "roc", "kor", "puan", "metin"})
YER_TUTUCU = re.compile(r"\{([^{}:\s]+):([a-z]+)\}")

# İngilizce karşılığı henüz olmayan bloklar. Metin yaması (docs/metin_yamasi.json) ile hepsi
# yazıldı; liste boş kalmalıdır. Test gerçek eksiklerle birebir karşılaştırır.
EKSIK_EN: tuple[str, ...] = ()

# Bölüm 4.13 kod bloğu; belirtimdeki `…explain`, `…figures`, `…rule` kısaltmaları
# data_science/oulad/{explain,figures,rule}.py modüllerine açıldı.
KOD_BLOGU = (
    "python -m data_science.oulad.model\n"
    "python -m data_science.oulad.explain\n"
    "python -m data_science.oulad.figures\n"
    "python -m data_science.oulad.rule\n"
    "python scripts/arastirma_paketi.py"
)

METIN: dict[str, dict] = {
    "tr": {
        # 4.0
        "hero_baslik": "Dikkat bayrağının arkasındaki araştırma",
        "hero_alt": (
            "Okul sistemindeki risk sekmesi bir tahmin modelinden değil, açık veriyle sınanmış "
            "şeffaf bir kuraldan gelir. Bu sayfa o kurala nasıl varıldığını, neyin işe "
            "yaradığını, neyin yaramadığını ve neyi hâlâ bilmediğimizi gösterir."
        ),
        "ozet1_deger": "{rule.capture_rule2.2014J:yuzde}",
        "ozet1_aciklama": "Şeffaf kural, test döneminde modelin isabetlerinin bu kadarını yakalıyor.",
        "ozet2_deger": "{rule.gap_rule2.2014J:puan} puan",
        "ozet2_aciklama": (
            "Şeffaflığın bedeli: kesinlikte modelin gerisinde kalınan fark (sınıf içi "
            "{rule.flag_rate:yuzdetam})."
        ),
        "ozet3_deger": "Bilmiyoruz",
        "ozet3_aciklama": "Hocanın etkisi: iki veri setinde de hoca bilgisi yok, test edilemedi.",
        "uyari": (
            "Okul demosundaki öğrenciler ve notlar sentetiktir. Bu sayfadaki bütün bulgular "
            "yalnızca iki açık veri setinden gelir; okul verisinden bulgu çıkarılmamıştır."
        ),
        # 4.1
        "soru": (
            "Bir öğrencinin zorlandığını, iş işten geçmeden ve gerekçesiyle söyleyebilir miyiz? "
            "Ve risk yalnızca öğrenciye mi bağlı, yoksa derse, hocaya, o yılın koşullarına göre "
            "de değişir mi? Gerçek hayatta aynı notlarla bir derste güvende olan öğrenci, finali "
            "zor geçen başka bir derste risk altında olabilir. Bu doğruysa, yalnızca öğrenciye "
            "bakan bir yaklaşım yanılır."
        ),
        # 4.2
        "veri1_baslik": "UCI Student Performance",
        "veri1": (
            "Portekiz'de iki lise, iki ders (Matematik, Portekizce), tek öğretim yılı. "
            "{uci.total:tam} kayıt; notlar 0–20 (G1, G2 dönem içi, G3 final). "
            "Kaynak: Cortez ve Silva (2008), CC BY 4.0."
        ),
        "veri2_baslik": "OULAD",
        "veri2": (
            "Open University (Birleşik Krallık), uzaktan eğitim. {oulad.n_courses:tam} "
            "ders-dönem, {oulad.n_rows_raw:tam} öğrenci-ders kaydı, {oulad.n_vle_rows:tam} "
            "çevrim içi etkinlik satırı; 2013–2014. "
            "Kaynak: Kuzilek, Hlosta ve Zdrahal (2017), CC BY 4.0."
        ),
        "veri_alt": (
            "İkisi de bir Türk lisesi değil. Bu yüzden sisteme veri ya da model taşınmadı; "
            "yalnızca sınanmış bir kuralın tarifi taşındı."
        ),
        # 4.3
        "uci_bulgu": (
            "Erken notlar finali güçlü biçimde yansıtıyor (G1 ile G3 arasında "
            "r = {uci.corr_g1:kor}). Not dışındaki en güçlü işaret geçmiş başarısızlık "
            "(r = {uci.corr_failures:kor}). Devamsızlık ise ilk analizde zayıf görünüyordu; "
            "bu bir hataydı."
        ),
        "u1_dahil": "G3=0 dahil",
        "u1_haric": "G3=0 hariç",
        "uci_hata": (
            "**Hata kaydı.** {uci.g3_zero:tam} öğrencinin final notu 0 ve hepsinin devamsızlığı "
            "0 görünüyordu: büyük olasılıkla sınava girmeyen ya da ayrılan öğrenciler. Bu "
            "kayıtlar ilişkiyi bastırıyordu. Hariç tutulunca devamsızlık arttıkça geçme "
            "oranının düzenli düştüğü görüldü. Yine de en yüksek dilimdekilerin yarısı geçiyor: "
            "devamsızlık tek başına karar verdirmez."
        ),
        "uci_kapanis": (
            "UCI'da ders, hoca ya da sınav tarihi yok; gerçek bir erken uyarı kurulamıyor. "
            "Bağlam sorusu için daha büyük ve zamansal bir veriye geçtik."
        ),
        # 4.4
        "oulad_duzen": (
            "Her öğrenci-ders için yalnızca dersin **60. gününe kadar** olan bilgiyi kullandık: "
            "o güne kadar teslim edilen ödevler ve çevrim içi etkinlik. Hedef, dersi başarısız "
            "bitirmek ya da bırakmak. Modeller geçmiş dönemlerle eğitildi, gelecek bir dönemde "
            "bir kez sınandı; gelecekten bilgi sızmasın diye her sınır testlerle korundu."
        ),
        # 4.5
        "b45_giris": (
            "Deneyde beş özellik seti, iki model türüyle karşılaştırıldı: yalnızca öğrencinin "
            "izi (GENERAL), buna dersin kimliği (GENERAL_MODULE), dersin geçmiş dönemleri "
            "(HISTORY) ve iki kontrol seti. Cevap dört parçalı."
        ),
        "kart_ders": (
            "**Ders: evet.** Test döneminde dersin risk oranı "
            "{test.module_rate_min:yuzde} ({test.module_rate_min_module:metin}) ile "
            "{test.module_rate_max:yuzde} ({test.module_rate_max_module:metin}) arasında "
            "değişiyor. Dersin kimliğini bilmek tahminin seviyesini düzeltiyor."
        ),
        "kart_zaman": (
            "**Zaman: kayıyor.** Dersin geçmiş risk oranı, yeni dönemde tahmini yanlış yöne "
            "çekti; dersin geçmişini eklemek sonucu kötüleştirdi (ROC AUC farkı "
            "{sets.paired.HISTORY_GENERAL.hgb.estimate:roc} "
            "[{sets.paired.HISTORY_GENERAL.hgb.low:roc}; "
            "{sets.paired.HISTORY_GENERAL.hgb.high:roc}]). "
            "Bu yüzden sistem mutlak olasılık göstermez."
        ),
        "kart_sira": (
            "**Sınıf içi sıra: bağlam katkı vermedi.** \"Bu sınıfta kim daha riskli?\" "
            "sorusunda hiçbir bağlam tarifi iki dönemde tutarlı bir katkı yapmadı. İşe yarayan, "
            "öğrenciyi kendi sınıfı içinde değerlendirmek."
        ),
        "kart_hoca": (
            "**Hoca: bilmiyoruz.** İki veri setinde de hoca bilgisi yok; bu boyut test "
            "edilemedi. Okul sisteminde sonuç bilgisi biriktikçe sınanabilir."
        ),
        # 4.6
        "b46_metin": (
            "Testte en iyi görünen set (GENERAL_REL, test ROC AUC "
            "{sets.roc_test.GENERAL_REL.hgb.estimate:roc}) test sonuçlarına bakılarak "
            "tasarlanmıştı. Bağımsız doğrulama döneminde en düşük sonucu verdi "
            "({sets.roc_val.GENERAL_REL.hgb:roc}). Benimsemedik. Test sonucuna bakarak yapılan "
            "tasarım şans eseri kazananı seçebilir; bu noktadan sonra test dönemini dondurduk "
            "ve sonradan eklenen setleri \"keşifsel\" diye işaretledik."
        ),
        "tablo_46_baslik": "Doğrulanmayan açıklamalar",
        "tablo_46": {
            "ust": ("Tahmin", "Kontrol", "Sonuç"),
            "satirlar": (
                (
                    "Kötüleşmenin kaynağı yalnızca geçmiş risk oranı",
                    "O sütun çıkarıldı: sonuç aynı kaldı",
                    "Yanlış: geçmiş ödev özellikleri de genelleşmiyor",
                ),
                (
                    "GENERAL_REL yalnızca seviyeyi kaçırıyor, sıralaması sağlam",
                    "Doğrulamada sıralama ölçüldü: en düşük",
                    "Yanlış: set benimsenmedi",
                ),
            ),
        },
        "b46_kapanis": "Doğrulanmayan hiçbir açıklama sonuç olarak yazılmadı.",
        # 4.7
        "b47": (
            "Her ders sırayla eğitimden çıkarılıp yalnızca onda sınandı. Dersin kimliği yeni bir "
            "derse taşınamıyor; sıralama başarısı setler arasında neredeyse aynı (ortalama "
            "ROC AUC {lomo.mean.GENERAL.roc_auc:roc} – {lomo.mean.GENERAL_REL.roc_auc:roc}). "
            "Asıl uyarı GGG'de: o derste 60. güne kadar notlu ödev yok, model \"henüz ödev yok\" "
            "durumunu \"ödev teslim etmedi\" gibi okuyup riski çok yüksek tahmin ediyor. "
            "Sistemdeki karşılığı: notu olmayan sınıfta bayrak gösterilmez."
        ),
        # 4.8
        "b48": (
            "Modelin en çok dayandığı üç işaret: teslim edilmeyen ödev sayısı, not ortalaması "
            "ve son etkinlikten bu yana geçen süre. Bu, modelin davranışını anlatır; \"ödev "
            "teslim etmemek başarısızlığa yol açar\" anlamına gelmez."
        ),
        # 4.9
        "b49_giris": (
            "Bir öğretmenin izleyebileceği öğrenci sayısı sınırlı. Bayrak oranını değiştirerek "
            "kesinlik (bayraklananların ne kadarı gerçekten zorlandı) ile yakalama (zorlananların "
            "ne kadarı bayraklandı) arasındaki dengeyi görebilirsin. Öğrencileri tüm okulda "
            "birlikte sıralamak ile her sınıfın içinde sıralamak karşılaştırılıyor."
        ),
        "b49_secim": (
            "Sınıf içi {rule.flag_rate:yuzdetam} bayrak oranını seçtik: sınıf içi sıralama geniş bir "
            "bayrak oranı aralığında okul genelindeki sıralamanın önünde (kaydırıcıda görülebilir), "
            "her öğretmene eşit izleme kapasitesi veriyor ve dersin taban oranındaki kaymadan "
            "etkilenmiyor. Bedeli: riskin düşük olduğu sınıflarda isabet de düşüyor."
        ),
        # 4.10
        "b410": (
            "Okulda \"bu öğrenci sonunda başarısız oldu mu\" bilgisini tutan bir geçmiş yok; bu "
            "yüzden sistemde model eğitmek zaten mümkün değildi. Biz de soruyu tersinden sorduk: "
            "eğitilmeyen, sonuca bakmayan, sonucu görmeden önce sabitlenmiş şeffaf bir kural "
            "modelin ne kadar gerisinde kalır? Önce üç sinyalli bir kural sınandı; okul "
            "verisinde \"girilmeyen sınav\" karşılığı olmadığı için iki sinyalli sürüme (not "
            "ortalaması ve aktif gün) geçildi ve o da aynı ölçütle önceden yazılmış kurallarla "
            "sınandı."
        ),
        "r1_not": "GGG iki dönemde de hariç: 60. güne kadar notlu ödev yok.",
        # 4.11
        "tablo_11": {
            "ust": ("OULAD sinyali", "Okuldaki karşılığı", "Yön"),
            "satirlar": (
                (
                    "Not ortalaması (60. güne kadar)",
                    "Dönem içi not ortalaması",
                    "Düşük olan riskli",
                ),
                (
                    "Aktif gün sayısı",
                    "Mazeretsiz devamsızlık",
                    "Az aktif gün / çok devamsızlık riskli",
                ),
                (
                    "Teslim edilmeyen ödev",
                    "Okulda karşılığı yok",
                    "Kullanılmıyor",
                ),
            ),
        },
        "b411": (
            "Her sınıfta iki sinyalin sınıf içi sırası alınır, ortalamaya göre sınıfın yaklaşık "
            "beşte biri işaretlenir. Olasılık ya da puan gösterilmez; her bayrağın gerekçesi "
            "yazılır. Risk yalnızca öğretmen ve müdüre açıktır."
        ),
        # 4.12
        "sinirlar": (
            "Tek kurum, tek ülke ve uzaktan eğitim; bir Türk lisesine doğrudan genellenemez. "
            "Başarısız olmak ve dersi bırakmak aynı sınıfta toplandı; farklı süreçler olabilir. "
            "Yalnızca bir doğrulama dönemi var. Görülmemiş ders analizinde belirsizlik aralığı "
            "hesaplanmadı. SHAP nedensellik değildir. Okuldaki iki sinyal OULAD sinyallerinin "
            "birebir aynısı değil, en yakın karşılığıdır. Hocanın etkisi test edilemedi."
        ),
        # 4.13
        "yeniden_uretim": (
            "Bütün sayılar ve grafikler aynı kod paketinden üretilir; notebook'lar bu paketi "
            "çağırır, kod kopyalamaz. Çalıştırma komutları ve notebook adları: `01_uci_eda`, "
            "`02_oulad_eda`, `03_oulad_model` (TR/EN). Kaynakça: Cortez & Silva (2008); Kuzilek, Hlosta "
            "& Zdrahal (2017)."
        ),
        # ====================================================================================
        # Spec v2 (bölüm 3–12) ve spec v2 eki (bölüm 1–3). Metinler belirtimden birebir alınmıştır.
        # `%` işaretini yer tutucunun biçimi koyar (yuzde), metin değil.
        # ====================================================================================
        # --- Sekmeler (ek, bölüm 1) ---
        "sekmeler": {
            "ozet": "Özet",
            "veri": "Veri setleri",
            "uci": "UCI keşif",
            "oulad": "OULAD keşif",
            "model": "Modelleme",
            "kural": "Karar kuralı",
            "ek": "Ek analizler",
            "hoca": "Hoca etkisi",
            "sistem": "Sisteme köprü",
            "hatalar": "Hatalar ve düzeltmeler",
            "kaynak": "Sınırlar ve kaynaklar",
        },
        "okuma_suresi": "Okuma süresi ~20 dk",
        # --- 3. Özet ---
        "ozet_gosterebildik_baslik": "Bu verilerle gösterebildiklerimiz",
        "ozet_gosterebildik": (
            (
                "Öğrencinin kendi izinden (ödev, not, etkinlik) dersin 60. gününde anlamlı bir erken "
                "uyarı kurulabiliyor; sınıf içi sıralama başarısı ROC AUC ≈ "
                "{sets.within_module_mean.GENERAL.test:roc}."
            ),
            "Dersler arasında risk seviyesi gerçekten farklı ve dönemden döneme kayıyor.",
            (
                "Eğitilmeyen, sonuca bakmayan iki sinyalli bir kural, modelin isabetlerinin "
                "{rule.capture_rule2.2014J:yuzde} kadarını yakalıyor."
            ),
            (
                "Model ve kural, dersi bırakacak öğrenciden çok, devam edip başarısız olacak "
                "öğrenciyi biraz daha yüksek oranda buluyor."
            ),
        ),
        "ozet_gosteremedik_baslik": "Gösteremediklerimiz",
        "ozet_gosteremedik": (
            "Hocanın etkisi: iki veri setinde de hoca bilgisi yok (Hoca etkisi sekmesi).",
            "Herhangi bir sinyalin nedensel etkisi: bütün bulgular ilişkiseldir.",
            (
                "Bir Türk lisesine doğrudan genelleme: veriler Portekiz liseleri ve İngiltere'de "
                "uzaktan eğitimden."
            ),
        ),
        # Z1 (grafik; S2'de çizilir). Her durak: (kimlik, metin).
        "z1_duraklar": (
            (
                "H8",
                (
                    "**Soru doğdu.** UCI'da erken notlar finali belirliyor, devamsızlık ilk bakışta "
                    "zayıf göründü (hata). Ders ve sınav bağlamı yok. *Karar:* bağlam için zamansal "
                    "bir veri setine geç."
                ),
            ),
            (
                "H9",
                (
                    "**Veri kuruldu.** OULAD, 60. gün kesimi, sızıntısız zamansal bölme, ders "
                    "geçmişi özellikleri. *Karar:* model yok, önce betimleme."
                ),
            ),
            (
                "H10",
                (
                    "**Hipotez sınandı.** Ders geçmişi tahmini iyileştirmedi; test sonucuna göre "
                    "tasarlanan set doğrulamada çöktü. *Karar:* sınıf içi {rule.flag_rate:yuzdetam}, "
                    "mutlak olasılık yok, şeffaf kural."
                ),
            ),
            (
                "H11",
                (
                    "**Kurala dönüştü.** Okulda \"girilmeyen ödev\" karşılığı yok; iki sinyalli "
                    "kural önceden yazılmış ölçütle sınandı ve kabul edildi."
                ),
            ),
            (
                "H11+",
                (
                    "**Kendimizi sorguladık.** \"Çalışma çok doğrusal; model belki yalnızca dersi "
                    "bırakanı buluyor\" şüphesi {ek.summary.total:tam} beklentiyle önceden yazıldı, "
                    "md5 ile mühürlendi ve sınandı. Şüphe çürüdü."
                ),
            ),
        ),
        # --- 4. Veri setleri ---
        "veri_bu_bolumde": (
            "Çalışma iki açık veri setine dayanıyor. Biri küçük ve zengin öğrenci bilgisi taşıyan "
            "bir lise verisi, diğeri büyük ve zamansal bir uzaktan eğitim verisi. Hangisinin "
            "hangi soruya cevap verebildiği, sonuçları anlamanın anahtarı."
        ),
        "veri_d0_baslik": "Yan yana karşılaştırma",
        "veri_d0": {
            "ust": (
                "Boyut",
                "UCI Student Performance",
                "OULAD",
            ),
            "satirlar": (
                (
                    "Kurum ve yer",
                    "İki lise, Portekiz",
                    "Open University, Birleşik Krallık",
                ),
                (
                    "Eğitim türü",
                    "Yüz yüze lise",
                    "Uzaktan, üniversite",
                ),
                (
                    "Zaman",
                    "Tek öğretim yılı",
                    "2013–2014, dört dönem (sunum)",
                ),
                (
                    "Büyüklük",
                    "{uci.total:tam} öğrenci-ders kaydı",
                    (
                        "{oulad.n_rows_raw:tam} öğrenci-ders kaydı, {oulad.n_vle_rows:tam} etkinlik "
                        "satırı"
                    ),
                ),
                (
                    "Birim",
                    "Öğrenci × ders",
                    "Öğrenci × modül × sunum",
                ),
                (
                    "Hedef",
                    "Final notu < {uci.pass_threshold_20:tam} / 20",
                    "Başarısız ya da dersi bırakmış",
                ),
                (
                    "Zamansal sinyal",
                    "Yok (yalnızca dönem notları)",
                    "Var (günlük etkinlik, ödev tarihleri)",
                ),
                (
                    "Ders bağlamı",
                    "İki ders",
                    "{oulad.n_courses:tam} ders-dönem, {turev.oulad.n_modul:tam} modül",
                ),
                (
                    "Hoca bilgisi",
                    "Yok",
                    "Yok",
                ),
                (
                    "Sosyokültürel bilgi",
                    "Var (kullanılmadı)",
                    "Var (kullanılmadı)",
                ),
                (
                    "Cevaplayabildiği",
                    "Hangi öğrenci bilgisi finalle ilişkili?",
                    "Erken uyarı mümkün mü; ders ve zaman bağlamı tahmini değiştirir mi?",
                ),
                (
                    "Cevaplayamadığı",
                    "Erken uyarı (sınav tarihi yok), bağlam",
                    "Hoca etkisi, lise genellemesi",
                ),
                (
                    "Lisans",
                    "CC BY 4.0",
                    "CC BY 4.0",
                ),
            ),
        },
        "veri_sosyokultur": (
            "Sosyokültürel sütunlar iki veride de vardı ama hiçbir aşamada kullanılmadı: okul "
            "sisteminde bu bilgiler tutulmuyor ve bir risk işaretinin aile ya da çevre bilgisine "
            "dayanması etiketleme riski taşır."
        ),
        # D1 ve D2 alt metinleri (grafik; S2'de çizilir)
        "veri_d1_alt": (
            "Yedi tablonun satır sayısı, logaritmik ölçek. En büyüğü günlük etkinlik kayıtları."
        ),
        "veri_d2_not": (
            "60. günden önce kaydını silenler çıkarıldı, çünkü o gün geldiğinde artık uyarılacak "
            "bir öğrenci yok. Sonra bırakanlar örneklemde kaldı ve riskli sayıldı."
        ),
        # --- 5. UCI keşif ---
        "uci_bu_bolumde": (
            "Küçük bir lise verisinde finali neyin belirlediğine baktık. İki bulgu ve bir hata "
            "çıktı: dönem notları finali neredeyse belirliyor (bu yüzden erken uyarıda "
            "kullanılamazlar), geçmiş başarısızlık not dışındaki en güçlü işaret ve devamsızlık "
            "ilk analizde yanlışlıkla zayıf göründü."
        ),
        # U1 eşik notu (grafik; S2'de çizilir)
        "uci_u1_not": (
            "Geçme: 20 üzerinden {uci.pass_threshold_20:tam}, okulun 100'lük sisteminde "
            "{uci.pass_grade_100:tam}"
        ),
        "uci_u2_bulgu": (
            "Final notu 0 olan {uci.g3_zero:tam} kayıt (Matematik {uci.g3_zero_by_subject.mat:tam}, "
            "Portekizce {uci.g3_zero_by_subject.por:tam}) dağılımın geri kalanından kopuk "
            "duruyor: bunlar büyük olasılıkla bir not değil, sınava girmemek ya da ayrılmak."
        ),
        # U4 alt metni (grafik; S2'de çizilir)
        "uci_u4_alt": (
            "Sayısal sütunların birbirleriyle Pearson korelasyonu. Dönem notları (G1, G2) finalle "
            "(G3) neredeyse aynı bilgiyi taşıyor."
        ),
        "uci_u5_bulgu": (
            "G2 ile G3 arasında r = {uci.corr_g2:kor}. Dönem sonu notunu bilen bir model finali "
            "\"tahmin etmez\", neredeyse okur. Bu yüzden iki özellik seti tanımlandı: EARLY "
            "({turev.uci.n_early:tam} sütun, dönem notu yok) ve MIDTERM (yalnız G1)."
        ),
        "uci_hata_baglanti": "Hatalar ve düzeltmeler: Devamsızlık zayıf sanıldı",
        "uci_u7_baslik": "Özellik setleri",
        "uci_bolum_sonu": (
            "UCI'ın cevaplayamadığı soru bağlamdı: tek yıl, iki ders, sınav tarihi yok. Bu yüzden "
            "bağlam hipotezi OULAD'a taşındı."
        ),
        # --- 6. OULAD keşif ---
        "oulad_bu_bolumde": (
            "Model kurmadan önce veriye baktık. Risk seviyesi derse ve döneme göre belirgin "
            "biçimde değişiyor; öğrencinin kendi izindeki erken sinyaller ise riskle çok güçlü ve "
            "düzenli bir ilişki gösteriyor. Bu bölümdeki her şey betimseldir; neden ileri sürmez."
        ),
        "oulad_o1_bulgu": (
            "En düşük oran {turev.risk.en_dusuk:metin} ({turev.risk.en_dusuk_oran:yuzde}), en "
            "yüksek {turev.risk.en_yuksek:metin} ({turev.risk.en_yuksek_oran:yuzde}). Aynı "
            "modülün dönemleri arasındaki fark ise en fazla birkaç puan."
        ),
        # O2 alt metni (grafik; S3'te çizilir)
        "oulad_o2_alt": (
            "Noktalar çizginin altındaysa ders o dönem geçmişinden daha iyi gitmiştir. Noktaların "
            "çoğu çizginin altında: risk zamanla düştü."
        ),
        # O4 sinyal seçenekleri ve altlarındaki cümleler (grafik; S3'te çizilir)
        "oulad_o4_secenekler": (
            "Teslim edilmeyen ödev",
            "Tıklama (etkinlik)",
            "Ortalama not",
            "Geçmiş nota göre fark",
        ),
        "oulad_o4_cumleler": (
            "Tek bir ödevi teslim etmemek, risk oranını {turev.sinyal.teslim_0:yuzde} "
            "düzeyinden {turev.sinyal.teslim_1:yuzde} düzeyine çıkarıyor.",
            "En az etkin beşte birlik grupta risk {turev.sinyal.tik_ilk:yuzde}, en etkin "
            "grupta {turev.sinyal.tik_son:yuzde}.",
            "Notu boş olanların riski ({turev.sinyal.not_eksik:yuzde}) orta dilimlerden yüksek: "
            "not almamış olmak da bir işaret.",
            "Aynı ödevin geçmiş ortalamasının altında kalanlar daha riskli.",
        ),
        "oulad_o4_nedensellik": "Birlikte görülen örüntüdür, neden değildir.",
        "oulad_o4_bulgu": (
            "Dört sinyalin hepsi riskle düzenli bir ilişki gösteriyor. Ama bu ilişkiler birbirinden "
            "bağımsız değil; hangisinin ne kadar katkı verdiğini ancak model ve SHAP söyleyebilir "
            "(Modelleme sekmesi)."
        ),
        "oulad_o5": {
            "baslik": "Özellik → okul karşılığı",
            "ust": ("Okul karşılığı", "Özellik"),
        },
        # --- 7. Modelleme ---
        "model_bu_bolumde": (
            "Beş özellik setini iki model türüyle, aynı test döneminde bir kez karşılaştırdık. "
            "Dersin geçmişini bilmek tahmini iyileştirmedi, kötüleştirdi; testte en iyi görünen "
            "set ise bağımsız doğrulamada sonuncu oldu. Sonuçlar mütevazı ama tutarlı: işe "
            "yarayan, öğrencinin kendi izi."
        ),
        "model_m0_baslik": "Özellik setleri",
        # Tanımlar notebook 03 hücre 2 metninden (03_oulad_model.ipynb, "Tasarım").
        "model_m0": {
            "satirlar": (
                (
                    "GENERAL",
                    "kesim gününe kadar ödev ve sanal öğrenme etkinliği ile kayıt gününü taşır. "
                    "Etkinlik türüne göre tıklama sütunları da girer. Modül kimliği ve geçmiş "
                    "sunum yoktur.",
                    "",
                ),
                ("GENERAL_MODULE", "aynı sütunlara modül kodunu ekler.", ""),
                (
                    "HISTORY",
                    "genel sütunlara önceki sunumların modül risk oranını, yuva notunu, yuva "
                    "teslim oranını, notun geçmiş yuvaya göre farkını ve geçmişin varlığını ekler.",
                    "",
                ),
                (
                    "HISTORY_SLOT",
                    "genel sütunlara yuva notunu, yuva teslim oranını, notun geçmiş yuvaya göre "
                    "farkını ve geçmişin varlığını ekler. Modül risk oranı bu sette yoktur.",
                    "keşifsel",
                ),
                (
                    "GENERAL_REL",
                    "ham değerlerin yerine, aynı modül sunumu içindeki yüzdelik sırayı kullanır. "
                    "Sıralar not, teslim oranı, tıklama, aktif gün, son etkinliğe yakınlık ve "
                    "gecikme içindir. Kayıt günü yanında durur. Modül kimliği yoktur. Sıra "
                    "hesaplanırken risk etiketi okunmaz.",
                    "keşifsel",
                ),
            ),
            "notlar": (
                "Model türleri `logreg` ve `hgb`.",
                "Ayar, eğitim bölümünün ilk sunumunda eğitilir. Seçim, sonraki sunumun log loss "
                "değerine bakar. Seçilen ayar eğitim bölümünün tamamında yeniden oturtulur. Test "
                "sunumu bir kez, sonda değerlendirilir. Aralıklar modül içinde sınıfa göre "
                "tabakalı bootstrap örneklemlerinden gelir.",
                "`HISTORY_SLOT` ve `GENERAL_REL` ilk test sonuçları görüldükten sonra "
                "eklenmiştir. İkisi keşifseldir. Test dondurulmuştur ve doğrulama dönemi ayrıca "
                "raporlanır.",
            ),
        },
        "model_m3_bulgu": (
            "HISTORY − GENERAL farkı iki model türünde de sıfırın altında ve aralık sıfırı "
            "içermiyor: ders geçmişi tahmini kötüleştiriyor."
        ),
        "model_m5_bulgu": (
            "Sınıf içinde setler arasındaki fark binde birkaç düzeyinde ve dönemden döneme sırası "
            "değişiyor."
        ),
        "model_m7_bulgu": (
            "Model geçmiş risk oranını {turev.model.egitim_satir:tam} satırdan değil, yalnızca "
            "{model.hist_rate_distinct_train:tam} farklı dönem değerinden öğreniyor; üstelik risk "
            "zamanla düştü. Sonuç: geçmiş oran yeni dönemde tahmini yukarı itiyor."
        ),
        # --- 8. Karar kuralı ---
        "kural_r2_bulgu": (
            "Model her modül-dönemde önde, ama fark küçük: noktalar çizginin hemen üstünde. "
            "Şeffaflığın bedeli bir sıçrama değil, düzenli ve küçük bir kayıp."
        ),
        # --- 9. Sisteme köprü ---
        "sistem_kopru": (
            "Sistemde model yok, çünkü okulda \"bu öğrenci sonunda başarısız oldu\" bilgisi "
            "tutulmuyor; model eğitecek etiket yok. Taşınan yalnızca tarif: hangi iki sinyalin, "
            "hangi yönde, sınıf içinde nasıl sıralanacağı ve kaç öğrencinin işaretleneceği. "
            "Okulun demo verisi sentetiktir ve bu rapordaki hiçbir sonuç ondan çıkarılmamıştır."
        ),
        # --- 10. Hoca etkisi ---
        "hoca_bu_bolumde": (
            "Gerçek hayatta öğretmenler fark yaratır; aynı ders, farklı bir öğretmenle farklı "
            "sonuç verebilir. Bu çalışmanın başındaki soru da buydu. Burada bu verilerle hoca "
            "etkisini neden ölçemediğimizi, ölçmek için neyin gerektiğini ve elimizdeki "
            "verilerin bu konuda neyi gösterip neyi gösteremediğini açıkça yazıyoruz."
        ),
        "hoca_basliklar": {
            "h10_1": "Neden ölçemiyoruz?",
            "h10_2": "Elimizdeki verilerle söyleyebileceğimiz",
            "h10_3": "Etik not",
        },
        "hoca_10_1": (
            "Bir öğretmenin etkisini görmek için, aynı dersi aynı öğretmenden alan birçok öğrenci "
            "grubunu yıllar boyunca izlemek ve bunları başka öğretmenlerin gruplarıyla, "
            "öğrencilerin başlangıç düzeyini hesaba katarak karşılaştırmak gerekir. Ancak o "
            "zaman \"bu fark öğretmenden mi, o yılın öğrencilerinden mi, dersin içeriğinden mi, "
            "sınavın zorluğundan mı?\" sorusu ayrılabilir. İki veri setimizde de hangi öğrencinin "
            "hangi öğretmenden ders aldığı yok. OULAD'da ders ve dönem var; ama bir ders-dönem, "
            "öğretmeni, materyali, sınavı ve o dönemin öğrencilerini tek bir pakette taşıyor."
        ),
        # H1 (grafik; S5'te çizilir): katman + durum (TR) ve açıklama
        "hoca_h1_katman": (
            ("Öğrencinin kendi izi", "Gösterildi"),
            ("Ders", "Gösterildi (seviye)"),
            ("Zaman (dönem)", "Gösterildi (kayma)"),
            ("Ders × dönem paketi", "Ölçüldü, ayrıştırılamadı"),
            ("Öğretmen", "Ölçülemedi"),
        ),
        "hoca_h1_aciklama": (
            "Erken sinyaller riskle güçlü ve tutarlı ilişkili; sınıf içi sıralama iki dönemde "
            "tutuyor.",
            "Dersler arasında risk seviyesi farklı. Ama bu fark kimin sıralamasının "
            "değişeceğini belirlemiyor.",
            "Aynı dersin riski dönemden döneme kayıyor; geçmiş, geleceği güvenilir biçimde "
            "taşımıyor.",
            "Öğretmen, materyal, sınav ve öğrenci grubu birlikte; bunları birbirinden ayırmak "
            "mümkün değil.",
            "Veri yok.",
        ),
        "hoca_10_2": (
            "Ders-dönem düzeyindeki toplam farkı ölçebildik; hoca etkisi, eğer varsa, bu paketin "
            "içinde bir yerde. Bu farkın üst sınırını (OULAD keşif ve Modelleme sekmeleri) ve "
            "zamanla ne kadar kaydığını (aynı sekmeler) gösterdik. Bu yüzden sistemi hoca etkisine "
            "**duyarsız** kurduk: her sınıf kendi içinde sıralanıyor, mutlak bir eşik ya da olasılık "
            "yok. Bir öğretmenin sınıfı genel olarak daha yüksek ya da düşük notlar alıyorsa, bu "
            "bayrakların sayısını değiştirmiyor; her öğretmene sınıfının yaklaşık beşte biri kadar "
            "izleme kapasitesi düşüyor. Hoca etkisini ölçemedik, ama sistemin ona dayanmamasını "
            "sağladık."
        ),
        "hoca_h2": {
            "baslik": "Gerçek bir çalışma için gereken veri",
            "ust": (
                "Gereken",
                "UCI",
                "OULAD",
                "Okul sistemi (bugün)",
                "Okul sistemi (yıllar içinde)",
            ),
            "satirlar": (
                (
                    "Öğrenci–öğretmen eşleşmesi",
                    "Yok",
                    "Yok",
                    "Sınıf öğretmeni var; ders öğretmeni yok",
                    "Ders öğretmeni eklenebilir",
                ),
                (
                    "Aynı öğretmen, birden çok yıl",
                    "Yok",
                    "Yok",
                    "Yok (tek yıl)",
                    "Birikir",
                ),
                (
                    "Öğrencinin başlangıç düzeyi",
                    "Kısmen (önceki başarısızlık)",
                    "Kısmen (önceki deneme)",
                    "Yok",
                    "Önceki yıl notları",
                ),
                (
                    "Sonuç etiketi (geçti/kaldı)",
                    "Var",
                    "Var",
                    "Yok",
                    "Birikir",
                ),
                (
                    "Aynı sınav, farklı öğretmen",
                    "Yok",
                    "Yok",
                    "Yok",
                    "Ortak sınavlarla mümkün",
                ),
            ),
        },
        "hoca_10_3": (
            "Öğretmen etkisi ölçülebilir hâle gelse bile, bu bir öğretmen sıralaması aracı "
            "olmamalıdır. Küçük sınıflarda ve az yılda bu tahminler çok gürültülüdür; tek başına "
            "karar dayanağı olamaz. Okul asistanı da \"hangi öğretmen daha başarılı\" sorusuna "
            "not ortalamasıyla cevap vermez."
        ),
        "hoca_bulgu": (
            "**Bu verilerle hoca etkisi hakkında söylenebilecek en dürüst cümle: ölçemiyoruz, "
            "ama ders-dönem düzeyindeki bütün bağlam farkının sistemin bayraklarını bozmadığını "
            "gösterebiliyoruz.**"
        ),
        # --- 11. Hatalar ve düzeltmeler (kartlar 1–8: spec v2, 9–12: spec v2 eki) ---
        "hatalar_bu_bolumde": (
            "Bir analizin güvenilirliği, hatalarını nasıl bulduğuyla ölçülür. Aşağıdaki her kayıt "
            "belirtiyi, kök nedeni, düzeltmeyi ve düzeltmeden sonra neyin değiştiğini gösterir."
        ),
        "hata_basliklar": (
            "Devamsızlık zayıf sanıldı",
            "Testten esinlenen set doğrulamada çöktü",
            "\"Kaynak yalnızca geçmiş oran\" tahmini",
            "\"GENERAL_REL yalnız seviyeyi kaçırıyor\" tahmini",
            "Ders geçmişi hipotezi desteklenmedi",
            "Görülmemiş ders grafiğinin alt metni yanlış",
            "Kuralın ilk sinyalinin okulda karşılığı yok",
            "Analiz mantığı notebook hücresindeydi",
            "Notebook 02 ve 03'te hesaplar hücrelerin içindeydi",
            "Sanal ortam kopyalanmıştı; notebook başka ortamda çalışıyordu",
            "Ön kayıt kontrolü ilk kayda bakıyordu",
            "Ana şüphe çürüdü",
        ),
        "hata_tur": (
            "Veri",
            "Yöntem",
            "Yorum",
            "Yorum",
            "Yöntem (hata değil, çürüyen hipotez)",
            "Yorum",
            "Yöntem",
            "Yeniden üretilebilirlik",
            "Yeniden üretilebilirlik",
            "Yeniden üretilebilirlik",
            "Yöntem (koşu durdu, dosyalar değişmedi)",
            "Yorum (hata değil, çürüyen hipotez)",
        ),
        # Bağlantılı görselin yanındaki açıklama (kart numarası → metin)
        "hata_bag_not": {
            "1": "dahil/hariç seçici bu kaydın \"önce/sonra\" görünümüdür",
            "3": "HISTORY_SLOT satırı",
        },
        # Belirtimde metni verilen alanlar (kart numarası → alan → metin). Verilmeyenler boş kalır.
        "hata_govde": {
            "1": {
                "belirti": "İlk analizde devamsızlık ile final notu arasındaki ilişki zayıf göründü.",
                "kok": (
                    "Final notu 0 olan {uci.g3_zero:tam} kaydın hepsinde devamsızlık da 0'dı. Bunlar "
                    "büyük olasılıkla sınava girmeyen ya da ayrılan öğrencilerdi ve ilişkiyi "
                    "bastırıyordu."
                ),
                "duzeltme": (
                    "G3=0 kayıtları ayrı incelendi; devamsızlık analizi dahil ve hariç iki görünümle "
                    "yapıldı."
                ),
                "sonra": (
                    "Hariç tutulunca devamsızlık arttıkça geçme oranının düzenli düştüğü görüldü. "
                    "Yine de devamsızlık tek başına karar verdirmez."
                ),
            },
            "2": {
                "belirti": (
                    "GENERAL_REL testte en iyi set göründü "
                    "({sets.roc_test.GENERAL_REL.hgb.estimate:roc})."
                ),
                "kok": (
                    "Set, test sonuçlarına bakılarak tasarlanmıştı; test dönemine uyum, gerçek bir "
                    "iyileşme gibi görünebilirdi."
                ),
                "duzeltme": (
                    "Set bağımsız doğrulama döneminde ölçüldü ve en düşük sonucu verdi "
                    "({sets.roc_val.GENERAL_REL.hgb:roc})."
                ),
                "sonra": (
                    "Set benimsenmedi. Test dönemi donduruldu; sonradan eklenen setler \"keşifsel\" "
                    "olarak işaretlendi."
                ),
            },
            "3": {
                "belirti": (
                    "Ders geçmişini eklemek sonucu kötüleştirdi ve nedeni olarak yalnızca dersin "
                    "geçmiş risk oranı tahmin edildi."
                ),
                "kok": "Açıklama sınanmadan kabul edilmek üzereydi.",
                "duzeltme": (
                    "Geçmiş risk oranı çıkarılarak HISTORY_SLOT seti kuruldu ve aynı protokolle "
                    "ölçüldü."
                ),
                "sonra": (
                    "Sonuç aynı kaldı: geçmiş ödev özellikleri de genelleşmiyor. Tahmin yanlıştı ve "
                    "sonuç olarak yazılmadı."
                ),
            },
            "4": {
                "belirti": (
                    "GENERAL_REL doğrulamada düşünce, düşüşün yalnızca seviyeden geldiği, "
                    "sıralamanın ise sağlam olduğu düşünüldü."
                ),
                "kok": "Sıralamanın sağlam olduğu varsayılmıştı, ölçülmemişti.",
                "duzeltme": "Doğrulama döneminde sınıf içi sıralama başarısı ölçüldü.",
                "sonra": "Sıralama da en düşüktü. Tahmin yanlıştı; set benimsenmedi.",
            },
            "5": {
                "belirti": "Dersin geçmişini bilmenin tahmini iyileştirmesi bekleniyordu.",
                "kok": (
                    "Dersin risk oranı dönemden döneme kayıyor ve model geçmiş oranı az sayıda "
                    "farklı dönem değerinden öğreniyor."
                ),
                "duzeltme": (
                    "Hipotez eşli farklarla ve ayrıca doğrulama döneminde sınandı; sonuç olduğu gibi "
                    "yazıldı."
                ),
                "sonra": (
                    "Hipotezin yarısı tuttu (ders seviyesi), yarısı tutmadı (ders geçmişinin "
                    "sıralamaya katkısı). İkisi de rapora yazıldı."
                ),
            },
            "6": {
                "belirti": (
                    "görülmemiş ders grafiğinin alt metni, vurgulu satırı \"eğitimde yer almayan "
                    "ders\" olarak tanımlıyordu."
                ),
                "kok": (
                    "bu analizde her satır eğitimde görülmeyen bir ders. GGG'nin vurgulanma nedeni "
                    "farklı: 60. güne kadar notlu ödevi yok."
                ),
                "duzeltme": "başlık, alt metin (TR/EN) ve GGG satırına açıklama notu güncellendi.",
                "sonra": "doğrulandı (figures.json ve yeniden üretilen grafik kontrol edildi).",
            },
            "7": {
                "belirti": "İlk kural üç sinyalliydi; sinyallerden biri teslim edilmeyen ödevdi.",
                "kok": "Okul sisteminde ödev teslim kaydı yok; bu sinyal okulda uygulanamazdı.",
                "duzeltme": (
                    "Kural iki sinyalli sürüme (not ortalaması ve aktif gün) indirildi ve aynı "
                    "ölçütle, önceden yazılmış kurallarla yeniden sınandı."
                ),
                "sonra": (
                    "İki sinyalli kural kabul edildi. Teslim kaydı, okul için en değerli eksik "
                    "sinyal olarak gelecek çalışmalara yazıldı."
                ),
            },
            "8": {
                "belirti": (
                    "Rapor 'mantık paketten çağrılır' diyordu, ama devamsızlık analizi notebook "
                    "hücresinde tanımlıydı."
                ),
                "kok": "Hesap notebook'ta yazılmış, sonra pakete taşınmamıştı.",
                "duzeltme": (
                    "Fonksiyonlar `data_science.absence` modülüne taşındı; notebook oradan "
                    "çağırıyor; Hafta 8 değerleri testle doğrulandı."
                ),
                "sonra": (
                    "Notebook ile paket aynı değerleri veriyor; rapordaki sayılar tek kaynaktan "
                    "geliyor."
                ),
            },
            "9": {
                "belirti": (
                    "Notebook 02 ve 03'te bazı tablo ve hesaplar hücrelerin içinde tanımlıydı; "
                    "paketleyici bunları kopyalamadan kullanamıyordu."
                ),
                "kok": "Aynı kalıp ilk notebook'ta düzeltilmiş, diğerlerinde aranmamıştı.",
                "duzeltme": (
                    "Hesaplar `data_science` paketine (`oulad/eda.py`, `oulad/model_tables.py`) "
                    "taşındı; notebook'lar oradan çağırıyor."
                ),
                "sonra": (
                    "Notebook'lar yeniden çalıştırıldı; her kod hücresinin çıktısı önceki çıktıyla "
                    "birebir aynı."
                ),
            },
            "10": {
                "belirti": (
                    "Sanal ortam başka bir haftanın klasöründen kopyalanmıştı; komut dosyaları ve "
                    "Jupyter çekirdeği eski ortamın Python'unu gösteriyordu."
                ),
                "kok": (
                    "Kopyalanan ortamın içindeki yollar güncellenmemişti; notebook'lar farklı bir "
                    "ortamda çalışıyordu."
                ),
                "duzeltme": (
                    "Komutlar ortamın kendi Python'u üzerinden çalıştırıldı ve ortama ait çekirdek "
                    "kaydedildi."
                ),
                "sonra": (
                    "Notebook 03 doğru ortamda yeniden çalıştırıldı ve çıktılar aynı kaldı. "
                    "`explain.json`'un TreeExplainer ile üretildiği doğrulandı."
                ),
            },
            "11": {
                "belirti": "Ek analiz koşusu ön kayıt kontrolünde durdu.",
                "kok": (
                    "Ek dosya koşudan önce bir kez güncellenmiş ve iki md5 kaydı oluşmuştu; kontrol "
                    "son kayıt yerine ilk kayda bakıyordu."
                ),
                "duzeltme": (
                    "Kontrol son kaydı okuyacak biçimde düzeltildi; ön kayıt dosyaları "
                    "değiştirilmedi."
                ),
                "sonra": (
                    "Koşu dosyaların son mühürlü hâliyle başladı; iki kayıt da mühür tablosunda "
                    "duruyor."
                ),
            },
            "12": {
                "belirti": (
                    "Çalışma tek hat üzerinde ilerlemişti; modelin yalnızca dersi bırakan öğrenciyi "
                    "bulduğundan şüphelenildi."
                ),
                "kok": "Hedef \"başarısız ya da bırakmış\" birleşikti; iki grup ayrı ölçülmemişti.",
                "duzeltme": (
                    "Şüphe sayısal beklentiler olarak önceden yazılıp mühürlendi; iki hedef ayrı "
                    "ayrı tahmin edildi."
                ),
                "sonra": "B4, B5 ve B7 tutmadı. Çalışmanın en önemli bulgularından biri bu oldu.",
            },
        },
        # --- 12. Sınırlar ve kaynaklar ---
        "kaynak_kaynakca": (
            "Cortez ve Silva (2008)",
            "Kuzilek, Hlosta ve Zdrahal (2017)",
            "scikit-learn",
            "SHAP",
        ),
        "kaynak_yazar": "Ensar Bera Ergin · Türksat A.Ş. yaz stajı · 2026",
        # --- Sayfa sonu (bölüm 1) ---
        "sayfa_sonu": "Bu raporu kaynak koduyla birlikte yeniden üretmek için",
        # --- Ek analizler (spec v2 eki, bölüm 2) ---
        "ek_bu_bolumde": (
            "Buraya kadar çalışma tek bir hat üzerinde ilerledi: tek bir kesim günü, tek bir "
            "hedef, tek bir özellik paketi. Bu sekmede kendi sonucumuzu sorguladık: model "
            "gerçekten zorlanan öğrenciyi mi buluyor, yoksa yalnızca dersi çoktan bırakmış olanı "
            "mı? Beklentilerimizi koşmadan önce yazdık ve mühürledik; sonra sınadık."
        ),
        "ek_basliklar": {
            "harita": "Düşünce haritası",
            "onkayit": "Ön kayıt",
            "e2": "Şüphe çürüyor (E2)",
            "e1": "Bilgi nerede? (E1)",
            "e3": "Ne kadar erken? (E3)",
            "e4": "Başkaları ne buldu? (E4)",
            "kapanis": "Kapanış: ne değişti, ne değişmedi",
        },
        # 2.1: dört kutu, kutu başına "Ne bulduk" ve "Neyi eksik bıraktı"
        # (docs/ek_analizler_on_kayit.md bölüm 1 tablosu; ilk dört satır).
        "ek_harita": {
            "bulduk": "Ne bulduk",
            "eksik": "Neyi eksik bıraktı",
            "duraklar": (
                (
                    "H8 · UCI",
                    "Dönem notları finali neredeyse belirliyor; devamsızlık (G3=0 "
                    "düzeltmesinden sonra) riskle ilişkili.",
                    "Bağlam yok, zaman yok. Erken uyarı kurulamıyor.",
                ),
                (
                    "H9 · OULAD keşif",
                    "Risk seviyesi derse ve döneme göre değişiyor; öğrencinin erken izi riskle "
                    "güçlü ilişkili.",
                    "Hepsi betimsel.",
                ),
                (
                    "H10 · Model",
                    "Ders geçmişi tahmini iyileştirmedi; işe yarayan öğrencinin kendi izi ve "
                    "sınıf içi sıralama.",
                    "**Çalışma doğrusal ilerledi:** tek kesim günü (60), tek hedef (başarısız ∪ "
                    "bırakmış), tek özellik paketi (\"öğrencinin izi\" tek blok olarak).",
                ),
                (
                    "H11 · Kural",
                    "İki sinyalli kural (not + etkinlik), modelin isabetlerinin büyük kısmını "
                    "yakalıyor.",
                    "\"Öğrencinin izi\" tam olarak neyi yakalıyor? Notu düşen öğrenciyi mi, "
                    "yoksa dersi çoktan bırakmış öğrenciyi mi?",
                ),
            ),
        },
        "ek_suphe": (
            "**Şüphe:** Hedef \"başarısız ya da bırakmış\". Bırakan öğrenci sisteme girmeyi ve "
            "ödev teslim etmeyi de bırakır; model belki yalnızca bunu görüyor."
        ),
        # E1–E4 soru kartları (docs/ek_analizler_on_kayit.md bölüm 1, "Cevapladığı soru")
        "ek_sorular": (
            (
                "E1 · Sinyal ayrıştırma",
                "Hangi sinyal grubu tek başına ne kadar bilgi taşıyor? Yalnız notlarla ne kadar "
                "ileri gidilebilir?",
            ),
            (
                "E2 · Hedef ayrıştırma",
                "Model, \"başarısız\" ile \"bıraktı\"yı aynı kolaylıkla mı buluyor? Kural kimi "
                "işaretliyor?",
            ),
            (
                "E3 · Ne kadar erken?",
                "Erken uyarının bedeli: kesim günü öne çekildikçe başarı nasıl değişiyor?",
            ),
            (
                "E4 · Literatürle kıyas",
                "Bizim sayılarımız neden yayınlardakinden düşük ve bu ne anlama geliyor?",
            ),
        ),
        "ek_onkayit": (
            "Analizleri koşmadan önce {ek.summary.total:tam} beklentiyi sayısal ölçütleriyle yazdık "
            "ve dosyaların md5 değerini kaydettik. Analiz kodu, bu dosyalar kayıttan sonra "
            "değiştiyse çalışmayı reddediyor. Bir beklenti ancak iki dönemde de (doğrulama ve test) "
            "tutarsa \"tuttu\", ikisinde de tutmazsa \"tutmadı\" sayıldı; dönemler ayrışırsa "
            "\"belirsiz\"."
        ),
        "ek_muhur": {
            "baslik": "Mühür tablosu",
            "ust": ("Dosya", "md5", "Zaman"),
            "not": "Ek dosya koşudan önce bir kez güncellendi; iki kayıt da duruyor.",
        },
        # P1 açılış sonrası özet satırı (grafik; S5'te çizilir)
        "ek_onkayit_ozet": (
            "{ek.summary.tuttu:tam} tuttu, {ek.summary.tutmadı:tam} tutmadı, "
            "{ek.summary.belirsiz:tam} belirsiz."
        ),
        "ek_e2_metin": (
            "İlk soru: kim daha kolay bulunuyor? \"Başarısız\" ile \"bıraktı\"yı ayrı ayrı "
            "tahmin ettik. Beklentimiz bırakanların daha kolay bulunacağıydı (B4). Tersi çıktı: "
            "iki dönemde de başarısız olacak öğrenciyi bulmak daha kolay."
        ),
        # X2 alt metni (grafik; S5'te çizilir)
        "ek_x2_alt": (
            "Kural, bırakanların da yaklaşık üçte birini yakalıyor; ama başarısız olacakları "
            "biraz daha yüksek oranda buluyor. Bu bir 'kopmuş öğrenci dedektörü' değil."
        ),
        "ek_e2_bulgu": (
            "**Model ve kural işi kolay olanı yapmıyor.** Dersi sürdürüp başarısız olacak "
            "öğrenciyi, bırakacak öğrenciden daha kolay ve biraz daha yüksek oranda buluyorlar."
        ),
        "ek_e1_metin": (
            "Öğrencinin izini dört gruba ayırdık: notlar, ödev teslim davranışı, çevrim içi "
            "etkinlik ve kayıt tarihi. Hiçbir grup tek başına tam modele ulaşmıyor (B1). Not ve "
            "teslim birlikte ise tam modele çok yaklaşıyor (B3). Hangi tek grubun en güçlü "
            "olduğu ise dönemden döneme değişiyor (B2 belirsiz): tek bir sinyale güvenmek, "
            "Modelleme sekmesindeki \"testte birinci, doğrulamada sonuncu\" dersinin küçük bir "
            "tekrarı olurdu."
        ),
        "ek_e1_bulgu": (
            "**Okul için:** Risk işaretinin asıl taşıyıcısı devamsızlık değil, not ve ödev "
            "kaydı. Okulda bugün teslim kaydı yok; bu çalışma onun en değerli eksik sinyal "
            "olduğunu gösteriyor."
        ),
        "ek_e3_metin": (
            "Erken uyarının bir bedeli var: ne kadar erken uyarırsak, o kadar az bilgiyle uyarırız. "
            "Aynı hattı 14, 30, 60, 90 ve 120. günler için koştuk. Başarı her adımda arttı (B8), "
            "kazancın çoğu 60. güne kadar geldi (B9) ve 14. günde başarıyı neredeyse tek başına "
            "etkinlik taşıdı (B10)."
        ),
        "ek_e3_karar": (
            "Koşmadan önce fark ettik: 14. günde test döneminde hiçbir derste notlu ödev yok. "
            "'Notlu ödevi olmayan sınıfta bayrak yok' kuralı okul sisteminin kuralıdır, modelin "
            "değerlendirme kuralı değil; bu yüzden E3'te uygulanmadı. Karar, sonuçlar "
            "görülmeden ek bir ön kayıt dosyasına yazıldı."
        ),
        # X5 kalıcı notu (grafik; S5'te çizilir)
        "ek_x5_not": "Sabit kohortta 'bırakan' = 120. günden sonra bırakan.",
        "ek_e3_bulgu": (
            "**60. gün geriye dönük olarak gerekçelendi.** Kazancın çoğu 14 ile 60. gün "
            "arasında geliyor; 60. gün, kazancın çoğunun alındığı ve hâlâ müdahale için zaman "
            "olan nokta."
        ),
        # DIŞ KAYNAK SAYISI (spec eki 2.6, tek istisna): "%90'ın üzerinde" yayınlardan gelir, paketten değil.
        "ek_e4_metin": (
            "Yayınlarda OULAD için %90'ın üzerinde değerler görülüyor (farklı metriklerle); bizim "
            "test değerimiz ROC AUC {sets.roc_test.GENERAL.hgb.estimate:roc}. Bu sayılar doğrudan "
            "karşılaştırılamaz: tahmin anı, bölme yöntemi, hedef ve demografik özellik kullanımı "
            "çalışmadan çalışmaya değişiyor. İncelediğimiz iki yüksek değerli çalışma demografik "
            "özellik kullanıyor ve en yüksek değerler dersin sonuna ait; bölme türlerini "
            "doğrulayamadık. En yakın tasarımdaki bağımsız bir çalışma (Wu, Jia ve Pham, 2026) hem "
            "sayılarımızla aynı aralıkta hem de \"bırakmak daha zor\" bulgusunu kendi verisinde "
            "tekrarlıyor."
        ),
        # L1: dış kaynak sayıları; paket dışı (spec v2 eki, bölüm 2.6). "Metinde elle rakam yok"
        # kuralının tek istisnasıdır: tablo, gözlemler ve kaynakça docs/ek_analizler_sonuc.md
        # bölüm 7'den birebir alınmış metin sabitidir; yer tutucu kullanılmaz. "Doğrulanmadı"
        # hücreleri sayfada gri çizilir.
        # DIŞ KAYNAK SAYILARI (spec eki 2.6, tek istisna): Wu/Adnan/Scientific Reports satırları,
        # gözlemler ve kaynakça literatürden birebir alındı; paket değeri değildir. Bu çalışmanın
        # kendi değerleri yer tutucudur.
        "ek_l1": {
            "baslik": "Tablo L1",
            "ust": (
                "Çalışma",
                "Tahmin anı",
                "Bölme",
                "Hedef",
                "Demografik özellik",
                "Bildirilen değer",
            ),
            "satirlar": (
                (
                    "Bu çalışma",
                    "60. gün (E3: 14–120)",
                    "Zamansal: 2013J ile eğitim, 2014B doğrulama, 2014J test",
                    "Başarısız ∪ bırakmış; kesimden önce kaydını silenler dışarıda",
                    "Yok",
                    (
                        "ROC AUC test {sets.roc_test.GENERAL.hgb.estimate:roc} (60. gün, GGG dahil); "
                        "sabit kohortta 30. gün {turev.ek.e3_30_test:roc}"
                    ),
                ),
                (
                    "Wu, Jia ve Pham (2026), Frontiers in Education 11",
                    "28. gün",
                    "Öğrenciye göre gruplanmış rastgele 80/20 ve ayrıca zamansal (2013 → 2014)",
                    "Başarısız ∪ sonradan bırakmış; 28. günden önce kaydını silenler dışarıda",
                    "Var (9 arka plan/idari özellik) ve yok, ikisi de raporlanmış",
                    (
                        "ROC AUC: tüm özellikler 0,775, yalnız davranış 0,750 (gruplanmış bölme); "
                        "zamansal: 0,747 (tüm, RF), 0,709 (yalnız davranış, HistGB)"
                    ),
                ),
                (
                    "Adnan vd. (2021), IEEE Access 9",
                    "Dersin %0, 20, 40, 60, 80, 100'ü",
                    "Doğrulanmadı",
                    (
                        "Withdrawn / Fail / Pass / Distinction (çok sınıflı ve birleştirilmiş "
                        "varyantlar)"
                    ),
                    "Var",
                    (
                        "RF ortalama kesinlik: %20'de 0,79, %100'de 0,92 (doğruluk %20'de 0,79, "
                        "%100'de 0,91)"
                    ),
                ),
                (
                    (
                        "Scientific Reports (2025), \"Accurate multi-category student performance "
                        "forecasting at early stages of online education using neural networks\""
                    ),
                    "Dersin yaklaşık %20'si",
                    "Doğrulanmadı",
                    "Distinction / Fail / Pass / Withdrawn",
                    "Var (demografik, ödev, tıklama)",
                    "Doğruluk %92 (yaklaşık %20'de)",
                ),
            ),
            "gri": "Doğrulanmadı",
            "gozlemler": (
                (
                    "**Gözlem 1: Zaman noktası sayıyı belirliyor.** Adnan vd.'de başarı dersin "
                    "%0'ından %100'üne doğru düzenli artıyor; bu, bizim E3 eğrimizle (B8, B9) aynı "
                    "biçim. Dersin tamamına ya da geç bir pencereye ait bir değer, 60. gündeki bir "
                    "değerle karşılaştırılamaz."
                ),
                (
                    "**Gözlem 2: En yakın kurgu bağımsız olarak benzer sayılar veriyor.** Wu vd. "
                    "(2026) bizimkine en yakın tasarım: erken bir sabit gün, kesimden önce "
                    "bırakanların dışlanması, zamansal doğrulama ve demografik özelliksiz bir model. "
                    "Zamansal aktarımdaki yalnız davranış modeli (0,709, 28. gün) ile bizim 30. gün "
                    "sabit kohort değerimiz ({turev.ek.e3_30_test:roc}) çok yakın. Kurgular birebir "
                    "aynı değil: test kümesi, kohort tanımı ve özellikler farklı. Bu bir doğrulama "
                    "değil, sayılarımızın bu protokol ailesi için makul aralıkta olduğunun işareti."
                ),
                (
                    "**Gözlem 3: \"Bırakmak daha zor\" bulgusu bağımsız olarak tekrarlanıyor.** Wu "
                    "vd.'de 28. günde hâlâ kayıtlı öğrenciler arasında sonradan bırakmayı tahmin "
                    "etmek (0,697), başarısızlığı tahmin etmekten (0,720) daha zor; bırakmayan "
                    "öğrenciler içinde başarısızlığı geçmeden ayırmak ise en kolay görev (0,783). "
                    "Bu, bizim B4'te ön kayda aykırı çıkan sonucumuzla aynı yönde. Aynı çalışmada "
                    "bırakma tahmininin ödev teslim bilgisine, başarısızlık tahmininin etkinliğe "
                    "daha çok dayandığı raporlanıyor; bu da \"bırakmanın erken izi teslimde\" "
                    "hipotezimizle uyumlu. İki çalışma da nedensellik iddia etmiyor."
                ),
                (
                    "**Gözlem 4: Notlu ödevi olmayan dersler.** Wu vd.'de başka derslere en kötü "
                    "aktarılan iki ders, tahmin penceresinde notlu ödevi olmayan GGG ve EEE. Bizim "
                    "60. günde GGG'yi notlu ödevsiz olduğu için bayrak kuralından dışlamamız ve "
                    "E3'te 14. günde test döneminde hiç notlu ödev bulunmaması aynı yapısal soruna "
                    "işaret ediyor."
                ),
                (
                    "**Gözlem 5 (hipotez): Bırakmanın neden bazı çalışmalarda \"kolay\" göründüğü.** "
                    "*Scientific Reports* (2025) çalışması Withdrawn sınıfının erken aşamalarda "
                    "yüksek isabetle bulunduğunu raporluyor. Bizim ve Wu vd.'nin tasarımında, tahmin "
                    "anından önce kaydını silen öğrenciler çıkarılıyor; çünkü onların sonucu o an "
                    "zaten belli. Bu öğrenciler örneklemde kalırsa \"bırakan\" sınıfının bir kısmı "
                    "tanım gereği kolaylaşır. Çalışmanın örneklem kuralını doğrulamadığımız için bu "
                    "bir açıklama önerisidir, tespit değildir."
                ),
            ),
            "kaynakca": (
                (
                    "Wu, M., Jia, J. ve Pham, T. T. (2026). Early warning of academic risk from the "
                    "first four weeks of online learning activity and assessment performance: a "
                    "leakage-controlled, demographic-data-minimizing study on the OULAD benchmark. "
                    "*Frontiers in Education*, 11. doi:10.3389/feduc.2026.1917092"
                ),
                (
                    "Adnan, M. vd. (2021). Predicting at-risk students at different percentages of "
                    "course length for early intervention using machine learning models. *IEEE "
                    "Access*, 9, 7519–7539. doi:10.1109/ACCESS.2021.3049446"
                ),
                (
                    "Accurate multi-category student performance forecasting at early stages of "
                    "online education using neural networks (2025). *Scientific Reports*. "
                    "https://www.nature.com/articles/s41598-025-00256-3"
                ),
            ),
        },
        "ek_kapanis": {
            "degisti": (
                "**Değişti:** Şüphemiz çürüdü; sistemin neyi yakaladığını artık biliyoruz. 60. "
                "gün seçimi gerekçelendi. Okul için en değerli eksik sinyal belirlendi: ödev "
                "teslim kaydı."
            ),
            "degismedi": (
                "**Değişmedi:** Sistemdeki kural. Ek analizler bir şeyi düzeltmek için değil, "
                "anlamak için yapıldı; bir değişiklik önerisi çıkarsa yeni ve önceden yazılmış "
                "ölçütlerle ayrıca sınanır."
            ),
        },
        # --- Ham tablolar başlıkları (spec v2, bölüm 5, 6 ve 7'deki listeler) ---
        "ham_uci": {
            "korelasyon": "Korelasyonlar",
            "devamsizlik": "Devamsızlık dilimleri (dahil/hariç)",
            "g3_sifir": "G3=0 sayıları",
        },
        "ham_oulad": {
            "tablolar": "Tablo boyutları",
            "final": "Final sonuçları",
            "risk": "Risk pivotu",
            "gecmis": "Geçmiş-şimdi",
            "yuva": "Yuva ortalamaları",
            "sinyaller": "Dört sinyal tablosu",
            "ggg": "GGG özeti",
        },
        "ham_model": {
            "test": "Test metrikleri",
            "esli": "Eşli farklar",
            "dogrulama": "Doğrulama",
            "modul_roc": "Modül ROC",
            "taban": "Taban oran",
            "lomo": "LOMO",
            "shap": "SHAP",
        },
        # Metin yaması (H11): "Bu bölümde" kutuları (yeni_metinler).
        "ozet_bu_bolumde": (
            "Bu sayfa, okul sistemindeki risk bayrağının arkasındaki araştırmayı anlatır. Soru "
            "şuydu: bir öğrencinin zorlandığını erken ve gerekçesiyle söyleyebilir miyiz? Kısa "
            "cevap: öğrencinin kendi izinden evet, mütevazı bir başarıyla; hocanın etkisini ise bu "
            "verilerle ölçemiyoruz."
        ),
        "kural_bu_bolumde": (
            "Okulda model eğitecek sonuç bilgisi olmadığı için modelin yerine şeffaf bir kural "
            "koyduk ve kuralın modelin ne kadar gerisinde kaldığını ölçtük. Cevap: geride kalıyor "
            "ama az; bedeli küçük ve düzenli. Bayrak oranını değiştirerek kesinlik ile yakalama "
            "arasındaki dengeyi kendin görebilirsin."
        ),
        "sistem_bu_bolumde": (
            "Araştırmadan okul sistemine ne taşındığını gösterir. Taşınan bir model ya da veri "
            "değil, yalnızca sınanmış bir kuralın tarifi: hangi iki sinyal, hangi yönde ve sınıf "
            "içinde kaç öğrenci."
        ),
        "kaynak_bu_bolumde": (
            "Çalışmanın neyi söyleyemeyeceğini, sonuçların nasıl yeniden üretileceğini ve kullanılan "
            "kaynakları bir arada verir."
        ),
    },
    "en": {
        # 4.0
        "hero_baslik": "The research behind the attention flag",
        "hero_alt": (
            "The school system's risk tab does not come from a prediction model but from a "
            "transparent rule tested on open data. This page shows how we arrived at that rule, "
            "what worked, what did not, and what we still do not know."
        ),
        "ozet1_deger": "{rule.capture_rule2.2014J:yuzde}",
        "ozet1_aciklama": (
            "On the test term, the transparent rule catches this share of the model's hits."
        ),
        "ozet2_deger": "{rule.gap_rule2.2014J:puan} points",
        "ozet2_aciklama": (
            "The price of transparency: the gap in precision behind the model (within-class "
            "{rule.flag_rate:yuzdetam})."
        ),
        "ozet3_deger": "Unknown",
        "ozet3_aciklama": (
            "Teacher effect: neither dataset records the teacher, so it could not be tested."
        ),
        "uyari": (
            "The students and grades in the school demo are synthetic. Every finding on this "
            "page comes from two open datasets; no findings are drawn from the school data."
        ),
        # 4.1
        "soru": (
            "Can we tell that a student is struggling early enough, and with a reason? And does "
            "risk depend only on the student, or also on the course, the teacher, and that "
            "year's conditions? In real life, a student who is safe in one course with certain "
            "grades may be at risk with the same grades in another course whose final was "
            "harder. If so, an approach that looks only at the student will be wrong."
        ),
        # 4.2
        "veri1_baslik": "UCI Student Performance",
        "veri1": (
            "Two Portuguese high schools, two subjects (Mathematics, Portuguese), one school "
            "year. {uci.total:tam} records; grades 0–20 (G1, G2 in term, G3 final). "
            "Source: Cortez & Silva (2008), CC BY 4.0."
        ),
        "veri2_baslik": "OULAD",
        "veri2": (
            "Open University (UK), distance learning. {oulad.n_courses:tam} "
            "course-presentations, {oulad.n_rows_raw:tam} student-course records, "
            "{oulad.n_vle_rows:tam} online activity rows; 2013–2014. "
            "Source: Kuzilek, Hlosta & Zdrahal (2017), CC BY 4.0."
        ),
        "veri_alt": (
            "Neither is a Turkish high school. So no data or model was carried into the system; "
            "only the recipe of a tested rule was."
        ),
        # 4.3
        "uci_bulgu": (
            "Early grades strongly reflect the final (r = {uci.corr_g1:kor} between G1 and G3). "
            "The strongest non-grade signal is past failure (r = {uci.corr_failures:kor}). "
            "Absence looked weak in the first analysis; that was a mistake."
        ),
        "u1_dahil": "Including G3=0",
        "u1_haric": "Excluding G3=0",
        "uci_hata": (
            "**Error record.** {uci.g3_zero:tam} students had a final grade of 0 and all showed "
            "zero absences: most likely students who did not sit the exam or left. These "
            "records suppressed the relationship. Once excluded, the pass rate falls steadily "
            "as absences rise. Still, half of those in the highest band pass: absence alone "
            "does not decide."
        ),
        "uci_kapanis": (
            "UCI has no course context, teacher, or exam dates, so a real early warning cannot "
            "be built. For the context question we moved to a larger, time-ordered dataset."
        ),
        # 4.4
        "oulad_duzen": (
            "For each student-course we used only information up to **day 60** of the course: "
            "assignments submitted by then and online activity. The target is failing or "
            "withdrawing. Models were trained on past terms and tested once on a future term; "
            "every boundary was guarded by tests so that no future information leaked."
        ),
        # 4.5
        "b45_giris": (
            "The experiment compared five feature sets with two model types: the student's own "
            "trace only (GENERAL), plus the course identity (GENERAL_MODULE), plus the course's "
            "past terms (HISTORY), and two control sets. The answer has four parts."
        ),
        "kart_ders": (
            "**Course: yes.** On the test term, a course's risk rate ranges from "
            "{test.module_rate_min:yuzde} ({test.module_rate_min_module:metin}) to "
            "{test.module_rate_max:yuzde} ({test.module_rate_max_module:metin}). Knowing the "
            "course identity corrects the level of the prediction."
        ),
        "kart_zaman": (
            "**Time: it drifts.** A course's past risk rate pulled predictions the wrong way in "
            "the new term; adding the course history made results worse (ROC AUC difference "
            "{sets.paired.HISTORY_GENERAL.hgb.estimate:roc} "
            "[{sets.paired.HISTORY_GENERAL.hgb.low:roc}; "
            "{sets.paired.HISTORY_GENERAL.hgb.high:roc}]). "
            "That is why the system shows no absolute probability."
        ),
        "kart_sira": (
            "**Ranking within a class: context did not help.** For \"who is more at risk in "
            "this class?\", no context recipe helped consistently across two terms. What works "
            "is judging each student within their own class."
        ),
        "kart_hoca": (
            "**Teacher: unknown.** Neither dataset records the teacher, so this could not be "
            "tested. It can be tested as outcome data accumulates in the school system."
        ),
        # 4.6
        "b46_metin": (
            "The set that looked best on test (GENERAL_REL, test ROC AUC "
            "{sets.roc_test.GENERAL_REL.hgb.estimate:roc}) had been designed after looking at "
            "test results. It scored lowest on the independent validation term "
            "({sets.roc_val.GENERAL_REL.hgb:roc}). We did not adopt it. Design guided by test "
            "results can pick a lucky winner; from then on we froze the test term and marked "
            "later sets as \"exploratory\"."
        ),
        "tablo_46_baslik": "Explanations that did not hold",
        "tablo_46": {
            "ust": ("Guess", "Check", "Result"),
            "satirlar": (
                (
                    "The drop came only from the past risk-rate column",
                    "That column was removed: the result stayed the same",
                    "Wrong: past assignment features do not generalize either",
                ),
                (
                    "GENERAL_REL only misses the level; its ranking is sound",
                    "Ranking was measured on the validation term: lowest",
                    "Wrong: the set was not adopted",
                ),
            ),
        },
        "b46_kapanis": "No explanation that failed its check was reported as a finding.",
        # 4.7
        "b47": (
            "Each course was held out of training in turn and tested on its own. The course "
            "identity does not transfer to a new course; ranking performance is almost the same "
            "across sets (mean ROC AUC {lomo.mean.GENERAL.roc_auc:roc} – "
            "{lomo.mean.GENERAL_REL.roc_auc:roc}). The real warning is GGG: it has no graded "
            "assignment before day 60, so the model reads \"no assignment yet\" as \"did not "
            "submit\" and predicts very high risk. In the system: no flag is shown in a class "
            "with no grades."
        ),
        # 4.8
        "b48": (
            "The three signals the model relies on most: number of unsubmitted assignments, "
            "grade average, and time since last activity. This describes the model's behaviour; "
            "it does not mean that not submitting causes failure."
        ),
        # 4.9
        "b49_giris": (
            "A teacher can only follow so many students. Move the flag rate to see the "
            "trade-off between precision (how many flagged students really struggled) and "
            "recall (how many struggling students were flagged). Ranking everyone together is "
            "compared with ranking inside each class."
        ),
        "b49_secim": (
            "We chose a within-class flag rate of {rule.flag_rate:yuzdetam}: within-class ranking stays "
            "ahead of school-wide ranking across a wide range of flag rates (visible on the slider), "
            "gives every teacher equal follow-up capacity, and is not affected by drift in a "
            "course's base rate. The price: in classes where risk is low, precision is low too."
        ),
        # 4.10
        "b410": (
            "The school keeps no history of \"did this student eventually fail\", so training a "
            "model in the system was never an option. So we asked the reverse: how far behind "
            "the model does a transparent rule fall, one that is not trained, never looks at "
            "outcomes, and was fixed before seeing results? A three-signal rule was tested "
            "first; since the school data has no equivalent of \"missed assignment\", we moved "
            "to a two-signal version (grade average and active days), tested against criteria "
            "written in advance."
        ),
        "r1_not": "GGG is excluded in both terms: it has no graded assignment before day 60.",
        # 4.11
        "tablo_11": {
            "ust": ("OULAD signal", "School counterpart", "Direction"),
            "satirlar": (
                (
                    "Grade average (up to day 60)",
                    "In-term grade average",
                    "Lower is riskier",
                ),
                (
                    "Active days",
                    "Unexcused absences",
                    "Fewer active days or more absences is riskier",
                ),
                (
                    "Unsubmitted assignments",
                    "No counterpart in the school data",
                    "Not used",
                ),
            ),
        },
        "b411": (
            "In each class, the two signals are ranked within the class and about one fifth of "
            "the class is flagged by their average. No probability or score is shown; every "
            "flag comes with its reason. Risk is visible only to teachers and the principal."
        ),
        # 4.12
        "sinirlar": (
            "Single institution, single country, and distance learning; the findings cannot be "
            "generalized directly to a Turkish high school. Failing and withdrawing were "
            "grouped into one class; they may be different processes. There is only one "
            "validation term. No uncertainty intervals were computed for the unseen-course "
            "analysis. SHAP is not causation. The school's two signals are not identical to "
            "the OULAD signals, only their closest counterparts. The teacher effect could not "
            "be tested."
        ),
        # 4.13
        "yeniden_uretim": (
            "All numbers and charts are produced from the same code package; the notebooks call "
            "this package instead of copying code. Commands and notebook names: 01_uci_eda, "
            "02_oulad_eda, 03_oulad_model (TR/EN). References: Cortez & Silva (2008); "
            "Kuzilek, Hlosta & Zdrahal (2017)."
        ),
        # ====================================================================================
        # Spec v2 ve spec v2 eki: yalnızca belirtimde İngilizce metni VERİLEN bloklar.
        # Verilmeyenler EKSIK_EN'dedir ve burada yoktur; çeviri uydurulmamıştır.
        # ====================================================================================
        "sekmeler": {
            "ozet": "Summary",
            "veri": "Datasets",
            "uci": "UCI exploration",
            "oulad": "OULAD exploration",
            "model": "Modelling",
            "kural": "Decision rule",
            "ek": "Further analyses",
            "hoca": "Teacher effect",
            "sistem": "Bridge to the system",
            "hatalar": "Errors and fixes",
            "kaynak": "Limits and sources",
        },
        "ozet_gosterebildik_baslik": "What these data let us show",
        "ozet_gosterebildik": (
            (
                "From a student's own trace (assignments, grades, activity) a meaningful early "
                "warning can be built at day 60 of a course; within-class ranking performance is ROC "
                "AUC ≈ {sets.within_module_mean.GENERAL.test:roc}."
            ),
            "Risk levels genuinely differ between courses and drift from term to term.",
            (
                "An untrained two-signal rule that never looks at outcomes catches "
                "{rule.capture_rule2.2014J:yuzde} of the model's hits."
            ),
            (
                "The model and the rule find students who will stay and fail at a somewhat higher "
                "rate than students who will drop out."
            ),
        ),
        "ozet_gosteremedik_baslik": "What they do not",
        "ozet_gosteremedik": (
            "The teacher effect: neither dataset records the teacher (Teacher effect tab).",
            "The causal effect of any signal: every finding is associational.",
            (
                "Direct generalisation to a Turkish high school: the data come from Portuguese high "
                "schools and UK distance learning."
            ),
        ),
        "z1_duraklar": (
            (
                "H8",
                (
                    "**The question.** In UCI early grades drive the final; absence first looked "
                    "weak (an error). No course or exam context. *Decision:* move to a time-ordered "
                    "dataset."
                ),
            ),
            (
                "H9",
                (
                    "**The data.** OULAD, day-60 cutoff, leak-free temporal split, course-history "
                    "features. *Decision:* no model yet, describe first."
                ),
            ),
            (
                "H10",
                (
                    "**The test.** Course history did not improve prediction; a set designed after "
                    "seeing test results collapsed on validation. *Decision:* within-class "
                    "{rule.flag_rate:yuzdetam}, no absolute probability, transparent rule."
                ),
            ),
            (
                "H11",
                (
                    "**The rule.** The school has no \"missed assignment\" equivalent; a two-signal "
                    "rule was tested against pre-written criteria and accepted."
                ),
            ),
            (
                "H11+",
                (
                    "**We questioned ourselves.** The suspicion that the work was too linear and the "
                    "model might only find students who drop out was written as "
                    "{ek.summary.total:tam} expectations, sealed with md5, and tested. The suspicion "
                    "did not hold."
                ),
            ),
        ),
        "veri_bu_bolumde": (
            "The study rests on two open datasets: a small high-school dataset with rich student "
            "information, and a large, time-ordered distance-learning dataset. Which one can "
            "answer which question is the key to reading the results."
        ),
        "veri_sosyokultur": (
            "Socio-cultural columns existed in both datasets but were never used: the school "
            "system does not hold them, and a risk flag based on family or background would risk "
            "labelling students."
        ),
        "uci_bu_bolumde": (
            "In a small high-school dataset we looked at what drives the final grade. Two "
            "findings and one error emerged: term grades nearly determine the final (so they "
            "cannot serve an early warning), past failure is the strongest non-grade signal, and "
            "absence wrongly looked weak in the first analysis."
        ),
        "uci_u2_bulgu": (
            "The {uci.g3_zero:tam} records with a final grade of 0 (Mathematics "
            "{uci.g3_zero_by_subject.mat:tam}, Portuguese {uci.g3_zero_by_subject.por:tam}) sit "
            "apart from the rest of the distribution: most likely they are not a grade but a "
            "missed exam or a dropout."
        ),
        "uci_u5_bulgu": (
            "Between G2 and G3, r = {uci.corr_g2:kor}. A model that knows the end-of-term grade "
            "does not \"predict\" the final, it nearly reads it. So two feature sets were "
            "defined: EARLY ({turev.uci.n_early:tam} columns, no term grades) and MIDTERM (G1 "
            "only)."
        ),
        "oulad_bu_bolumde": (
            "Before modelling we looked at the data. Risk levels vary clearly by course and "
            "term, while early signals in the student's trace show a strong, orderly "
            "relationship with risk. Everything here is descriptive; nothing claims a cause."
        ),
        "oulad_o4_secenekler": (
            "Unsubmitted assignments",
            "Clicks",
            "Average score",
            "Score versus course history",
        ),
        "model_bu_bolumde": (
            "We compared five feature sets with two model types, once, on the same test term. "
            "Knowing the course history did not improve prediction; it made it worse. The set "
            "that looked best on test came last on independent validation. The results are "
            "modest but consistent: what works is the student's own trace."
        ),
        # Tanımlar notebook 03 hücre 2 metninden (03_oulad_model_eng.ipynb, "Design").
        "model_m0": {
            "satirlar": (
                (
                    "GENERAL",
                    "carries assessment and virtual-learning activity up to the cutoff day, plus "
                    "the registration day. Click counts by activity type are included. The "
                    "module code and earlier presentations are absent.",
                    "",
                ),
                ("GENERAL_MODULE", "adds the module code to those columns.", ""),
                (
                    "HISTORY",
                    "adds the earlier presentations' module risk rate, slot score, slot "
                    "submission rate, the score gap from the historical slot, and an indicator "
                    "that history exists.",
                    "",
                ),
                (
                    "HISTORY_SLOT",
                    "adds the slot score, the slot submission rate, the score gap from the "
                    "historical slot, and the history indicator. The module risk rate is not in "
                    "this set.",
                    "exploratory",
                ),
                (
                    "GENERAL_REL",
                    "replaces raw values with percentile ranks inside the same module "
                    "presentation. The ranks cover score, submission ratio, clicks, active days, "
                    "recency of the last activity, and delay. The registration day stays beside "
                    "them. The module code is absent. The risk label is not read when the ranks "
                    "are computed.",
                    "exploratory",
                ),
            ),
            "notlar": (
                "The model types are `logreg` and `hgb`.",
                "Tuning fits on the first presentation in the train split. Selection uses log "
                "loss on the next presentation. The chosen settings are refit on the whole train "
                "split. The test presentation is evaluated once, at the end. Intervals come from "
                "bootstrap samples stratified by class inside each module.",
                "`HISTORY_SLOT` and `GENERAL_REL` were added after the first test results were "
                "seen. Both are exploratory. The test split stays frozen, and the validation "
                "period is reported on its own.",
            ),
        },
        "kural_r2_bulgu": (
            "The model leads in every module-term, but narrowly: the points sit just above the "
            "line. The price of transparency is not a jump but a small, steady loss."
        ),
        "sistem_kopru": (
            "There is no model in the system, because the school does not record \"this student "
            "eventually failed\"; there is no label to train on. Only the recipe is carried "
            "over: which two signals, in which direction, how they are ranked within a class, "
            "and how many students are flagged. The school's demo data is synthetic, and no "
            "result in this report is drawn from it."
        ),
        "hoca_bu_bolumde": (
            "In real life teachers make a difference; the same course can turn out differently "
            "with a different teacher. That was the question this study started from. Here we "
            "state plainly why these data cannot measure a teacher effect, what it would take to "
            "measure one, and what our data do and do not show about it."
        ),
        "hoca_10_1": (
            "To see a teacher's effect, one needs to follow many groups of students taking the "
            "same course from the same teacher across years, and compare them with other "
            "teachers' groups while accounting for students' starting level. Only then can "
            "\"is this difference due to the teacher, that year's students, the course content, "
            "or the exam difficulty?\" be separated. Neither dataset records which student was "
            "taught by which teacher. OULAD has course and term; but a course-term carries the "
            "teacher, the material, the exam and that term's students in one bundle."
        ),
        "hoca_h1_aciklama": (
            "Shown: early signals relate strongly and consistently to risk; within-class ranking "
            "holds across two terms.",
            "Shown (level): risk levels differ between courses, but this does not change who "
            "ranks as at risk.",
            "Shown (drift): a course's risk drifts between terms; the past does not reliably "
            "carry into the future.",
            "Measured, not separable: teacher, material, exam and cohort together; they cannot "
            "be told apart.",
            "Not measurable: no data.",
        ),
        "hoca_10_2": (
            "We could measure the total difference at the course-term level; any teacher effect lies "
            "somewhere inside that bundle. We showed the upper bound of that difference (OULAD "
            "exploration and Modelling tabs) and how much it drifts over time (same tabs). So we "
            "built the system to be **insensitive** to teacher effects: each class is ranked within "
            "itself, with no absolute threshold or probability. If one teacher's class scores higher "
            "or lower overall, that does not change the number of flags; every teacher gets "
            "follow-up capacity for about one fifth of the class. We could not measure the teacher "
            "effect, but we made sure the system does not depend on it."
        ),
        "hoca_10_3": (
            "Even if teacher effects became measurable, this should not become a tool for "
            "ranking teachers. With small classes and few years these estimates are very noisy "
            "and cannot be the sole basis for a decision. The school assistant likewise does not "
            "answer \"which teacher is better\" with grade averages."
        ),
        "hoca_bulgu": (
            "**The most honest sentence these data allow about the teacher effect: we cannot "
            "measure it, but we can show that the whole course-term context difference does not "
            "distort the system's flags.**"
        ),
        "hatalar_bu_bolumde": (
            "An analysis is as trustworthy as the way it finds its own mistakes. Each record "
            "below shows the symptom, the root cause, the fix, and what changed afterwards."
        ),
        "hata_basliklar": (
            "Absence looked weak",
            "A test-inspired set collapsed on validation",
            "\"Only the past rate\" guess",
            "\"GENERAL_REL only misses the level\" guess",
            "Course-history hypothesis not supported",
            "Wrong caption on the unseen-course chart",
            "The rule's first signal has no school counterpart",
            "Analysis logic lived in a notebook cell",
            "Analysis logic lived inside notebook 02 and 03 cells",
            "The virtual environment was a copy; notebooks ran in another environment",
            "The pre-registration check read the first record",
            "The main suspicion did not hold",
        ),
        "ek_bu_bolumde": (
            "Until here the work moved along a single line: one cutoff day, one target, one "
            "feature bundle. In this tab we questioned our own result: does the model really "
            "find struggling students, or only those who have already dropped out? We wrote our "
            "expectations before running anything, sealed them, and then tested them."
        ),
        "ek_suphe": (
            "**The suspicion:** The target is \"failed or withdrew\". A student who withdraws "
            "also stops logging in and submitting; perhaps that is all the model sees."
        ),
        "ek_onkayit": (
            "Before running the analyses we wrote {ek.summary.total:tam} expectations with numeric "
            "criteria and recorded the files' md5 values. The analysis code refuses to run if those "
            "files changed after registration. An expectation counted as \"held\" only if it held in "
            "both periods (validation and test), \"did not hold\" if it failed in both, and "
            "\"inconclusive\" if the periods disagreed."
        ),
        "ek_e2_metin": (
            "First question: who is easier to find? We predicted \"failed\" and \"withdrew\" "
            "separately. We expected withdrawals to be easier (B4). The opposite held: in both "
            "periods, students who will fail are easier to find."
        ),
        # Metin yaması (H11): daha önce EKSIK_EN'de olan bloklar.
        "okuma_suresi": "Reading time ~20 min",
        "veri_d0_baslik": "Side-by-side comparison",
        "veri_d0": {
            "ust": (
                "Dimension",
                "UCI Student Performance",
                "OULAD",
            ),
            "satirlar": (
                (
                    "Institution and place",
                    "Two high schools, Portugal",
                    "Open University, United Kingdom",
                ),
                (
                    "Type of education",
                    "Face-to-face high school",
                    "Distance, university",
                ),
                (
                    "Time",
                    "One school year",
                    "2013–2014, four terms (presentations)",
                ),
                (
                    "Size",
                    "{uci.total:tam} student-course records",
                    (
                        "{oulad.n_rows_raw:tam} student-course records, {oulad.n_vle_rows:tam} "
                        "activity rows"
                    ),
                ),
                (
                    "Unit",
                    "Student × course",
                    "Student × module × presentation",
                ),
                (
                    "Target",
                    "Final grade < {uci.pass_threshold_20:tam} / 20",
                    "Failed or withdrew",
                ),
                (
                    "Temporal signal",
                    "None (term grades only)",
                    "Yes (daily activity, assignment dates)",
                ),
                (
                    "Course context",
                    "Two courses",
                    "{oulad.n_courses:tam} course-terms, {turev.oulad.n_modul:tam} modules",
                ),
                (
                    "Teacher information",
                    "None",
                    "None",
                ),
                (
                    "Socio-cultural information",
                    "Present (not used)",
                    "Present (not used)",
                ),
                (
                    "Can answer",
                    "Which student information relates to the final grade?",
                    "Is early warning possible; do course and time context change the prediction?",
                ),
                (
                    "Cannot answer",
                    "Early warning (no exam dates), context",
                    "Teacher effect, generalisation to high school",
                ),
                (
                    "Licence",
                    "CC BY 4.0",
                    "CC BY 4.0",
                ),
            ),
        },
        "veri_d1_alt": (
            "Row counts of the seven tables, logarithmic scale. The largest is the daily activity "
            "log."
        ),
        "veri_d2_not": (
            "Students who unregistered before day 60 were removed, because by that day there is no "
            "longer anyone to warn. Those who withdrew later stayed in the sample and counted as at "
            "risk."
        ),
        "uci_u1_not": (
            "Pass mark: {uci.pass_threshold_20:tam} out of 20, {uci.pass_grade_100:tam} on the "
            "school's 100-point scale"
        ),
        "uci_u4_alt": (
            "Pearson correlations between the numeric columns. Term grades (G1, G2) carry almost the "
            "same information as the final (G3)."
        ),
        "uci_hata_baglanti": "Errors and fixes: Absence looked weak",
        "uci_u7_baslik": "Feature sets",
        "uci_bolum_sonu": (
            "What UCI could not answer was context: one year, two courses, no exam dates. So the "
            "context hypothesis moved to OULAD."
        ),
        "oulad_o1_bulgu": (
            "The lowest rate is {turev.risk.en_dusuk:metin} ({turev.risk.en_dusuk_oran:yuzde}), the "
            "highest {turev.risk.en_yuksek:metin} ({turev.risk.en_yuksek_oran:yuzde}). Between terms "
            "of the same module the gap is at most a few points."
        ),
        "oulad_o2_alt": (
            "A point below the line means the course did better that term than its history. Most "
            "points sit below the line: risk fell over time."
        ),
        "oulad_o4_cumleler": (
            (
                "Missing a single assignment raises the risk rate from {turev.sinyal.teslim_0:yuzde} "
                "to {turev.sinyal.teslim_1:yuzde}."
            ),
            (
                "In the least active fifth, risk is {turev.sinyal.tik_ilk:yuzde}; in the most "
                "active, {turev.sinyal.tik_son:yuzde}."
            ),
            (
                "Students with no score have a higher risk ({turev.sinyal.not_eksik:yuzde}) than the "
                "middle bins: having no grade is itself a signal."
            ),
            "Students below the historical average for the same assignment are more at risk.",
        ),
        "oulad_o4_nedensellik": "This is a pattern seen together, not a cause.",
        "oulad_o4_bulgu": (
            "All four signals show an orderly relationship with risk. But these relationships are "
            "not independent of each other; only the model and SHAP can say how much each "
            "contributes (Modelling tab)."
        ),
        "oulad_o5": {
            "baslik": "Feature → school counterpart",
            "ust": (
                "School counterpart",
                "Feature",
            ),
        },
        "model_m0_baslik": "Feature sets",
        "model_m3_bulgu": (
            "The HISTORY − GENERAL difference is below zero for both model types and its interval "
            "excludes zero: course history makes prediction worse."
        ),
        "model_m5_bulgu": (
            "Within classes, the differences between sets are a few thousandths, and their order "
            "changes from term to term."
        ),
        "model_m7_bulgu": (
            "The model does not learn the historical risk rate from {turev.model.egitim_satir:tam} "
            "rows, but from only {model.hist_rate_distinct_train:tam} distinct term values; and risk "
            "fell over time. Result: the historical rate pushes predictions up in a new term."
        ),
        "hoca_basliklar": {
            "h10_1": "Why can we not measure it?",
            "h10_2": "What our data allow us to say",
            "h10_3": "An ethical note",
        },
        "hoca_h1_katman": (
            (
                "The student's own trace",
                "Shown",
            ),
            (
                "Course",
                "Shown (level)",
            ),
            (
                "Time (term)",
                "Shown (drift)",
            ),
            (
                "Course × term bundle",
                "Measured, not separable",
            ),
            (
                "Teacher",
                "Not measurable",
            ),
        ),
        "hoca_h2": {
            "baslik": "Data a real study would need",
            "ust": (
                "Requirement",
                "UCI",
                "OULAD",
                "School system (today)",
                "School system (over years)",
            ),
            "satirlar": (
                (
                    "Student–teacher link",
                    "No",
                    "No",
                    "Homeroom teacher yes; subject teacher no",
                    "Subject teacher can be added",
                ),
                (
                    "Same teacher across years",
                    "No",
                    "No",
                    "No (one year)",
                    "Accumulates",
                ),
                (
                    "Student's starting level",
                    "Partly (past failures)",
                    "Partly (previous attempts)",
                    "No",
                    "Previous year's grades",
                ),
                (
                    "Outcome label (passed/failed)",
                    "Yes",
                    "Yes",
                    "No",
                    "Accumulates",
                ),
                (
                    "Same exam, different teachers",
                    "No",
                    "No",
                    "No",
                    "Possible with common exams",
                ),
            ),
        },
        "hata_tur": (
            "Data",
            "Method",
            "Interpretation",
            "Interpretation",
            "Method (not an error: a hypothesis that did not hold)",
            "Interpretation",
            "Method",
            "Reproducibility",
            "Reproducibility",
            "Reproducibility",
            "Method (the run stopped; files unchanged)",
            "Interpretation (not an error: a hypothesis that did not hold)",
        ),
        "hata_bag_not": {
            "1": "the included/excluded selector is this record's \"before/after\" view",
            "3": "HISTORY_SLOT row",
        },
        "hata_govde": {
            "1": {
                "belirti": (
                    "In the first analysis, the relationship between absence and the final grade "
                    "looked weak."
                ),
                "kok": (
                    "All {uci.g3_zero:tam} records with a final grade of 0 also had 0 absences. They "
                    "were most likely students who missed the exam or left, and they suppressed the "
                    "relationship."
                ),
                "duzeltme": (
                    "G3=0 records were examined separately; the absence analysis was run in two "
                    "views, included and excluded."
                ),
                "sonra": (
                    "With them excluded, the pass rate fell steadily as absence rose. Still, absence "
                    "alone does not decide."
                ),
            },
            "2": {
                "belirti": (
                    "GENERAL_REL looked like the best set on test "
                    "({sets.roc_test.GENERAL_REL.hgb.estimate:roc})."
                ),
                "kok": (
                    "The set had been designed after looking at test results; fitting the test term "
                    "could look like a real improvement."
                ),
                "duzeltme": (
                    "The set was measured on the independent validation term and gave the lowest "
                    "result ({sets.roc_val.GENERAL_REL.hgb:roc})."
                ),
                "sonra": (
                    "The set was not adopted. The test term was frozen; sets added afterwards were "
                    "marked \"exploratory\"."
                ),
            },
            "3": {
                "belirti": (
                    "Adding course history made the result worse, and the course's historical risk "
                    "rate alone was guessed to be the cause."
                ),
                "kok": "The explanation was about to be accepted without a test.",
                "duzeltme": (
                    "The HISTORY_SLOT set was built without the historical risk rate and measured "
                    "with the same protocol."
                ),
                "sonra": (
                    "The result stayed the same: historical assignment features do not generalise "
                    "either. The guess was wrong and was not reported as a result."
                ),
            },
            "4": {
                "belirti": (
                    "When GENERAL_REL dropped on validation, the drop was thought to come only from "
                    "the level, with the ranking intact."
                ),
                "kok": "The ranking was assumed to be sound, not measured.",
                "duzeltme": "Within-class ranking performance was measured on the validation term.",
                "sonra": (
                    "The ranking was the lowest as well. The guess was wrong; the set was not "
                    "adopted."
                ),
            },
            "5": {
                "belirti": "Knowing a course's history was expected to improve prediction.",
                "kok": (
                    "A course's risk rate drifts from term to term, and the model learns the "
                    "historical rate from only a few distinct term values."
                ),
                "duzeltme": (
                    "The hypothesis was tested with paired differences and also on the validation "
                    "term; the result was reported as it was."
                ),
                "sonra": (
                    "Half of the hypothesis held (course level), half did not (course history's "
                    "contribution to ranking). Both were reported."
                ),
            },
            "6": {
                "belirti": (
                    "the alt text of the unseen-course figure described the highlighted row as \"the "
                    "course left out of training\"."
                ),
                "kok": (
                    "in this analysis every row is a course unseen in training. GGG is highlighted "
                    "for another reason: it has no graded assessment by day 60."
                ),
                "duzeltme": "title, alt text (TR/EN) and an explanatory note on the GGG row were updated.",
                "sonra": "verified (figures.json and the regenerated figure were checked).",
            },
            "7": {
                "belirti": "The first rule had three signals; one of them was unsubmitted assignments.",
                "kok": (
                    "The school system keeps no assignment submission record, so this signal could "
                    "not be applied at school."
                ),
                "duzeltme": (
                    "The rule was reduced to two signals (grade average and active days) and "
                    "re-tested with the same criterion and pre-written rules."
                ),
                "sonra": (
                    "The two-signal rule was accepted. The submission record was listed for future "
                    "work as the most valuable missing signal for the school."
                ),
            },
            "8": {
                "belirti": (
                    "The report said 'logic is called from the package', but the absence analysis "
                    "was defined in a notebook cell."
                ),
                "kok": "The calculation was written in the notebook and never moved to the package.",
                "duzeltme": (
                    "The functions were moved to the `data_science.absence` module; the notebook "
                    "calls them from there; the Week 8 values were verified by tests."
                ),
                "sonra": (
                    "The notebook and the package give the same values; the numbers in the report "
                    "come from a single source."
                ),
            },
            "9": {
                "belirti": (
                    "Some tables and calculations in notebooks 02 and 03 were defined inside cells; "
                    "the packager could not use them without copying."
                ),
                "kok": (
                    "The same pattern had been fixed in the first notebook but not looked for in the "
                    "others."
                ),
                "duzeltme": (
                    "The calculations were moved to the `data_science` package (`oulad/eda.py`, "
                    "`oulad/model_tables.py`); the notebooks call them from there."
                ),
                "sonra": (
                    "The notebooks were re-run; every code cell's output was identical to the "
                    "previous output."
                ),
            },
            "10": {
                "belirti": (
                    "The virtual environment had been copied from another week's folder; its scripts "
                    "and Jupyter kernel pointed to the old environment's Python."
                ),
                "kok": (
                    "Paths inside the copied environment were never updated; the notebooks were "
                    "running in a different environment."
                ),
                "duzeltme": (
                    "Commands were run through the environment's own Python, and a kernel belonging "
                    "to the environment was registered."
                ),
                "sonra": (
                    "Notebook 03 was re-run in the correct environment and its outputs stayed the "
                    "same. It was verified that `explain.json` was produced with TreeExplainer."
                ),
            },
            "11": {
                "belirti": "The further-analysis run stopped at the pre-registration check.",
                "kok": (
                    "The addendum had been updated once before the run, leaving two md5 records; the "
                    "check read the first record instead of the last."
                ),
                "duzeltme": (
                    "The check was fixed to read the last record; the pre-registration files were "
                    "not changed."
                ),
                "sonra": (
                    "The run started with the files in their last sealed state; both records remain "
                    "in the seal table."
                ),
            },
            "12": {
                "belirti": (
                    "The work had moved along a single line; we suspected the model only found "
                    "students who drop out."
                ),
                "kok": (
                    "The target \"failed or withdrew\" was combined; the two groups had never been "
                    "measured separately."
                ),
                "duzeltme": (
                    "The suspicion was written down in advance as numeric expectations and sealed; "
                    "the two targets were predicted separately."
                ),
                "sonra": (
                    "B4, B5 and B7 did not hold. This became one of the study's most important "
                    "findings."
                ),
            },
        },
        "kaynak_kaynakca": (
            "Cortez and Silva (2008)",
            "Kuzilek, Hlosta and Zdrahal (2017)",
            "scikit-learn",
            "SHAP",
        ),
        "kaynak_yazar": "Ensar Bera Ergin · Türksat A.Ş. summer internship · 2026",
        "sayfa_sonu": "To reproduce this report together with its source code",
        "ek_basliklar": {
            "harita": "Map of our thinking",
            "onkayit": "Pre-registration",
            "e2": "The suspicion falls apart (E2)",
            "e1": "Where is the information? (E1)",
            "e3": "How early? (E3)",
            "e4": "What did others find? (E4)",
            "kapanis": "Closing: what changed, what did not",
        },
        "ek_harita": {
            "bulduk": "What we found",
            "eksik": "What it left open",
            "duraklar": (
                (
                    "W8 · UCI",
                    (
                        "Term grades nearly determine the final; absence (after the G3=0 fix) "
                        "relates to risk."
                    ),
                    "No context, no time. Early warning cannot be built.",
                ),
                (
                    "W9 · OULAD exploration",
                    (
                        "Risk levels vary by course and term; a student's early trace relates "
                        "strongly to risk."
                    ),
                    "All descriptive.",
                ),
                (
                    "W10 · Model",
                    (
                        "Course history did not improve prediction; what works is the student's own "
                        "trace and within-class ranking."
                    ),
                    (
                        "**The work moved in a straight line:** one cutoff day (60), one target "
                        "(failed ∪ withdrew), one feature bundle (\"the student's trace\" as a "
                        "single block)."
                    ),
                ),
                (
                    "W11 · Rule",
                    "A two-signal rule (grades + activity) catches most of the model's hits.",
                    (
                        "What exactly does \"the student's trace\" capture? The student whose grades "
                        "are falling, or the one who has already dropped out?"
                    ),
                ),
            ),
        },
        "ek_sorular": (
            (
                "E1 · Signal decomposition",
                (
                    "How much information does each signal group carry on its own? How far can "
                    "grades alone go?"
                ),
            ),
            (
                "E2 · Target decomposition",
                (
                    "Does the model find \"failed\" and \"withdrew\" equally easily? Whom does the "
                    "rule flag?"
                ),
            ),
            (
                "E3 · How early?",
                (
                    "The cost of early warning: how does performance change as the cutoff day moves "
                    "earlier?"
                ),
            ),
            (
                "E4 · Comparison with literature",
                "Why are our numbers lower than published ones, and what does that mean?",
            ),
        ),
        "ek_muhur": {
            "baslik": "Seal table",
            "ust": (
                "File",
                "md5",
                "Time",
            ),
            "not": "The addendum was updated once before the run; both records remain.",
        },
        "ek_onkayit_ozet": (
            "{ek.summary.tuttu:tam} held, {ek.summary.tutmadı:tam} did not hold, "
            "{ek.summary.belirsiz:tam} inconclusive."
        ),
        "ek_x2_alt": (
            "The rule also catches about a third of those who withdraw, but it finds those who will "
            "fail at a somewhat higher rate. It is not a 'disengaged-student detector'."
        ),
        "ek_e2_bulgu": (
            "**The model and the rule are not doing the easy part.** They find students who will "
            "stay and fail more easily, and at a somewhat higher rate, than students who will "
            "withdraw."
        ),
        "ek_e1_metin": (
            "We split the student's trace into four groups: grades, assignment submission behaviour, "
            "online activity and registration date. No group alone reaches the full model (B1). "
            "Grades and submissions together come very close to it (B3). Which single group is "
            "strongest changes from term to term (B2 inconclusive): relying on one signal would be a "
            "small repeat of the \"first on test, last on validation\" lesson from the Modelling tab."
        ),
        "ek_e1_bulgu": (
            "**For the school:** the main carrier of the risk flag is not absence but the grade and "
            "assignment record. The school has no submission record today; this work shows it is the "
            "most valuable missing signal."
        ),
        "ek_e3_metin": (
            "Early warning has a cost: the earlier we warn, the less information we warn with. We "
            "ran the same pipeline for days 14, 30, 60, 90 and 120. Performance rose at every step "
            "(B8), most of the gain came by day 60 (B9), and on day 14 activity alone carried almost "
            "all of the performance (B10)."
        ),
        "ek_e3_karar": (
            "We noticed before running: on day 14, no course in the test term has a graded "
            "assignment. The rule 'no flag in a class without graded assignments' is a rule of the "
            "school system, not of model evaluation; so it was not applied in E3. The decision was "
            "written into an additional pre-registration file before any results were seen."
        ),
        "ek_x5_not": "In the fixed cohort, 'withdrew' means withdrew after day 120.",
        "ek_e3_bulgu": (
            "**Day 60 was justified in hindsight.** Most of the gain comes between day 14 and day "
            "60; day 60 is the point where most of the gain has been collected and there is still "
            "time to intervene."
        ),
        # DIŞ KAYNAK SAYISI (spec eki 2.6, tek istisna): "%90'ın üzerinde" yayınlardan gelir, paketten değil.
        "ek_e4_metin": (
            "Published work reports values above 90% for OULAD (with different metrics); our test "
            "value is ROC AUC {sets.roc_test.GENERAL.hgb.estimate:roc}. These numbers cannot be "
            "compared directly: the prediction time, the split, the target and the use of "
            "demographic features differ between studies. The two high-scoring studies we examined "
            "use demographic features, and their highest values belong to the end of the course; we "
            "could not verify their split types. An independent study with the closest design (Wu, "
            "Jia and Pham, 2026) lands in the same range as our numbers and also replicates the "
            "finding that \"withdrawal is harder\" on its own data."
        ),
        # DIŞ KAYNAK SAYILARI (spec eki 2.6, tek istisna): Wu/Adnan/Scientific Reports satırları,
        # gözlemler ve kaynakça literatürden birebir alındı; paket değeri değildir. Bu çalışmanın
        # kendi değerleri yer tutucudur.
        "ek_l1": {
            "baslik": "Table L1",
            "ust": (
                "Study",
                "Prediction time",
                "Split",
                "Target",
                "Demographic features",
                "Reported value",
            ),
            "satirlar": (
                (
                    "This study",
                    "Day 60 (E3: 14–120)",
                    "Temporal: trained on 2013J, 2014B validation, 2014J test",
                    "Failed ∪ withdrew; students who unregistered before the cutoff excluded",
                    "No",
                    (
                        "ROC AUC test {sets.roc_test.GENERAL.hgb.estimate:roc} (day 60, GGG "
                        "included); fixed cohort, day 30: {turev.ek.e3_30_test:roc}"
                    ),
                ),
                (
                    "Wu, Jia and Pham (2026), Frontiers in Education 11",
                    "Day 28",
                    "Random 80/20 grouped by student, and separately temporal (2013 → 2014)",
                    "Failed ∪ later withdrew; students who unregistered before day 28 excluded",
                    "Yes (9 background/administrative features) and no; both reported",
                    (
                        "ROC AUC: all features 0.775, behaviour only 0.750 (grouped split); "
                        "temporal: 0.747 (all, RF), 0.709 (behaviour only, HistGB)"
                    ),
                ),
                (
                    "Adnan et al. (2021), IEEE Access 9",
                    "0, 20, 40, 60, 80, 100% of the course",
                    "Not verified",
                    "Withdrawn / Fail / Pass / Distinction (multi-class and merged variants)",
                    "Yes",
                    (
                        "RF mean precision: 0.79 at 20%, 0.92 at 100% (accuracy 0.79 at 20%, 0.91 at "
                        "100%)"
                    ),
                ),
                (
                    (
                        "Scientific Reports (2025), \"Accurate multi-category student performance "
                        "forecasting at early stages of online education using neural networks\""
                    ),
                    "About 20% of the course",
                    "Not verified",
                    "Distinction / Fail / Pass / Withdrawn",
                    "Yes (demographic, assessment, clicks)",
                    "Accuracy 92% (at about 20%)",
                ),
            ),
            "gri": "Not verified",
            "gozlemler": (
                (
                    "**Observation 1: The prediction time drives the number.** In Adnan et al., "
                    "performance rises steadily from 0% to 100% of the course; this is the same "
                    "shape as our E3 curve (B8, B9). A value for the whole course or a late window "
                    "cannot be compared with a value at day 60."
                ),
                (
                    "**Observation 2: The closest setup independently gives similar numbers.** Wu et "
                    "al. (2026) is the design closest to ours: an early fixed day, exclusion of "
                    "students who withdrew before the cutoff, temporal validation, and a model "
                    "without demographic features. Their behaviour-only model in temporal transfer "
                    "(0.709, day 28) is very close to our day-30 fixed-cohort value "
                    "({turev.ek.e3_30_test:roc}). The setups are not identical: test set, cohort "
                    "definition and features differ. This is not a validation, but a sign that our "
                    "numbers are in a reasonable range for this family of protocols."
                ),
                (
                    "**Observation 3: \"Withdrawal is harder\" replicates independently.** In Wu et "
                    "al., among students still registered on day 28, predicting later withdrawal "
                    "(0.697) is harder than predicting failure (0.720); separating failure from "
                    "passing among non-withdrawers is the easiest task (0.783). This points the same "
                    "way as our B4 result, which went against the pre-registration. The same study "
                    "reports that withdrawal prediction relies more on submission information and "
                    "failure prediction more on activity; this is consistent with our hypothesis "
                    "that \"the early trace of withdrawal is in submissions\". Neither study claims "
                    "causality."
                ),
                (
                    "**Observation 4: Courses without graded assignments.** In Wu et al., the two "
                    "courses that transfer worst to other courses are GGG and EEE, which have no "
                    "graded assignment in the prediction window. Our exclusion of GGG from the flag "
                    "rule at day 60 for lack of graded assignments, and the absence of any graded "
                    "assignment in the test term at day 14 in E3, point to the same structural "
                    "problem."
                ),
                (
                    "**Observation 5 (hypothesis): Why withdrawal looks \"easy\" in some studies.** "
                    "The *Scientific Reports* (2025) study reports finding the Withdrawn class with "
                    "high accuracy at early stages. In our design and in Wu et al., students who "
                    "unregistered before the prediction time are removed, because their outcome is "
                    "already known at that moment. If they stay in the sample, part of the "
                    "\"withdrew\" class becomes easy by definition. Since we did not verify that "
                    "study's sampling rule, this is a suggested explanation, not a finding."
                ),
            ),
            "kaynakca": (
                (
                    "Wu, M., Jia, J. ve Pham, T. T. (2026). Early warning of academic risk from the "
                    "first four weeks of online learning activity and assessment performance: a "
                    "leakage-controlled, demographic-data-minimizing study on the OULAD benchmark. "
                    "*Frontiers in Education*, 11. doi:10.3389/feduc.2026.1917092"
                ),
                (
                    "Adnan, M. vd. (2021). Predicting at-risk students at different percentages of "
                    "course length for early intervention using machine learning models. *IEEE "
                    "Access*, 9, 7519–7539. doi:10.1109/ACCESS.2021.3049446"
                ),
                (
                    "Accurate multi-category student performance forecasting at early stages of "
                    "online education using neural networks (2025). *Scientific Reports*. "
                    "https://www.nature.com/articles/s41598-025-00256-3"
                ),
            ),
        },
        "ek_kapanis": {
            "degisti": (
                "**Changed:** our suspicion did not hold; we now know what the system catches. The "
                "choice of day 60 was justified. The most valuable missing signal for the school was "
                "identified: the assignment submission record."
            ),
            "degismedi": (
                "**Unchanged:** the rule in the system. The further analyses were done to "
                "understand, not to fix; any proposed change would be tested separately with new, "
                "pre-written criteria."
            ),
        },
        "ham_uci": {
            "korelasyon": "Correlations",
            "devamsizlik": "Absence bins (included/excluded)",
            "g3_sifir": "G3=0 counts",
        },
        "ham_oulad": {
            "tablolar": "Table sizes",
            "final": "Final results",
            "risk": "Risk pivot",
            "gecmis": "Past vs present",
            "yuva": "Slot means",
            "sinyaller": "Four signal tables",
            "ggg": "GGG summary",
        },
        "ham_model": {
            "test": "Test metrics",
            "esli": "Paired differences",
            "dogrulama": "Validation",
            "modul_roc": "Module ROC",
            "taban": "Base rate",
            "lomo": "LOMO",
            "shap": "SHAP",
        },
        # Metin yaması (H11): "Bu bölümde" kutuları (yeni_metinler).
        "ozet_bu_bolumde": (
            "This page tells the research behind the school system's risk flag. The question was: "
            "can we tell, early and with reasons, that a student is struggling? The short answer: "
            "yes, from the student's own trace, with modest performance; the teacher effect cannot "
            "be measured with these data."
        ),
        "kural_bu_bolumde": (
            "Since the school has no outcome data to train a model on, we replaced the model with a "
            "transparent rule and measured how far behind the model it falls. The answer: behind, "
            "but only slightly; the cost is small and steady. You can see the balance between "
            "precision and recall yourself by changing the flag rate."
        ),
        "sistem_bu_bolumde": (
            "Shows what was carried from the research into the school system. Not a model and not "
            "data, only the recipe of a tested rule: which two signals, in which direction, and how "
            "many students within a class."
        ),
        "kaynak_bu_bolumde": (
            "Brings together what the study cannot say, how the results can be reproduced, and the "
            "sources used."
        ),
    },
}

# Arayüz etiketleri (bölüm kutusu, ham tablo düğmeleri, hata kartı alanları). Belirtim bunların
# İngilizcesini vermedi; çeviri değil, işlevsel etiketlerdir. Raporda ayrıca listelenir ve
# İngilizceleri kullanıcı tarafından onaylanmalı ya da değiştirilmelidir.
ARAYUZ: dict[str, dict] = {
    "tr": {
        "bu_bolumde": "Bu bölümde",
        "bulgu": "Bulgu",
        "ham_tablolar": "Ham tablolar",
        "csv_indir": "CSV indir",
        "belirti": "Belirti",
        "kok": "Kök neden",
        "duzeltme": "Düzeltme",
        "sonra": "Sonra",
        "gorsel": "Görsel",
        "atif_grafik": "Grafik",
        "sonuclar": "Sonuçlar",
        "alt_eksik": "alt metin eksik",
        "sinyal": "Sinyal",
        "m0_ust": ("Özellik seti", "Tanım", "Etiket"),
    },
    "en": {
        "bu_bolumde": "In this section",
        "bulgu": "Finding",
        "ham_tablolar": "Raw tables",
        "csv_indir": "Download CSV",
        "belirti": "Symptom",
        "kok": "Root cause",
        "duzeltme": "Fix",
        "sonra": "Outcome",
        "gorsel": "Figures",
        "atif_grafik": "Chart",
        "sonuclar": "Results",
        "alt_eksik": "alt text missing",
        "sinyal": "Signal",
        "m0_ust": ("Feature set", "Definition", "Status"),
    },
}

# Sekme sırası (spec v2 eki, bölüm 1): adres çubuğundaki `bolum` değerleri bu kimliklerdir.
SEKME_SIRA: tuple[str, ...] = (
    "ozet",
    "veri",
    "uci",
    "oulad",
    "model",
    "kural",
    "ek",
    "hoca",
    "sistem",
    "hatalar",
    "kaynak",
)

# Hata kartlarının bağlantılı görselleri (spec v2, bölüm 11; kart numarası 1'den başlar).
# Belirtimde bağlantısı yazılmayan kartlar boştur.
HATA_BAGLANTI: dict[int, tuple[str, ...]] = {
    1: ("U6",),
    2: ("M4",),
    3: ("M3",),
    4: ("M4", "M5"),
    5: ("M3", "M7"),
    6: ("M8",),
    7: ("R1",),
}
