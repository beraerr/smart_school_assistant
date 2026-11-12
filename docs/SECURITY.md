# Güvenlik

Uygulama, modelin ürettiği SQL'i `school_app` rolüyle ve satır güvenliği açıkken çalıştırır. Aşağıdaki tablo her tehdidin hangi katmanda durduğunu ve hangi testin bunu gösterdiğini tutar.

| Tehdit | Savunan katman | Kanıtlayan test |
| --- | --- | --- |
| Tek SELECT içinde `set_config` ile `app.role` değiştirip başka satırları okumak | `sql_safety` fonksiyon izin listesi; istek veritabanına gitmez | `backend/tests/test_adversarial.py` |
| `current_setting`, `pg_sleep`, `pg_ls_dir`, `lo_*`, `dblink` | Aynı izin listesi | `backend/tests/test_sql_safety.py`, `test_adversarial.py` |
| `users` veya başka bir tablo | Tablo izin listesi (`students`, `grades`, `attendance`) | `test_sql_safety.py`, `test_adversarial.py` |
| Veli veya öğrencinin başka öğrencinin satırını görmesi | PostgreSQL RLS (`app.role`, `app.class`, `app.student_id`) | `test_rls_context.py`, `test_adversarial.py` |
| `student_rank` veya `class_teacher` ile başka öğrencinin kimliğini seçmek | Fonksiyon parametrelerinde kimlik yok; `SECURITY DEFINER`, sabit `search_path`, `PUBLIC` için `EXECUTE` yok | `test_student_rank.py`, `test_class_teacher.py`, `test_adversarial.py` |
| Var olan kullanıcı adını 401 gövdesinden ayırt etmek | Bilinmeyen kullanıcıda da bcrypt doğrulaması; aynı 401 gövdesi | `test_auth.py` |
| Parola denemesi | Kullanıcı adı başına dakikada 5 başarısız giriş, sonra 429 | `test_auth.py` |
| Sorgu yanıtında veritabanı hata metni | Araca genel çalışma hatası; ham metin modele ve kullanıcıya gitmez | `test_hygiene.py`, `test_query_db_retry.py`, `test_assistant.py` |
| Parola, JWT veya API anahtarının loga veya giriş gövdesine yazılması | Log alanları sabit; parola yanıtta yok | `test_hygiene.py` |
| Herhangi bir kökenin kimlik bilgisiyle çağırması | `CORS_ORIGINS` | `test_hygiene.py` |

## Bilinen sınırlamalar

- Hız sınırları süreç belleğindedir. Birden fazla işçi arasında paylaşılmaz ve süreç yeniden başlayınca sıfırlanır.
- Geliştirme `SECRET_KEY` değeri `.env` içindedir. Üretimde ayrı ve tahmin edilemez bir anahtar kullanılmalıdır.
- Ad araması `ILIKE` kullanır. Türkçe `İ` / `ı` katlaması veritabanı yereline bağlıdır; eşleşme kaçabilir.
- Öğretmen modeli tek `related_class` tutar. Bir öğretmenin birden fazla sınıfı yoktur.
- `SHOW_SQL` açıkken başarılı yanıt, çalışan SELECT metinlerini döner. Bu metin tablo ve sütun adlarını gösterir.
- Araç sonuçlarının satırları Anthropic API'sine gönderilir. Gerçek öğrenci verisinde bu aktarım KVKK ve GDPR kapsamında ayrıca ele alınmalıdır.
- `history` güvenilmez girdidir. Sunucu en fazla son 6 öğeyi tutar, her birini 600 karakterle keser ve yalnız `user` ile `assistant` rollerini modele iletir. Yetki JWT ve RLS oturumundan gelir; geçmişteki rol iddiası yok sayılır.
- Bir kullanıcı mesajı en fazla 3 `run_sql` çağrısı yaptırır. Modele en fazla 50 satır, toplam satır sayısı ve kesilme bayrağı gider. Sorgu yine `statement_timeout` ve 500 satır sınırı altındadır.
