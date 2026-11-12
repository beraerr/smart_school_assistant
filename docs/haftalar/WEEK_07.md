# Hafta 7 — Güvenlik, Değerlendirme ve Konuşmalı Asistan

**Proje:** Akıllı Okul Bilgi Sistemi
**Önceki durum:** Hafta 6'nın arayüzlü sistemi (`week07/week-07/`, Hafta 6'nın kopyası)

---

## 1. Bu haftanın amacı

Hafta 1-6'da her katman kendi testiyle doğrulandı, ama sistem bütün
olarak hiç saldırgan gözüyle sınanmadı ve modelin davranışı sistematik
ölçülmedi. Bu hafta yeni özellik eklemiyoruz: (1) bir tehdit modeli
çıkarıp her tehdit için bir test yazıyoruz, (2) modelin davranışını
ölçen bir değerlendirme (eval) seti kuruyoruz.

## 2. Önemli hipotez: modelin SQL'i ile yetki yükseltme

RLS politikaları oturum ayarını (`app.role`) okuyor. Doğrulama şu an
yalnızca "tek SELECT, izinli tablolar" diye bakıyor, fonksiyonlara
bakmıyor. Bu yüzden şuna benzer tek bir SELECT doğrulamadan geçebilir:

```sql
WITH x AS (SELECT set_config('app.role','principal',true))
SELECT s.* FROM students s, x
```

Bu bir **hipotezdir, kanıtlanmış bir açık değildir.** Çalışma sırası:
önce testle yeniden üretmeye çalış; üretilirse kapat; üretilemezse
neden güvenli olduğunu belgele. Her iki durumda da kalıcı bir test ve
fonksiyon izin listesi (allowlist) kalır: bilinmeyen her fonksiyon
reddedilir.

## 3. Teslim edilecekler

- [ ] `backend/app/core/sql_safety.py` — fonksiyon izin listesi
      (`COUNT, SUM, AVG, MIN, MAX, ROUND, LOWER, UPPER, COALESCE`, tarih
      işlevleri); listede olmayan her fonksiyon reddedilir
      (`set_config`, `current_setting`, `pg_*`, `lo_*`, `dblink` dahil)
- [ ] `backend/tests/test_adversarial.py` — sahte client'la saldırgan
      SQL'ler: `set_config` (CTE ve alt sorgu biçimleri), `pg_sleep`,
      `current_setting`; her biri 400 döner; hiçbir rol kendi
      görünürlüğünün (4 / 12 / 1 / 1) ötesine geçemez
- [ ] `student_rank` saldırı testleri: başka öğrenci için çağrılamaz
      (parametresiz kimlik, oturumdan okunur), `PUBLIC` yetkisi yok,
      `search_path` sabit, çıktıda başka öğrencinin tekil verisi yok;
      fonksiyon izin listesine açıkça eklenir
- [ ] Giriş güvenliği: bilinmeyen kullanıcı ve yanlış şifre aynı `401`
      yanıtını verir; kullanıcı adı başına giriş hız sınırı (aşımda
      `429`); `CORS_ORIGINS` ayarı (`allow_origins=*` kaldırılır)
- [ ] Log/yanıt hijyeni testleri `/auth/login` için de: JWT, şifre,
      API anahtarı hiçbir yanıtta ya da logda yok
