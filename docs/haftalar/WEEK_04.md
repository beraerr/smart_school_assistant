# Hafta 4 — Doğal Dil → SQL

**Proje:** Akıllı Okul Bilgi Sistemi (Smart School Information System)
**Önceki durum:** Hafta 3'ün güvenli RLS bağlamı (`week04/week-04/`, Hafta 3'ün kopyası)

---

## 1. Bu haftanın amacı

Hafta 1-3'te veritabanı seviyesinde rol bazlı erişimi kurduk, bağlamı
API'ye taşıdık ve bu bağlamı enjeksiyona karşı güvenli hale getirdik.
Ama veri döndüren gerçek bir uç nokta yoktu; yalnızca geçici bir
`/debug/students` vardı.

Bu hafta ilk gerçek uç nokta geliyor: `POST /query`. Kullanıcı doğal
dilde soru sorar, Claude SQL üretir, SQL doğrulanır ve **olduğu gibi**,
RLS bağlamı altında çalıştırılır. Claude'un ürettiği SQL'i değiştirmiyor,
sarmalamıyor ve yeniden yazmıyoruz: hangi satırların döneceğine
veritabanının RLS politikaları karar veriyor.

## 2. Üç savunma katmanı

| Katman | Neyi durdurur | Örnek |
|---|---|---|
| Doğrulama (`sqlglot`) | Çalıştırılmaması gereken SQL | `DROP TABLE`, çoklu ifade, `users` |
| Veritabanı yetkisi (en az yetki) | Doğrulama atlansa bile hassas tablolara erişim | `school_app` ile `SELECT * FROM users` |
| RLS | Yetkisiz satırlar | Öğretmen `SELECT * FROM students` yazsa da 4 satır görür |

`users` tablosu şifre hash'leri içeriyor ve RLS'i yok. Bu yüzden yalnızca
doğrulamaya güvenmiyoruz: `school_app` rolünün `users` ve `teachers`
üzerinde hiçbir yetkisi yok, `students`, `grades`, `attendance`
üzerinde yalnızca `SELECT` yetkisi var.

## 3. Teslim edilecekler

- [ ] `database/enable_rls.py` güncellemesi: `school_app` için en az yetki
- [ ] `backend/app/services/llm_service.py` —
      `translate_question_to_sql(question, client=None) -> str`;
      `temperature=0`; şema ve kurallar prompt'ta; markdown kod bloğu
      temizleme; sahte client verilebilir
- [ ] `backend/app/core/sql_safety.py` — `validate_select_only(sql)`;
      `sqlglot` ile: tek ifade, SELECT, yalnızca `students`/`grades`/
      `attendance`; saf Python
- [ ] `backend/app/api/query.py` — `POST /query`; `get_db_with_context`
      oturumunda SQL olduğu gibi çalışır; 5 saniyelik `statement_timeout`;
      en fazla 500 satır; üretilen SQL yanıta konmaz, yalnızca loglanır;
      Anthropic 529 hatası 503 olur
- [ ] `config/settings.py` — `ANTHROPIC_API_KEY`, `LLM_MODEL`
- [ ] `requirements.txt` — `anthropic`, `sqlglot`
- [ ] `backend/app/api/debug.py` ve testleri kaldırılır; RLS bağlam
      testleri `/query` üzerinden çalışır

## 4. Kapsam DIŞI (bilerek ertelenen)

- Niyet analizi (sohbet mi veri sorgusu mu), açıklama metni → Hafta 5
- Rate limiting, yapılandırılmış loglama → Hafta 5
- Prompt iyileştirmeleri (isim araması, kimlik sütunları) → Hafta 5
- Streamlit arayüzü → Hafta 6

## 5. Kabul kriterleri

1. Geçerli token ile `POST /query` `200` ve sonuç listesi döner.
2. Aynı SQL (`SELECT * FROM students`) dört rolde sırasıyla `principal`
   12, `teacher` 4, `parent` 1, `student` 1 satır verir; toplama sorgusu
   (`SELECT COUNT(*) AS total FROM students`) aynı sayıları verir.
3. `users` veya `teachers` tablosuna erişen SQL `400` döner; ayrıca
   `school_app` ile doğrudan `SELECT * FROM users` veritabanı yetki
   hatası verir.
4. `DROP TABLE` ve çoklu ifade `400` ile reddedilir.
5. 5 saniyeyi aşan sorgu iptal edilir; en fazla 500 satır okunur.
6. Üretilen SQL yanıtta yer almaz.
7. Anthropic 529 hatası `503` ve anlaşılır bir mesajla döner.
8. `/debug/students` kaldırılmıştır; Hafta 2-3'ün RLS bağlam testleri
   `/query` üzerinden çalışır ve sonuçlar (4 / 12 / 1 / 1) değişmez.
9. Testlerin tamamı API anahtarı olmadan geçer.
10. Kodda araç veya model öz-referansı yoktur; `.gitignore` içinde
    `.env` bulunur.

## 6. Sunumdaki demo akışı

1. `teacher1` ile giriş yapılıp "Sınıfımdaki öğrenciler kim?" sorulur;
   yalnızca 9-A öğrencileri döner.
2. Aynı soru `principal` ile sorulur; 12 öğrenci döner.
3. Sunucu loğunda üretilen SQL gösterilir; yanıtta yer almadığı
   vurgulanır.
4. `users` tablosunu soran bir istek gösterilir: `400`; ardından
   veritabanı seviyesindeki yetki hatası gösterilir.

## 7. Notlar / gerekçeler

- Doğrulama yalnızca "bu SQL çalıştırılabilir mi" sorusuna bakar; "hangi
  satırlar görünür" sorusu veritabanının işidir. Bu ayrım sayesinde
  takma ad, JOIN, toplama ve alt sorgu gibi her SQL şekli aynı şekilde
  filtrelenir.
- RLS satırları filtreler ama bir sorgunun maliyetini sınırlamaz. Süre
  ve satır sınırları bu yüzden ayrı bir önlemdir.
- `client=None` parametresi ve `monkeypatch`, Claude'a bağımlı kodun
  Claude olmadan test edilmesini sağlar.
- `ANTHROPIC_API_KEY` yalnızca `.env`'den okunur.
