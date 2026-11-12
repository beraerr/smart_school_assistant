# Hafta 12 — Canlıya Alma ve Kapanış

## Özet
Stajın son haftasında sistemi internete açtık: https://smartschoolassistant.com, Contabo VPS üzerinde Docker Compose ile çalışıyor ve dışarıya yalnızca Caddy açık. Asistana risk sayfasıyla aynı kodu çağıran bir `get_risk` aracı ve daha sıkı sayı kuralları ekledik. Öğretmenin "sınıfım okulda kaçıncı?" sorusu için `class_rank` fonksiyonunu yazdık. Canlıda bir listeleme sorusunda modelin bir öğrenciyi sessizce atladığını gördük ve bunu yapısal olarak kapattık: liste isteklerinde model satır görmüyor, tablonun tamamını uygulama çiziyor.

Haftanın ikinci yarısı kapanışa gitti: kod temizlendi, sessiz hata yutmaları kaldırıldı, AI araç dosyaları silindi, iki dilli README yazıldı ve proje GitHub'a hazırlandı. Arayüzde not tablosu, iki dilli risk gerekçesi, haftalık raporlar sayfası, araştırma sayfasının özet kartları ve telefon görünümü düzeltildi.

## 1. Canlıya alma

### 1.1 Kurulum
| Servis | Görevi |
|---|---|
| `db` | postgres:18.6; veri `smartschool_db_data` volume'ünde; dışa kapalı |
| `init` | Tek seferlik (`init` profili): `init_db.py` → `bootstrap_roles.py` → `enable_rls.py` → `seed_mock.py` |
| `backend` | uvicorn; sağlık kontrollü; dışa kapalı |
| `frontend` | Streamlit; `API_BASE_URL=http://backend:8000`; dışa kapalı |
| `caddy` | caddy:2.10.0; 80/443; otomatik sertifika; `.env` almaz |

- **Tek imaj:** `smartschool-app:week12` (`python:3.14.9-slim`), bağımlılıklar `requirements.lock.txt`'ten birebir, root olmayan kullanıcı. Backend ve frontend aynı imajı kullanıyor.
- **Sürümler yerel test ortamıyla aynı:** Python 3.14.9, PostgreSQL 18. Cursor `postgres:16` yazmıştı; yerel testler PG 18'de koştuğu için `postgres:18.6` yapıldı (Hafta 11'deki ortam farkı hatasının dersi).
- **`.env` yalnızca sunucuda:** imaja girmiyor; parolalar ve `SECRET_KEY` sunucu için yeniden üretildi; `DEMO_TODAY=2026-11-09`.
- **Alan adı:** `smartschoolassistant.com` (Cloudflare Registrar ve DNS). Kök alan ve `www` için sertifika alındı; `www` kök alana yönleniyor.
- **Ayrı Postgres:** Sunucudaki n8n yığınına ve onun veritabanına dokunulmadı.
- **Rol ve politikalar kodda:** `school_app` rolü ve izin veren politikalar yerel veritabanında elle kurulmuştu. Deploy hazırlığında bu fark edildi; `bootstrap_roles.py` yazıldı ve `database/ref/sema.sql` ile eşitlik testi eklendi. Böylece RLS sıfırdan kurulabiliyor.

### 1.2 Güncelleme akışı
1. Yerelde tam test koşusu.
2. `rsync` (`.env`, `.venv`, ham veri, `docs/sunumlar` hariç).
3. Dosya bazında md5 karşılaştırması; sıralama `LC_ALL=C`; çıktı `AYNI` olmalı.
4. Sunucuda `docker compose build` ve `docker compose up -d backend frontend`.
5. Yalnız veritabanı fonksiyonu değiştiyse: `docker compose exec backend python database/enable_rls.py`.

`init` yeniden çalıştırılmıyor; `seed_mock` tabloları boşaltıyor.

## 2. Asistan

### 2.1 `get_risk`
Risk sayfasının `read_risk` fonksiyonunu aynı oturum ve RLS bağlamıyla çağırıyor; hesap kopyalanmadı. Müdür tüm okulu ya da bir sınıfı, sınıf öğretmeni yalnız kendi sınıfını görüyor. Başka bir sınıf istenince `forbidden` dönüyor ve `get_risk_denied` loglanıyor. Veli ve öğrencide araç listede yok; doğrudan çağrı reddediliyor.

### 2.2 Sayı kuralları
Sayılar sonuçtan aynen yazılıyor: aralık, yuvarlama ya da "yaklaşık" yok. Yeni bir sayı istenirse yeni sorgu yapılıyor. "Bu dönem" dönem başından bugüne; veri aralığı darsa cevabın başında söyleniyor. Türkçede ondalık virgül. Canlı denemede model bir müdür sorusuna "71-74 aralığında" yazdı; dayanak denetimi `71`'i yakaladı. Düzeltme talimatta yapıldı, denetim gevşetilmedi.