- [ ] `eval/questions.json` (~25 soru, 4 rol; tipik, sınır ve saldırgan
      istemler; her biri için beklenen davranış) ve `eval/run_eval.py`
      (çalışan API'ye gerçek modelle karşı koşar, `eval/report.md`
      geçti/kaldı tablosu üretir; pytest'in parçası değildir)
- [ ] `docs/SECURITY.md` — tehdit modeli tablosu: tehdit, savunan
      katman, kanıtlayan test; bilinen sınırlamalar

## 4. Kapsam DIŞI

- Yeni kullanıcı özelliği, arayüz değişikliği
- Dağıtık hız sınırı (Redis) ve gerçek dağıtım sertleştirmesi → Hafta 12
- Branş öğretmeni modeli → gelecek çalışma

## 5. Kabul kriterleri

1. `set_config` içeren SQL (düz, CTE ve alt sorgu biçimleri) `400` ile
   reddedilir; hiçbir testte `teacher` 4'ten fazla öğrenci görmez.
2. İzin listesindeki fonksiyonlar çalışır, listede olmayan reddedilir.
3. Bilinmeyen kullanıcı ve yanlış şifre aynı `401` gövdesini döndürür.
4. Aynı kullanıcı adıyla ardışık yanlış denemeler sınırlanır (`429`).
5. CORS izinli adresler ayardan okunur.
6. Hiçbir yanıtta ya da logda JWT, şifre, API anahtarı yoktur.
7. Eval seti çalışır ve rapor üretir; başarısız maddeler raporda
   açıkça listelenir (gizlenmez).
8. Testlerin tamamı API anahtarı olmadan geçer.
9. Kodda araç/model öz-referansı yoktur.

## 6. Demo akışı

1. Saldırgan bir soru yazılır; model `set_config` üretse bile doğrulama
   400 verir, kullanıcı hiçbir ek satır görmez.
2. Aynı soru `teacher1` ile sorulur; yine 4 satır.
3. Yanlış şifre ve bilinmeyen kullanıcı: aynı yanıt.
4. Eval raporu gösterilir: kaç soru geçti, hangileri kaldı ve neden.

## 7. Notlar

- İzin listesi bilinçli olarak sıkı: model yeni bir fonksiyon
  gerektirirse, ihtiyaç doğrulanıp listeye eklenir.
- Eval seti, "model doğru çalışıyor mu" sorusunu tek tek denemelerin
  yerine tekrarlanabilir bir ölçüme çevirir. Model aynı soruya bazen
  farklı SQL üretebildiği için sonuçlar zamanla değişebilir; rapor tarih
  ve model adıyla saklanır.
- Bu haftanın bulguları (hipotez doğrulandıysa) Hafta 7 raporunda
  açıkça belgelenir: ne denendi, ne bulundu, nasıl kapatıldı.

## 8. Sonuç: hipotez doğrulandı

- **Bulgu:** `WITH x AS (SELECT set_config('app.role','principal',true))
  SELECT s.* FROM students s, x` (ve `WHERE (SELECT set_config(...))`
  biçimi) `teacher` bağlamında 12 satır döndürdü; aynı oturumda normal
  sorgu 4 satır veriyordu. Sebep: RLS politikası taramada
  `current_setting('app.role')` okur; aynı ifadedeki `set_config` bu
  ayarı transaction içinde `principal` yapar ve tarama yeni rolü görür.
- **Kapsam:** Açık, `/query` uç noktası geldiğinden (Hafta 4) beri vardı;
  Hafta 7'deki güvenlik gözden geçirmesinde bulundu. Doğrulama yalnızca
  tek SELECT ve izinli tablolara bakıyordu, fonksiyonlara bakmıyordu.
- **Düzeltme:** `sql_safety` ayrıştırma ağacındaki tüm fonksiyon
  çağrılarını izin listesine bağlıyor; `set_config`, `current_setting`,
  `pg_*`, `lo_*`, `dblink` reddedilir. Tablo fonksiyonu olarak yalnızca
  `student_rank` `FROM` içinde serbesttir.
- **Kanıt:** saldırgan SQL'ler `/query`'de 400 döner; görünürlük
  4 / 12 / 1 / 1'in ötesine geçmez. Testler: 168 geçti. Bilinmeyen
  kullanıcı ve yanlış parola aynı 401'i verir; beş yanlış denemeden
  sonra 429.
- **Eval:** 25 / 25 geçti (model `claude-sonnet-4-5-20250929`, rapor
  `eval/report.md`). Saldırgan istemlerde model `set_config` üretmedi;
  ama asıl garanti modelin davranışı değil, doğrulama katmanıdır. Eval
  seti henüz doğal konuşma kalitesini (takip soruları, kapsam dışı
  sorular, yorum isteyen sorular) ölçmüyor.

## 9. Konuşmalı asistan

Canlı denemeler, SQL çevirici yaklaşımının doğal konuşma için yetersiz
olduğunu gösterdi (kalıp metinler, takip sorularının çalışmaması, veride
olmayan sorularda alakasız satırlar). Bu hafta `/query` araç kullanan bir
asistana dönüştürüldü: model veriyi yalnızca `run_sql` aracıyla ister;
çalışan her sorgu aynı doğrulama, izin listesi, RLS, 5 saniyelik süre ve
500 satır sınırından geçer; bir soru için en çok 3 araç çağrısı vardır.
Konuşma geçmişi (son 6 mesaj) güvenilmez girdidir. Ayrı niyet çağrısı,
sabit sohbet metni ve karşılaştırma reddi kaldırıldı. Ek veritabanı
fonksiyonu: `class_teacher()` (sınıf öğretmeninin adı). Sonuç satırları
modelin API'sine gönderilir; gerçek veride KVKK/GDPR gerektirir
(`docs/SECURITY.md`).

## 10. Canlı testte bulunan hatalar ve düzeltmeleri

1. **Sessizce yanlış sınıf ortalaması** (doğrulandı, eval). Belirti: Ali
   ve sınıf ortalaması aynı (69,79); gerçek sınıf ortalaması 74,75 (o günkü seed verisiyle; veri
   sonradan donduruldu, bkz. 8). Kök
   neden: veli hesabında RLS yüzünden yalnızca çocuğun notları görünür;
   düz SQL ile "sınıf ortalaması" yine çocuğun ortalamasını verir. Hata
   vermediği için en tehlikeli türdü. Düzeltme: sınıf/okul geneli yalnızca
   `student_rank`; veli/öğrencide toplama içeren sorgu sonucuna
   `scope_warning`; eval'de `truth_sql` ile gerçek değerle karşılaştırma.
2. **Çelişen kurallar: geçme notu** (doğrulandı, eval). Belirti: "Geçer
   notu kaç?" sorusuna "veritabanında yok". Kök neden: şema özeti geçme
   notunu "YOKTUR" listesine koyuyordu. Düzeltme: okul politikası olarak
   `PASS_GRADE` (50, MEB yönetmeliğine göre; sınıf geçme için ek kurallar
   olduğu belirtilir). 5'lik dönüşüm doğrulanamadığı için `GRADE_LABELS`
   boş bırakıldı.
3. **Eval denetleyicisi yanlış alarm veriyordu** (doğrulandı). İlk tam
   koşu 51/64 gösterdi; sayı dayanağı yalnızca son sorgunun satırlarına
   bakıyor ve "74,10" ile 74.1'i farklı sayıyordu. Her çalışan sorgu
   uygulamayla aynı `school_app` ve RLS bağlamında yeniden çalıştırılıp
   değer olarak karşılaştırılıyor.
4. **Robotik ton** (kısmen). "Tavsiye veremem" geri çekilmesi, kalın
   başlıklı kalıp cevaplar. Prompt veriye bağlı kısa destek, rehber
   öğretmen önerisi ve anlayış cümlesiyle açılış kuralı eklendi. Açık:
   model hâlâ nedensellik tahmini yürütebiliyor ("Matematik okuldan
   soğumasının nedeni olabilir").
5. **Model sayımı kendisi yapıyor** (doğrulandı, eval). Belirti: 60
   satırlık listeden "4 öğrenci" sayıyor; sayı doğru ama kaynağı sorgu
   değil. Düzeltme: araç sonucuna sütun başına ayrı değer sayısı
   (`distinct_counts`) eklendi; model sayımı `row_count`,
   `total_students` ve `distinct_counts` değerlerinden alıyor.
6. **Eval süreci kör çalışıyordu** (doğrulandı): `Retry-After`'a uymuyor,
   ilerleme yazmıyordu. Düzeltildi.

7. **Devamsızlık verisi tutarsız** (doğrulandı). Belirti: Ali için
   kayıtlı toplam 3, attendance'ta devam etmediği 10 kayıt (eski seed
   verisiyle); asistan
   çelişen sayılar verdi. Kök neden: seed, `total_absences` ile
   attendance kayıtlarını bağımsız rastgele üretiyordu (12 öğrencinin
   10'unda uyuşmazlık). Düzeltme: `total_absences` artık attendance'taki
   `present` dışı kayıt sayısı; şema özeti toplamı ve ayrıntıyı tanımlar.
8. **Seed her çalıştığında veriyi değiştiriyordu** (doğrulandı). Belirti:
   seed yeniden çalışınca Ali'nin ortalaması 69,79'dan 79,05'e, 9-A
   ortalaması 74,75'ten 76,93'e kaydı. Kök neden: tohum sabit değildi ve
   tarihler bugünden geriye hesaplanıyordu. Düzeltme: veri
   `database/mock_data.json` dosyasına donduruldu (mutlak tarihler); seed
   bu dosyadan yükler. Üç koşuda veri özeti (md5) aynı. Ders: belgelerdeki
   rakamlar veriye bağlıdır; veri dondurulmadan yazılan rakamlar eskir.
9. **Öğrenciye veli gibi hitap** (doğrulandı, eval). Belirti: öğrenci
   hesabında "çocuğunuzla konuşun". Düzeltme: rol bazlı hitap kuralları ve
   eval'de yasak ifade kontrolü.

10b. **Eval eski kodla koşuyordu** (doğrulandı, süreç dersi). Belirti:
   düzeltmelerden sonra eval aynı hataları (z2, m1) tekrarladı. Kök neden:
   sunucu `--reload` olmadan ve düzeltmelerden önce başlatılmıştı, yani
   eval eski kodu ölçtü. Düzeltme: sunucu yeniden başlatıldı. Ders: bir
   eval sonucu yalnızca, ölçülen sunucunun güncel kodu çalıştırdığı
   biliniyorsa anlamlıdır.

## 11. Eval sonucu (dondurulmuş)

Son canlı koşu: **59 / 65** (model `claude-sonnet-4-5-20250929`, yargıç
açık; rapor `eval/report.md`, cevap metinleri `eval/answers.md`). Kalan
altı madde:

- **d1** (yanlış alarm, doğrulandı): yargı, sayımların satırlarda
  olmadığını söyledi; oysa cevaptaki sayılar veritabanıyla birebir aynı
  (Ali 14 = 8 mazeretsiz + 6 mazeretli, Zeynep 13 = 7 + 6, Mehmet 9 = 6 + 3,
  Kerem 9 = 4 + 5). Yargıç yalnızca ilk satırları görmüştü.
- **c4** (küçük model hatası, bilinen sınırlama): "73-82 bandında"
  cümlesinde Matematik'in 73,98 değeri "73" diye kesilmişti (yuvarlanınca
  74). Sayı denetleyicisi bunu doğru yakaladı; zararsız ama tutarsız.
- **z2** (gerçek hata, düzeltildi): göreli tarihli soruda ("dün", "bu hafta") veri
  varken asistan "veri yok" dedi. Kök neden: modelin bugünün tarihinden
  haberi yok ve sonuç 50 satırda kesilmişti. Düzeltme: bağlama referans
  tarih ve veri aralığı eklenir; kesilen sonuçta "veri yok" denmez.
- **m1** (gerçek hata, düzeltildi): iki dersi birden sorulan takip sorusunda yalnızca
  biri cevaplandı. Düzeltme: prompt kuralı (sorulan her konuyu yanıtla).
- **m5** (bilinen sınırlama): duygusal konuda notlar gösterildikten sonra
  model nedensellik tahmini yürütebiliyor; prompt kuralı garanti değildir.
- **s3** (denetim fazla katıydı, düzeltildi): ilk cevapta "devamsızlık" kelimesi
  yasaklıydı, oysa asıl kural ilk cevapta veri kullanılmamasıdır (bu zaten
  "ilk turda sorgu yok" kontrolüyle sağlanıyor). Kural, ilk cevapta rakam
  ve nedensellik yasağına daraltılır.

Eval bu noktadan sonra dondurulmuştur: tekrar çalıştırmak ek token ve
zaman maliyetidir; yukarıdaki maddeler rapora gizlenmeden yazılmıştır.

**Yeniden koşu:** düzeltmeler uygulanıp sunucu yeniden başlatıldıktan
sonra `z2`, `m1`, `s3` (ve `d1`) yeniden koşuldu ve geçti. Tam eval bu
düzeltmelerden sonra tekrar çalıştırılmadı; prompt değişiklikleri diğer
maddeleri etkilemiş olabilir (ölçülmedi). Açık kalanlar: `m5` (nedensellik
tahmini, bilinen sınırlama) ve `c4` (küçük yuvarlama tutarsızlığı).

## 12. Değişen ve gelişen teknolojiler

| Teknoloji | Ne değişti | Neden |
|---|---|---|
| Araç kullanan asistan (tool use) | SQL çevirici yerine model `run_sql` aracını çağırır, sonucu görür, cevabı doğal dille yazar; son 6 mesaj bağlamdır | Takip soruları, dürüst cevap, doğal ton |
| Fonksiyon izin listesi (`sqlglot`) | Yasak listesi yerine izin listesi | Modelin SQL'iyle yetki yükseltme açığı kapandı |
| `SECURITY DEFINER` fonksiyonlar | `student_rank`, `class_teacher`: kimlik oturumdan okunur | Veli çocuğunun sırasını görür, başkasının verisi açılmaz |
| Sohbet arayüzü (Streamlit) | `st.chat_message`, `st.chat_input`; tablo ve SQL açılır bölümlerde | Konuşma deneyimi |
| Eval seti + LLM yargıç | 65 soru; `truth_sql` ile gerçek değer, yargıçla ton ve dürüstlük | Asistan kalitesi tekrarlanabilir ölçülür |
| Dondurulmuş mock veri | `database/mock_data.json`, mutlak tarihler | Rakamlar ve testler tekrarlanabilir |
| Yapılandırma ile politika | `PASS_GRADE`, `REFERENCE_DATE`, `SHOW_SQL`, `CORS_ORIGINS` | Politika kodda değil, ayarda |
| Giriş sertleştirme | Tek tip 401, kullanıcı başına hız sınırı, izinli CORS adresleri | Kaba kuvvet ve kullanıcı adı sızıntısı |
