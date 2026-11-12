# Hafta 6 — Streamlit Arayüzü

**Proje:** Akıllı Okul Bilgi Sistemi
**Önceki durum:** Hafta 5'in `/query` akışı (`week06/week-06/`, Hafta 5'in kopyası)

---

## 1. Bu haftanın amacı

Hafta 1-5 boyunca her şey `curl` ile test edildi. Bu hafta gerçek bir
kullanıcının (öğretmen, veli, öğrenci, müdür) kullanabileceği bir arayüz
ekliyoruz. Bu yeni bir backend özelliği değil: `/auth/login` ve
`/query`'yi çağıran, ayrı bir `frontend/` klasöründe yaşayan bir
Streamlit uygulaması. Backend'de yalnızca küçük bir ayar eklenir (`SHOW_SQL`); arayüz erişim
kuralı bilmez ve veritabanına dokunmaz; yalnızca backend'in döndürdüğü
sonucu, açıklamayı ve üretilen SQL'i gösterir.

## 2. Teslim edilecekler

- [ ] `frontend/app.py` — token yoksa giriş ekranı, varsa soru ekranı
- [ ] `frontend/api_client.py` — `login()` ve `query()`; `requests` ile
      çağırır, 400/401/429/503 ve bağlantı hatalarını yakalar; backend
      adresi `API_BASE_URL` ortam değişkeninden okunur (varsayılan
      `http://127.0.0.1:8000`)
- [ ] `frontend/i18n.py` — TR/EN metin sözlüğü; seçilen dil isteğin `lang`
      alanı olarak da gönderilir
- [ ] Sonuç tablosu (`st.dataframe`) ve açıklama; sohbet yanıtı da
      gösterilir; sonuçta `name`, `subject`, `grade` sütunları varsa
      "Derslere göre sütunlar" seçeneği (pandas `pivot_table`)
- [ ] `frontend/tests/test_api_client.py` — `requests` mock'lanarak
      yazılan testler
- [ ] SQL gösterimi: backend ayarı `SHOW_SQL` (varsayılan `true`) açıkken
      `/query` yanıtına, yalnızca çalıştırılan sorgular için `sql` alanı
      eklenir; arayüz bunu "Üretilen SQL" açılır bölümünde gösterir
- [ ] Sıralama: veritabanında `student_rank(kapsam, ders)` (`SECURITY
      DEFINER`); veli/öğrenci çocuğunun sınıf ya da okul sırasını,
      isteğe bağlı ders bazında görür; çocuğun kimliği oturumdan
      okunur, başka öğrencinin notu/adı dönmez; model SQL'i yine kendisi
      yazar (`SELECT * FROM student_rank('class', NULL)`)
- [ ] `requirements.txt` — `streamlit`, `requests`, `pandas`

## 3. Kapsam DIŞI

- PDF dışa aktarma, grafikler, yönetici paneli → sonraki haftalar
- Özel tema/marka çalışması
- `SHOW_SQL` ayarı dışında backend'de herhangi bir değişiklik

## 4. Kabul kriterleri

1. `streamlit run frontend/app.py` hatasız açılır.
2. Doğru kimlik bilgisi soru ekranını açar, yanlış kimlik bilgisi hata
   mesajı gösterir; çökme olmaz.
3. Soru sonucu tablo, açıklama ve üretilen SQL olarak gösterilir;
   sohbet mesajına verilen yanıt da gösterilir.
4. Dil seçici tüm etiketleri TR/EN arasında değiştirir.
5. 401 (giriş ekranına dönüş), 429 (bekleme süresi), 503 (yoğunluk
   mesajı), 400 ve backend'e ulaşılamama durumlarında arayüz çökmez.
6. `frontend/` içinde `sqlalchemy`, `backend` ya da veritabanı
   import'u yoktur.
7. Testler çalışan backend ve API anahtarı olmadan geçer.
8. Kodda araç/model öz-referansı yoktur.

## 5. Demo akışı

1. Yanlış şifreyle giriş: hata mesajı.
2. `teacher1` ile giriş, "Sınıfımdaki öğrencilerin notları" sorusu:
   tablo + açıklama; "Derslere göre sütunlar" seçeneği açılır.
3. Dil EN'e çevrilir; etiketler ve açıklama İngilizceye döner.
4. `parent1` ile aynı soru: yalnızca kendi çocuğunun kayıtları.

## 6. Notlar

- Hafta 4-5'te üretilen SQL yanıta konmuyordu. Bu hafta bilinçli olarak
  değiştirildi: projenin amaçlarından biri sistemin nasıl çalıştığını
  göstermek ve üretilen SQL bunun en açık kanıtı. SQL yalnızca
  çalıştırılan sorgular için gösterilir (sohbet, ret ve doğrulamadan
  geçemeyen sorgularda `sql` alanı yoktur). Erişim kontrolü etkilenmez,
  çünkü satırları RLS filtreler. `SHOW_SQL=false` ile kapatılabilir; gerçek
  dağıtımda (Hafta 12) bu karar yeniden değerlendirilir.

