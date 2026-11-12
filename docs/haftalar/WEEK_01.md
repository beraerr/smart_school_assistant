# Hafta 1 — Problem Tanımı, Mimari ve Veri Modeli

**Proje:** Akıllı Okul Bilgi Sistemi (Smart School Information System)
**Kapsam:** 12 haftalık staj sunum programının 1. sürümü

---

## 1. Bu haftanın amacı

Projenin mimarisini ve veri modelini bu hafta kuruyoruz. Bu haftanın
sonunda **kod henüz API içermez** — yalnızca veritabanı şeması, mock veri
ve rol bazlı erişim kontrolünün temeli çalışır durumda olacak.

## 2. Mimari karar: neden en baştan PostgreSQL

Bu projenin temel gereksinimi, bir kullanıcının (öğretmen, veli, öğrenci,
müdür) yalnızca yetkisi dahilindeki veriye erişebilmesi. Bu kısıtlamayı
uygulama kodunda (her sorguya elle `WHERE` koşulu eklemek) değil,
**veritabanının kendisinde** uygulamayı tercih ediyoruz — PostgreSQL'in
"Row-Level Security" (RLS, satır seviyesi güvenlik) özelliğiyle.

RLS, bir kullanıcının oturumuna "bu kullanıcının rolü X, sınıfı Y" gibi
bir bağlam bildirildiğinde, veritabanının **her sorguda, sorgunun şekli
ne olursa olsun**, otomatik olarak yalnızca izin verilen satırları
döndürmesini sağlıyor. Bu özellik SQLite'ta yok, yalnızca PostgreSQL gibi
olgun veritabanı motorlarında var — bu yüzden projeye SQLite ile değil,
en baştan PostgreSQL ile başlıyoruz.

Bu hafta RLS politikaları kuruluyor ama henüz hiçbir uygulama kodu
(FastAPI, LLM) bunları kullanmıyor — yalnızca veritabanı seviyesinde,
bağımsız olarak doğru çalıştığını kanıtlıyoruz. API katmanı Hafta 2'de,
bu temelin üzerine inşa edilecek.

## 3. Teslim edilecekler

- [ ] PostgreSQL (Docker container, tek bir `postgres:16` imajı)
- [ ] `database/models/` altında 5 SQLAlchemy modeli: `User`, `Student`,
      `Teacher`, `Grade`, `Attendance`
- [ ] `database/init_db.py` — tabloları PostgreSQL'de oluşturan script
- [ ] `database/seed_mock.py` — en az 10 öğrenci, 2 öğretmen, 2 veli, 4
      kullanıcı rolü içeren mock veri
- [ ] `database/enable_rls.py` — `students`, `grades`, `attendance`
      tabloları için Row-Level Security politikaları:
  - `students`: `principal` → tüm satırlar; `teacher` → yalnızca
    `class_name` eşleşen satırlar; `parent`/`student` → yalnızca `id`
    eşleşen satır
  - `grades`/`attendance`: yalnızca RLS uygulanmış `students` tablosunda
    halihazırda görünür olan bir öğrenciye ait satırlar
- [ ] `backend/tests/test_rls.py` — RLS'in API katmanından bağımsız,
      doğrudan veritabanı seviyesinde doğru çalıştığını kanıtlayan testler
- [ ] Mimari diyagramı ve rol/yetki matrisi

## 4. Kapsam DIŞI (bilerek ertelenen)

- FastAPI / herhangi bir API katmanı → Hafta 2
- Kimlik doğrulama (JWT/bcrypt) → Hafta 2
- RLS'i uygulama koduna (SQLAlchemy oturumlarına) bağlamak → Hafta 2-4
- LLM entegrasyonu → Hafta 4
- Streamlit arayüzü → Hafta 6

## 5. Kabul kriterleri

1. `docker run ... postgres:16` ile veritabanı ayağa kalkar.
2. `python database/init_db.py` hatasız çalışır, 5 tablo PostgreSQL'de
   oluşur.
3. `python database/seed_mock.py` çalıştırıldığında veritabanında
   tutarlı, ilişkili (FK'ler doğru) örnek veri bulunur.
4. `python database/enable_rls.py` çalıştırıldığında 3 tablo için RLS
   etkinleşir ve politikalar tanımlanır.
5. `backend/tests/test_rls.py`'deki testler, oturum değişkenleri
   (`app.role`, `app.class`, `app.student_id`) değiştirildiğinde
   `students` tablosunun doğru satır sayısını döndürdüğünü kanıtlar
   (`teacher` → 4, `principal` → 12, `parent` → 1).
6. README, projenin ne yaptığını ve neden PostgreSQL + RLS ile
   başlandığını bir paragrafta açıklar.

## 6. Sunumdaki demo akışı

1. `docker run` ile PostgreSQL başlatılır.
2. `init_db.py` → `seed_mock.py` → `enable_rls.py` sırasıyla çalıştırılır.
3. `psql` ile doğrudan veritabanına bağlanılıp `SET LOCAL app.role =
   'teacher'; SET LOCAL app.class = '9-A';` ardından `SELECT COUNT(*)
   FROM students;` çalıştırılır — yalnızca **4** döndüğü canlı gösterilir.
4. Aynı bağlantıda `SET LOCAL app.role = 'principal';` ile tekrar
   denenir — bu sefer **12** döndüğü gösterilir.
5. Bu, hiçbir uygulama kodu (API, LLM) yazılmadan, yalnızca veritabanının
   kendisinin rol bazlı erişimi doğru uyguladığının kanıtıdır.

## 7. Notlar / gerekçeler

- RLS politikalarının bu kadar erken (API'den önce) kurulması bilinçli:
  güvenlik modelinin veritabanı seviyesinde, uygulama kodundan bağımsız
  olarak doğru çalıştığını kanıtlamak, üzerine inşa edilecek her şeyin
  (API, LLM entegrasyonu) bu sağlam temelden faydalanmasını sağlıyor.
- `requirements.txt`'te bu hafta yalnızca `sqlalchemy`, `python-dotenv`,
  `psycopg2-binary` yer alır; `fastapi`, `anthropic` gibi bağımlılıklar
  henüz eklenmez.
- Docker Compose değil, tek bir `docker run` komutu kullanılıyor —
  orkestrasyon (çoklu servis, ağ yapılandırması) daha sonraki bir
  haftanın konusu.
