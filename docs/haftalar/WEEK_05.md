# Hafta 5 — Niyet Analizi, Açıklanabilirlik ve Sertleştirme

**Proje:** Akıllı Okul Bilgi Sistemi (Smart School Information System)
**Önceki durum:** Hafta 4'ün çalışan `/query` endpoint'i (`week5/week-05/`, Hafta 4'ün kopyası)

---

## 1. Bu haftanın amacı

Hafta 4'te `/query` çalışıyordu ama her soruyu bir SQL sorgusu sayıp Claude'a
gönderiyordu — "merhaba" yazan biri bile gereksiz yere SQL ürettirme sürecine
sokuluyordu. Bu hafta üç şey ekleniyor: sorunun gerçekten bir veri sorgusu mu
yoksa sohbet mi olduğunu anlayan bir niyet analizi, sonuçla birlikte kısa bir
açıklama, ve sistemi kötüye kullanıma karşı koruyan rate limiting + loglama.
Yeni bir endpoint yok — mevcut `/query` olgunlaşıyor.

## 2. Teslim edilecekler

- [ ] `backend/app/services/intent_service.py` — `detect_intent(question: str,
      client=None) -> Literal["chat", "sql"]`; `client` parametresi opsiyonel,
      test edilebilirlik için (bağımlılık enjeksiyonu)
- [ ] `backend/app/services/explain_service.py` — `build_explanation(role: str,
      related_class: str | None, related_id: int | None, row_count: int) ->
      str`; kural tabanlı, LLM çağrısı yapmaz
- [ ] `backend/app/core/rate_limiter.py` — kullanıcı başına 60 saniyelik kayan
      pencerede 10 istek sınırı, bellek içi; limit aşılırsa `(False,
      retry_after_seconds)` döner
- [ ] `backend/app/core/logging_config.py` — JSON formatlı log handler'ı
- [ ] `query.py` güncellemesi: önce rate limit kontrolü → sonra niyet analizi
      → `chat` ise kısa yanıt, `sql` ise Hafta 4'ün tüm akışı + açıklama
      metni → her istek sonunda tek satır JSON log
- [ ] Üç yeni servis için birim testleri (API key gerektirmeyenler: rate
      limiter ve explain_service tamamen; intent_service mock client ile)

## 3. Kapsam DIŞI (bilerek ertelenen)

- Streamlit arayüzü → Hafta 6
- Shortcut/pattern-matching katmanı (LLM öncesi hızlı yanıt) → Hafta 7
- Redis gibi paylaşılan bir rate-limit deposu → kapsam dışı (README'de
  belirtilen bilinen sınırlama)
- Birden fazla soru tipi için ayrı niyet kategorileri (yalnızca chat/sql
  ikili ayrımı var)

## 4. Kabul kriterleri

1. `{"question": "merhaba"}` gönderildiğinde veritabanına hiç gidilmeden
   dostça bir yanıt döner.
2. `{"question": "sınıfımdaki öğrenci sayısı kaç"}` gönderildiğinde Hafta
   4'ün tüm akışından (Claude → güvenlik → RuleEngine) geçer.
3. Aynı kullanıcı 60 saniye içinde 11. isteği attığında `429 Too Many
   Requests` döner, yanıtta `Retry-After` header'ı bulunur.
4. Her `/query` isteği (başarılı veya başarısız) sunucu loglarında tek
   satırlık bir JSON kaydı bırakır.
5. SQL niyetli bir yanıtın gövdesinde `explanation` alanı bulunur ve bu alan
   `RuleEngine`'in uyguladığı filtreye dayanır (LLM'den gelmez).
6. `rate_limiter.py` ve `explain_service.py` testleri `ANTHROPIC_API_KEY`
   olmadan da çalışır ve geçer.
7. `intent_service.py` testleri mock bir client kullanarak hem `chat` hem
   `sql` dallarını API key olmadan doğrular.

## 5. Sunumdaki demo akışı

1. `{"question": "Merhaba, nasılsın?"}` gönderilir — dostça bir yanıt döner,
   sunucu loglarında `"intent": "chat"` ve veritabanına gidilmediği görülür.
2. `{"question": "Sınıfımdaki öğrenci sayısı kaç?"}` gönderilir — yanıtta
   hem `results` hem `explanation` alanı olduğu gösterilir.
3. Art arda 11 istek atan kısa bir döngü çalıştırılır, 11. isteğin `429`
   döndüğü ve `Retry-After` header'ının bulunduğu gösterilir.
4. Sunucu logları `tail -f` ile izlenir, her isteğin tek satır JSON
   bıraktığı canlı gösterilir.

## 6. Notlar / gerekçeler

- Rate limiter'ın bellek içi olması bilinçli bir sınırlama — tek worker'lı
  geliştirme ortamı için yeterli, production'da paylaşılan bir depoya
  (Redis vb.) geçiş gerektiği README'de açıkça belirtilir.
- Açıklama metninin LLM yerine kural tabanlı üretilmesi, Claude'un kendi
  sonucunu "açıklarken" tutarsız veya yanlış bir şey söyleme (hallucination)
  riskini ortadan kaldırmak için bilinçli bir tasarım kararı.
- Bu hafta yeni bir bağımlılık eklenmedi — rate limiting ve loglama Python'ın
  standart kütüphanesiyle yazıldı, niyet analizi mevcut `anthropic` SDK'sını
  yeniden kullanıyor.
