# Hafta 3 — Kural Motoru (Rol Bazlı Erişim Kontrolü)

**Proje:** Akıllı Okul Bilgi Sistemi (Smart School Information System)
**Önceki durum:** Hafta 2'nin FastAPI + JWT auth katmanı (`week3/week-03/`, Hafta 2'nin kopyası)

---

## 1. Bu haftanın amacı

Hafta 2'de "kimsin" sorusuna cevap verebiliyorduk (JWT token). Bu hafta "ne
görebilirsin" sorusuna cevap veren kural motorunu yazıyoruz. Bu motor henüz
hiçbir API endpoint'ine bağlı değil — kendi başına, izole şekilde test ediliyor.
Gerçek bir endpoint'e bağlanması Hafta 4'te, LLM ile üretilen SQL'in bu
motordan geçirilmesiyle olacak.

## 2. Teslim edilecekler

- [ ] `backend/app/services/rule_engine.py` — `RuleEngine` sınıfı, 4 rol için
      bound-parameter SQL filtresi üreten statik metot
- [ ] Her rol için filtre mantığı:
  - `principal` → filtre yok (`1=1`)
  - `teacher` → `class_name = :class_name` (`related_class` zorunlu)
  - `parent` → `id = :student_id` (`related_id` zorunlu — veli hesabında
    `related_id` zaten çocuğun `students.id`'sini tutuyor, bu yüzden `parent`
    filtresi `student` ile birebir aynı mantığı kullanır; `students.parent_id`
    sütunu bu filtre için kullanılmaz)
  - `student` → `id = :student_id` (`related_id` zorunlu)
  - Bilinmeyen rol veya eksik `related_id`/`related_class` → `ValueError`
- [ ] `backend/tests/test_rule_engine.py` — birim testleri (her rol, hata
      durumları, bilinmeyen rol)
- [ ] Entegrasyon testleri — Hafta 1-2'nin seed verisi üzerinde gerçek
      SQLAlchemy sorgusu çalıştırıp doğru satırların döndüğünü doğrulama
- [ ] Bir SQL injection denemesini kapsayan test (`related_class =
      "9-A' OR '1'='1"` gibi bir değerin salt veri olarak işlendiğinin
      kanıtlanması)
- [ ] `requirements-dev.txt` — `pytest`, `pytest-cov`

## 3. Kapsam DIŞI (bilerek ertelenen)

- `/query` gibi veri döndüren bir FastAPI endpoint'i → Hafta 4
- Doğal dil → SQL, LLM entegrasyonu → Hafta 4
- Streamlit arayüzü → Hafta 6
- Rate limiting → Hafta 5

## 4. Kabul kriterleri

1. `pytest backend/tests/ -v` tüm testler `PASSED` döner.
2. `RuleEngine`, `teacher` rolü için yalnızca o kullanıcının `related_class`
   değerini içeren bir filtre üretir.
3. `RuleEngine`, `parent`/`student` rolü için yalnızca o kullanıcının
   `related_id` değerini içeren bir filtre üretir.
4. Üretilen SQL metninde hiçbir yerde ham (interpolate edilmiş) değer yoktur —
   tüm değişkenler `:param` olarak bağlanır.
5. `teacher` rolü `related_class` olmadan çağrılırsa `ValueError` fırlatılır.
6. Entegrasyon testi, gerçek `school.db` üzerinde `teacher1`'in yalnızca 9-A
   sınıfındaki öğrencileri, `parent1`'in yalnızca kendi çocuğunu gördüğünü
   doğrular.
7. `RuleEngine` henüz hiçbir FastAPI route'una bağlı değildir — `backend/app/api/`
   altında bu haftaya ait yeni bir dosya yoktur.

## 5. Sunumdaki demo akışı

1. `pytest backend/tests/test_rule_engine.py -v` çalıştırılır, tüm testlerin
   geçtiği gösterilir.
2. Python konsolunda `RuleEngine.build_student_filter("teacher", None, "9-A")`
   çağrılıp üretilen `(sql, params)` çiftinin ekrana basılması — SQL'in
   `:class_name` içerdiği, ham `"9-A"` değerinin SQL metninde değil `params`
   sözlüğünde olduğu gösterilir.
3. Aynı çağrı kötü niyetli bir `related_class` değeriyle (`"9-A' OR '1'='1"`)
   tekrarlanır — SQL metninin değişmediği, değerin yalnızca `params` içinde
   taşındığı vurgulanır.
4. Entegrasyon testinin gerçek veritabanına karşı çalıştığı, `teacher1` için
   yalnızca 4 öğrenci (9-A sınıfı) döndüğü gösterilir.

## 6. Notlar / gerekçeler

- `RuleEngine`'i bu hafta bilerek hiçbir endpoint'e bağlamıyoruz. Sebep: Hafta
  4'te LLM'in ürettiği SQL de aynı motordan geçecek, ikisini aynı anda inşa
  etmek yerine önce kuralın kendisinin doğru çalıştığını kanıtlamak daha
  sağlam bir temel oluşturuyor.
- `pytest`/`pytest-cov` ayrı bir `requirements-dev.txt` dosyasında tutuluyor;
  bu paketler çalışan uygulamanın bir parçası değil, yalnızca geliştirme
  sırasında gerekli.
- Entegrasyon testleri gerçek `school.db` dosyasını kullanıyor, mock/sahte bir
  veritabanı değil — bu, kuralın yalnızca teoride değil gerçek veri üzerinde
  de doğru çalıştığını kanıtlamak için bilinçli bir tercih.
