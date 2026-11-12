# Hafta 2 — FastAPI İskeleti ve Kimlik Doğrulama

**Proje:** Akıllı Okul Bilgi Sistemi (Smart School Information System)
**Önceki durum:** Hafta 1'in PostgreSQL + Row-Level Security kurulumu (`week2/week-02/`, Hafta 1'in kopyası)

---

## 1. Bu haftanın amacı

Hafta 1'de, veritabanının kendisinin rol bazlı erişimi doğru uyguladığını
kanıtladık — ama hiçbir kullanıcı giriş yapamıyordu, "bu isteği kim
atıyor" bilgisi hiçbir yerde yoktu. Bu hafta, FastAPI + JWT ile kimlik
doğrulama ekliyoruz, ve en önemlisi: **giriş yapan kullanıcının bağlamını
(rol, sınıf, öğrenci kimliği), her istekte PostgreSQL oturumuna bildiren
bir mekanizma** kuruyoruz. Bu sayede Hafta 1'in veritabanı seviyesindeki
kanıtı, artık gerçek bir API isteğinden geçerek de doğrulanmış olacak.

## 2. Teslim edilecekler

- [ ] `backend/app/main.py` — FastAPI app, router kayıtları, `/health`
- [ ] `backend/app/core/security.py` — `verify_password`, `get_password_hash`,
      `create_access_token`, `decode_access_token`
- [ ] `backend/app/api/auth.py` — `POST /auth/login`; JWT payload artık
      `sub`, `role`, `related_class`, `related_id` taşıyor
- [ ] `backend/app/api/dependencies.py`:
  - `get_current_user()` — token doğrulama
  - `get_db_with_context()` — **bu haftanın en önemli parçası**: ayrı,
    kısıtlı yetkili bir `school_app` veritabanı bağlantısı açar, aynı
    transaction içinde `SET LOCAL app.role`, `app.class`, `app.student_id`
    çalıştırır, sonra bu session'ı endpoint'e verir
- [ ] `config/settings.py` — `APP_DATABASE_URL` (superuser değil,
      `school_app` rolüyle bağlanan ayrı bir bağlantı dizesi)
- [ ] `backend/app/api/debug.py` — **geçici** `GET /debug/students`
      endpoint'i, yalnızca bağlam zincirinin uçtan uca çalıştığını
      kanıtlamak için (Hafta 4'te LLM gelince kaldırılacak)
- [ ] Hafta 1'in seed verisindeki düz metin şifrelerin bcrypt hash'e
      çevrilmesi
- [ ] `requirements.txt` güncellemesi: `fastapi`, `uvicorn[standard]`,
      `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`

## 3. Kapsam DIŞI (bilerek ertelenen)

- Doğal dil → SQL, LLM entegrasyonu → Hafta 4
- `/debug/students` dışında gerçek veri döndüren bir endpoint → Hafta 4
- Streamlit arayüzü → Hafta 6
- Rate limiting, CORS sertleştirme → ileride, kapsam netleşince

## 4. Kabul kriterleri

1. `uvicorn backend.app.main:app --reload` hatasız başlar, `/docs`
   (Swagger UI) erişilebilir.
2. 4 rolün (`principal`, `teacher1`, `parent1`, `student1`) her biri
   doğru şifreyle `POST /auth/login`'e istek attığında `200` ve geçerli
   bir JWT döner.
3. Yanlış şifreyle istek `401 Unauthorized` döner.
4. `GET /debug/students`'a geçerli bir token ile istek atıldığında,
   dönen satır sayısı Hafta 1'in `test_rls.py` sonuçlarıyla birebir
   eşleşir: `principal` → 12, `teacher1` → 4, `parent1` → 1,
   `student1` → 1.
5. `school_app` veritabanı rolü **superuser değildir** — bu, RLS'in
   gerçekten devrede olduğunun ön koşuludur (Hafta 1'in notlarına bakın:
   superuser RLS'i otomatik atlar).
6. `APP_DATABASE_URL` yalnızca `.env`'den okunur, kodda sabit değer
   olarak yer almaz.

## 5. Sunumdaki demo akışı

1. `POST /auth/login` ile `teacher1` olarak giriş yapılır, token alınır.
2. `GET /debug/students` bu token ile çağrılır — yalnızca **4** satır
   (9-A sınıfı) döndüğü gösterilir.
3. Aynı istek `principal` token'ıyla tekrarlanır — bu sefer **12** satır
   döndüğü gösterilir.
4. Bu, Hafta 1'de yalnızca `psql` ile elle gösterdiğimiz şeyin, artık
   gerçek bir HTTP isteği üzerinden, kimlik doğrulamalı olarak da aynen
   çalıştığının kanıtıdır.

## 6. Notlar / gerekçeler

- `get_db_with_context()`'in ayrı bir veritabanı bağlantısı (`school_app`)
  kullanması bilinçli: `init_db.py`/`seed_mock.py` gibi yönetimsel
  script'ler superuser ile çalışmaya devam ediyor (tablo oluşturma, RLS
  politikası tanımlama gibi işler için superuser yetkisi gerekiyor), ama
  **gerçek uygulama trafiği hiçbir zaman superuser bağlantısı
  kullanmamalı** — aksi halde RLS sessizce atlanır.
- `/debug/students` endpoint'inin ayrı bir dosyada (`debug.py`) tutulması
  bilinçli — Hafta 4'te bu geçici kodu silmek, gerçek sorgu mantığına
  hiç dokunmadan tek bir dosyayı kaldırmak kadar basit olacak.
- Bu hafta sonunda, Hafta 3'ün orijinal planı (bir `RuleEngine` sınıfı
  inşa etmek) geçersiz kaldı — bu iş artık PostgreSQL'in kendisi
  tarafından, veritabanı seviyesinde yapılıyor. Hafta 3'ün kapsamı
  yeniden değerlendirilecek.