- Arayüz, backend'in döndürdüğü hata mesajlarını yorumlamadan gösterir
  (iç ayrıntı zaten backend'de gizlenir).
- Pivot görünümü yalnızca gösterimdir; erişim kontrolü ve SQL
  değişmez.
- Streamlit script'i `frontend/` klasörünü kök alır; bu yüzden
  `app.py` içinde `from api_client import ...` kullanılır.

- Sıralama: Hafta 5'te veli/öğrenci için karşılaştırma soruları gizlilik
  gerekçesiyle reddediliyordu. Bu, ürün için yetersiz kaldı: veli
  çocuğunun sınıfta, okulda ve derslerde kaçıncı olduğunu görebilmeli.
  Çözüm, RLS'i gevşetmek değil, kontrollü bir fonksiyon: `student_rank`
  yalnızca oturumdaki öğrencinin sırasını, toplam sayıyı, öğrencinin ve
  kapsamın ortalamasını döndürür. Sıra, öğrenci ortalamasına (ilgili
  kapsamdaki notların ortalaması) göre `RANK()` ile hesaplanır; eşitlikte
  aynı sıra verilir. Diğer öğrencilerin tekil verisini isteyen sorular
  ("sınıfın birincisi kim?") hâlâ reddedilir.

## 7. Canlı testte bulunan hatalar ve düzeltmeleri

Bu bölüm, haftanın gerçek zamanlı hata kayıtlarıdır: her kayıt belirtiyi,
kök nedeni, düzeltmeyi ve durumu içerir.

1. **Boş soru gönderiliyordu** (doğrulandı). Belirti: "Sor"a basınca API
   400 dönüyordu. Kök neden: soru kutusu ve buton ayrı bileşendi,
   metin butonla birlikte gitmiyordu. Düzeltme: ikisi tek bir `st.form`
   içine alındı.
2. **Yanıltıcı hata mesajı** (doğrulandı, test). Belirti: sunucu hata
   verince arayüz "Sunucuya bağlanılamadı" yazıyordu. Kök neden:
   `api_client` 5xx yanıtlarını gerçek bağlantı hatasıyla aynı mesaja
   çeviriyordu; bu yüzden ilk tanı yanlış yöne (zaman aşımı, API anahtarı)
   gitti, asıl neden backend traceback'inde çıktı. Düzeltme: 5xx ayrı
   hata türü ve ayrı mesaj oldu.
3. **Modelin uydurduğu ayar** (doğrulandı, canlı). Belirti: "Ben kimin
   velisiyim?" sorusu 500 döndü. Kök neden: model var olmayan
   `current_setting('app.user_id')` ayarını uydurdu; SQL doğrulamadan
   geçti, veritabanında patladı, hata yakalanmadı. Düzeltme: prompt
   kuralları (kendi sorularında filtre yazma; `current_setting` ve
   `set_config` kullanma) ve çalıştırma hatasında en fazla bir yeniden
   deneme, ardından ayrıntısız 400. Bu olay, Hafta 7'deki fonksiyon izin
   listesinin gerekçesini de canlı olarak gösterdi.
4. **Pivotta sessiz ortalama** (doğrulanacak). Belirti: "Derslere göre
   sütunlar" seçilince farklı tarihlerin notları tek hücrede birleşebilir.
   Kök neden: `pivot_table` aynı öğrenci-ders çiftini sessizce ortalar.
   Düzeltme: `index=[name, date]`, `aggfunc=first`, tekrar eden satırda
   uyarı.
5. **Veli sıralama sorusu cevapsız** (uygulanacak). Belirti: "Ali sınıfta
   kaçıncı?" sorusu boş sonuç ve karşılaştırma açıklaması döndürüyordu.
   Kök neden: Hafta 5'teki ret, ürün için fazla kısıtlıydı. Düzeltme:
   `student_rank` fonksiyonu (bkz. teslim edilecekler ve notlar).
6. **Karar değişikliği: SQL gösterimi** (doğrulandı, canlı). Hafta 4-5'te
   SQL yanıta konmuyordu; projenin amaçlarından biri çalışabilirliği
   göstermek olduğu için `SHOW_SQL` ayarıyla (varsayılan açık)
   gösterilmeye başlandı.

Durumu "doğrulanacak" ya da "uygulanacak" olan kayıtlar, ilgili
düzeltme canlıda doğrulandığında bu bölümde ve sunumdaki durum
etiketinde güncellenir.