### 2.3 Liste modu
Canlıda "Sınıfımdaki öğrencilerin notlarını listele" sorusunda sorgu 60 satır döndü, modele ilk 50'si gitti. Cevap "6 öğrenciniz" dedi ama 5 öğrenci yazdı; Zeynep Demir yoktu. Dayanak denetimi bunu yakalayamadı, çünkü yazılan her sayı gerçekten sonuçtaydı; sorun eksik olanlardı.

Çözüm talimat değil, yapı: `run_sql` aracına `presentation` seçeneği eklendi. Liste isteklerinde model `table` gönderiyor ve satır yerine yalnızca tüm sonuçtan hesaplanan bir özet alıyor: `row_count`, `columns`, `distinct_counts` (bu modda 200 satır sınırı yok) ve `date_range`. Tablonun tamamını uygulama cevabın altında çiziyor. Model satır görmediği için satır atlayamıyor ya da değiştiremiyor; 32 kişilik bir sınıf da 6 kişilik bir sınıfla aynı kısa cevabı alıyor.

### 2.4 `class_rank`
Sınıf öğretmeni tablolarda yalnız kendi sınıfını görüyor; düz SQL ile yazılan bir "okul ortalaması" aslında sınıf ortalaması olurdu. `class_rank`, `student_rank`'in sınıflar için karşılığı: `SECURITY DEFINER`, sabit `search_path`, sınıfı parametreden değil `app.class` oturum ayarından okuyor, yalnız `teacher` rolünde tek satır döndürüyor (sıra, sınıf sayısı, sınıf ortalaması, okul ortalaması) ve zaman kapısını kendi içinde taşıyor. Başka sınıfın adı ve ortalaması dönmüyor. Cevapta bir cümleyle sınıfların farklı düzeylerde olduğu ve sıranın öğretmen başarısını ölçmediği söyleniyor.

### 2.5 Örnek sorular
Öğretmene "Sınıfımdaki öğrencilerin notlarını listele." ve "Sınıfım okulda kaçıncı?", müdüre "Okuldaki tüm öğrencilerin notlarını listele." eklendi (EN karşılıklarıyla).

## 3. Arayüz
- **Not tablosu:** Pivot ismi tablonun indeksine koyuyordu ve indeks gizli olduğu için isimler görünmüyordu; her tarih ayrı satır olduğundan tablo seyrekti. Şimdi her öğrenci bir satır, her sınav bir sütun. Bir derste herkesin sınav tarihleri aynıysa başlıkta tarih yazıyor (`Fizik 29.09`), değilse sıra numarası ve açıklama notu. Hesaplanmış sayı yok. Tablo cevabın hemen altında; "Sorguyu göster" yalnız SQL'i taşıyor.
- **Risk gerekçesi:** EN sayfada da Türkçe geliyordu ve her satır "Bu bir karar değildir." ile bitiyordu. `assess_risk` artık `lang` alıyor (geçersiz dilde hata), `/risk` ucu dili parametre olarak alıyor, eşitlik etiketi `(eşit)` / `(tie)`. Karar cümlesi kaldırıldı; açıklama sayfanın üstünde zaten var.
- **Haftalık raporlar sayfası** (`?sayfa=haftalik`): girişsiz; her haftanın sunumu slayt olarak ve PDF olarak. Slaytlar `scripts/haftalik_slaytlar.py` ile üretiliyor.
- **Giriş kartları:** "Veri bilimi çalışması" ve "Haftalık raporlar".
- **Araştırma sayfası:** Özet kartları tek bir ızgarada ve eşit boyda; üçüncü kart artık veri ölçeği (öğrenci-ders kaydı ve ders-dönem sayısı, paketten). "Bilmiyoruz" kartı ve okuma süresi etiketi kaldırıldı.
- **Telefon görünümü:** Seçim kutuları yazı kabul ettiği için telefonda klavye açıyordu; dokunmayla seçilen kontrollere çevrildi. Telefonda "demo verisi" çipi gizlendi; üst bar sığıyor, kenar çubuğu oku üst barla çakışmıyor.

## 4. Temizlik ve GitHub hazırlığı
- `backend/app/main.py`: açılıştaki şema özeti hatası `except Exception: pass` ile yutuluyordu; artık uyarı olarak loglanıyor (özet ilk sorguda yeniden kuruluyor).
- `data_science/oulad/explain.py`: SHAP için 3 kurulum × 3 çağrı şekli sessizce deneniyordu. shap 0.54.1 ile hangi yolun çalıştığı küçük bir sondayla doğrulandı ve tek yola indirildi; beklenmeyen biçimde hata veriyor. İki yeni test.
- `eval/run_eval.py`: başarısız kanıt sorgusu sessizce atlanıyordu; artık hata tipi ve SQL ile stderr'e yazılıyor.
- Kullanılmayan import'lar ve değişkenler temizlendi; `database/__init__.py` docstring'i güncellendi; `docs/architecture.md` (Hafta 1'den kalma) silindi.
- `.cursor/`, `*.mdc` ve prompt dosyaları bütün hafta klasörlerinden silindi; `docs/metin_yamasi.json`'daki araç ifadeleri nötr dile çevrildi.
- `.gitignore` yeniden yazıldı. Ham ve işlenmiş veri repoda yok (`studentVle.csv` 453 MB); README indirme adımlarını veriyor.
- README İngilizce ve Türkçe: canlı demo ve bağlantılar, özellikler, veliler için bölüm, mimari ve soru akışı diyagramları, güvenlik modeli, dikkat bayrağı, araştırma özeti, kurulum, demo hesapları, testler, deploy, sınırlamalar, veri kaynakları. Ekran görüntüleri ilgili bölümlerde (`docs/img/`, TR ve EN).
- Bütün haftaların WEEK dokümanları `docs/haftalar/` altında (21 dosya; Hafta 6 EN yok). Repo dışındaki `../week10` dosyasını okuyan test artık buradan okuyor.

## 5. Kararlar
| Karar | Gerekçe |
|---|---|
| Deploy, bekleyen güvenlik maddelerinden önce yapıldı | Kullanıcı kararı; tek şart `.env`'in imaja girmemesi |
| Demo herkese açık, her rol dahil | Tanıtım amaçlı; veri tamamen sentetik |
| `DEMO_TODAY` canlıda sabit | Mock kapısı sorunu (hata 2) çözülene kadar demo tutarlı kalsın |
| Liste isteklerinde model satır görmez | Eksik ya da değişmiş satır yazılamasın; yapısal güvence |
| Öğretmene sınıf sırası | Müdür sınıfları zaten kıyaslayabiliyor; sıra yalnız kendi sınıfı için, düzey uyarısıyla |
| Risk gerekçesi istemcinin dilinde, dil zorunlu | Sessiz Türkçe geri dönüşü yok |
| Repoya yalnız week-12 | Haftalık ilerleme WEEK dokümanlarında ve haftalık sayfada |
| Belirtimler ve ön kayıt dosyaları repoda kalır | Kod ve testler bunlara bağlı; ön kayıt iddiasının kanıtı |

## 6. Hata kayıtları
| Hata | Kök neden | Düzeltme |
|---|---|---|
| Test ve uygulama farklı ortamda koşuyordu (Hafta 11'den) | Ortam belgelenmemişti; testler `week-11/.venv`, uygulama ortak `.venv` (fastapi 0.162/0.142, pillow 13.0/12.3) | Tek ortam, `requirements.lock.txt`; deploy'da da aynı sürümler |
| Mock kapısı uygulamanın gösterdiğini korumuyor | Kapı kümülatif riske, uygulama dönem penceresine bakıyor; 2027-04-15'te Zeynep uygulamada bayraksız | Geçici: `DEMO_TODAY=2026-11-09`; kalıcı düzeltme açık |
| `_sor` ad çakışması | Cursor `test_assistant.py`'ye aynı adlı yardımcı ekledi; 3 kimlik testi `TypeError` (3 failed / 1289 passed) | Yeni kural: aynı adla yardımcı yok |
| Haftalık sayfa testlerinde kör assert | Sayma yardımcısı proto adı `imgs` ile her koşulda 0 sayıyordu; yeniden çalıştırma gerçek asset klasörünü okudu (`assert 21 == 3`) | `at.get("image")`, kök `HAFTALIK_DIZIN` ortam değişkeni |
| Rol, GRANT ve temel politikalar kodda yoktu | Yerel veritabanında elle kurulmuştu | `bootstrap_roles.py` + `sema.sql` eşitlik testi |
| Asistan aralık yazdı | Yuvarlanmış aralık; `71` dayanaksız | Talimat; denetim gevşetilmedi |
| Kartlarda düğme açıklamanın üstüne biniyordu | Eski `arastirma_ac` stil kuralları kartın içinde de uygulanıyordu | Kurallar temizlendi |
| Sunucu dosyaları eski kaldı | Test + rsync `&&` zinciri sessizce durdu | Her komut onay kelimesiyle bitiyor; md5 karşılaştırması |
| md5 toplamları farklı, dosyalar aynı | `sort` iki makinede farklı yerel ayarla sıraladı | `LC_ALL=C` ve dosya bazında `diff` |
| Not tablosunda isimler yok | Pivot ismi gizli indekse koyuyordu | İsim sütun; sınav başına sütun |
| Listede bir öğrenci eksik | Model 60 satırın 50'sini gördü ve gördüğünü listeledi | Liste modu |
| Risk gerekçesi EN sayfada Türkçe | Gerekçe backend'de tek dilde kuruluyordu | `lang` zorunlu; `/risk?lang=` |
| Risk dili değişikliğinden sonra 10 test düştü | `assess_risk`'i çağıran iki yer (`test_mock_uret.py`, `scripts/mock_uret.py`) aramada kaçtı; grep çıktısı kesilmişti | İki çağrı düzeltildi; arama çıktısı kesilmeden okundu |
| Örnek soru testi düştü | Yeni sorular kaynağa eklendi, testteki beklenen liste güncellenmedi | Beklenen liste güncellendi; karşılaştırma birebir kaldı |
| Temiz klonda bir test düşüyor | Test `../week10/WEEK_10.md`'yi okuyordu | Kaynak `docs/haftalar`'a alındı |
| Özet kartları farklı boyda | Kartlar ayrı Streamlit sütunlarındaydı | Tek CSS ızgarası |
| Telefonda klavye açılıyordu | Seçim kutuları arama metni kabul ediyor | Dokunmayla seçilen kontroller |

**Bilinen sınır:** UCI notebook görselleri TR ve EN sürümlerde birebir aynı (md5 eşit); TR'de etiketler İngilizce.

## 7. Bilinen sınırlar
- İstek ve giriş sayaçları süreç belleğinde: worker'lar arasında paylaşılmıyor, yeniden başlatmada sıfırlanıyor.
- Demo herkese açık; herkes müdür dahil her rolle girebiliyor.
- Asistan soruyu, şema özetini ve sorgu sonuçlarını harici bir API'ye gönderiyor; gerçek veriyle kullanmadan önce KVKK değerlendirmesi gerekir.
- Dikkat bayrağı yalnız not ve devamsızlığa bakıyor; araştırmanın en güçlü sinyali olan teslim edilmeyen ödev okul verisinde yok.
- Frontend servisinin sağlık kontrolü yok.

## 8. Çıktılar ve doğrulama
- **Sunucu:** `grades|attendance|pg_policies` = `1440|6444|5`; `init` rolü, RLS'i ve politikaları kurdu; servisler ayakta, backend ve db healthy; kök alan ve `www` için sertifika alındı.
- **Testler:** Hafta başında tam koşu 1.335 passed. Liste modu, `class_rank` ve risk dili değişikliklerinden sonraki son tam koşu **1.366 passed** (mobil arayüz düzeltmesinden önce).
- **Paket:** `arastirma.json` birebir aynı (md5 `27f5279b8b574814c2682d070603798e`).
- **Repo:** yasaklı dosya 0, `sk-ant-` izi 0, 5 MB üstü dosya yok, toplam 63 MB.

```
.venv/bin/python -m pytest -q
docker compose build && docker compose up -d backend frontend
docker compose exec backend python database/enable_rls.py
```

## 9. Açık konular
- API anahtarının yenilenmesi ve Anthropic konsolunda harcama limiti.
- Giriş sayacı, soru uzunluğu sınırı, log maskeleme; `seed_mock` demo parolalarını loga basıyor.
- Mock üretim kapısının dönem penceresiyle sınanması (hata 2).
- `database/ref/sema.sql`'in `class_rank` ile yeniden üretilmesi.
- İmaj boyutu: kilit dosyası jupyter ve shap yığınını da kuruyor; çalışma zamanı bağımlılıkları ayrılmalı.
- Sunucuda n8n (5678) ve render-service (8000) dışa açık HTTP; 70 bekleyen güncelleme.
- Çizim kodu pakete (UCI U1–U6, OULAD O1–O4), TR biçimleyici, UCI TR görselleri.
- Hafta 6 EN sunumu yok.

## 10. Gelecek çalışmalar
- **Ödev teslim kaydı:** araştırmada modelin en güçlü işareti; okul verisine eklenirse dikkat bayrağı bunu kullanabilir.
- **Veli için kıyassız bayrak:** çocuğun kendi geçmişine göre, sınıf kıyası olmadan.
- **Alt grup denetimi:** bayrağın farklı öğrenci grupları için aynı hassasiyette çalıştığının kontrolü.
- **Hoca etkisi:** iki veri setinde de yok; ölçmek için gereken veri ve tasarım.
