# UCI Student Performance ↔ PostgreSQL şeması

Hafta 10 risk entegrasyonu bu tabloyu girdi alır. Durum her satırda şunlardan biridir: **sistemde var**, **türetilebilir**, **yok**.

Canlı şema (SQLAlchemy modelleri, PostgreSQL):

- `users`: `id`, `username`, `password_hash`, `role`, `related_id`, `related_class`
- `students`: `id`, `name`, `class_name`, `total_absences`, `parent_id`
- `teachers`: `id`, `name`, `class_name`
- `grades`: `id`, `student_id`, `subject`, `grade`, `date` — `grade` 100'lük
- `attendance`: `id`, `student_id`, `date`, `status` — `present`, `absent`, `excused`

Ölçek: `UCI_notu = grades.grade / 5`. Backend `PASS_GRADE = 50` ile UCI `PASS_THRESHOLD_20 = 10` aynı kapıdır (`G3 * 5 >= 50`).

`teachers` ve `users` içinde UCI sütununun doğrudan karşılığı yoktur. Veli bağlantısı yalnızca `students.parent_id → users.id` şeklindedir.

## Ham UCI sütunları

| UCI özelliği | Durum | PostgreSQL | Dönüşüm |
| --- | --- | --- | --- |
| school | yok | — | GP / MS okul kodu. `students.class_name` sınıf adıdır (ör. `9-A`), okul değildir. |
| sex | yok | — | Cinsiyet sütunu yok. |
| age | yok | — | Yaş veya doğum tarihi yok. |
| address | yok | — | Kentsel / kırsal (`U` / `R`) yok. |
| famsize | yok | — | Aile büyüklüğü (`LE3` / `GT3`) yok. |
| Pstatus | yok | — | Ebeveynlerin birlikte yaşama durumu yok. |
| Medu | yok | — | Anne eğitim düzeyi (0–4) yok. |
| Fedu | yok | — | Baba eğitim düzeyi (0–4) yok. |
| Mjob | yok | — | Anne mesleği yok. |
| Fjob | yok | — | Baba mesleği yok. |
| reason | yok | — | Okulu seçme nedeni yok. |
| guardian | yok | — | `students.parent_id` veli hesabını bağlar. `mother` / `father` / `other` ayrımı yoktur, bu yüzden guardian türetilemez. |
| traveltime | yok | — | Eve ulaşım süresi yok. |
| studytime | yok | — | Haftalık çalışma süresi yok. |
| failures | yok | — | Geçmiş sınıf tekrarı sayısı yok. Düşük nottan üretilmez. |
| schoolsup | yok | — | Okulun ek eğitim desteği yok. |
| famsup | yok | — | Ailenin eğitim desteği yok. |
| paid | yok | — | Ücretli ek ders yok. |
| activities | yok | — | Ders dışı etkinlik yok. |
| nursery | yok | — | Anaokulu geçmişi yok. |
| higher | yok | — | Yükseköğrenim isteği yok. |
| internet | yok | — | Evde internet yok. |
| romantic | yok | — | Romantik ilişki yok. |
| famrel | yok | — | Aile ilişkisi skoru yok. |
| freetime | yok | — | Boş zaman skoru yok. |
| goout | yok | — | Arkadaşlarla dışarı çıkma skoru yok. |
| Dalc | yok | — | Hafta içi alkol tüketimi yok. |
| Walc | yok | — | Hafta sonu alkol tüketimi yok. |
| health | yok | — | Sağlık skoru yok. |
| absences | türetilebilir | `attendance`, `students.total_absences` | Dönemlik devamsızlık = `COUNT(*)` from `attendance` where `status = 'absent'`. `students.total_absences` bu sayının özet alanıdır. `excused` UCI devamsızlığına eklenmez. |
| G1 | türetilebilir | `grades.grade`, `grades.date` | Birinci dönem notu ≈ o dönemdeki `grades.grade` ortalaması / 5. Şemada dönem numarası yoktur; erken tarih penceresi vekildir. EARLY seti bu vekili kullanmaz. |
| G2 | türetilebilir | `grades.grade`, `grades.date` | İkinci dönem notu ≈ sonraki tarih penceresindeki ortalama / 5. G2, G3 ile çok güçlü ilişkilidir. EARLY ve MIDTERM özellik setlerinde yoktur. |
| G3 | türetilebilir | `grades.grade` | Nihai ders notu ≈ `AVG(grades.grade) / 5` (`student_id`, `subject`). Özellik değildir. `at_risk = 1` when ortalama `< PASS_GRADE` (50), UCI'de `G3 < 10`. |
| subject | sistemde var | `grades.subject` | Doğrudan `grades.subject`. UCI'de ayrı `student-mat.csv` ve `student-por.csv` dosyalarıdır; birleşik tabloda `subject` `mat` veya `por` olur. |

## Türetilmiş alanlar

| Alan | Durum | PostgreSQL | Dönüşüm |
| --- | --- | --- | --- |
| öğrenci kimliği | sistemde var | `students.id` | UCI'de öğrenci numarası yoktur. `student_key`, iki CSV'yi eşlemek için demografik sütunların SHA-256 özetidir. Canlı gruplama ve Hafta 9'daki `GroupKFold` karşılığı `students.id` olur; hash canlı anahtar değildir. |
| at_risk | türetilebilir | `grades.grade` | `1` if ders not ortalaması `< PASS_GRADE` (50), değilse `0`. UCI: `1` if `G3 < 10` else `0`. |
| g3_zero | türetilebilir | `grades.grade` | `1` if nihai not 0. UCI'de `G3 = 0` satırı silinmez. Bayrak özellik setine girmez çünkü `G3 = 0` ise `at_risk = 1`. |
| parent_edu_max | yok | — | `max(Medu, Fedu)`. İkisi de şemada yoktur. |
| alcohol_total | yok | — | `Dalc + Walc`. İkisi de yoktur. |
| support_any | yok | — | `1` if `schoolsup = yes` veya `famsup = yes`. İkisi de yoktur. |
| has_failures | yok | — | `1` if `failures > 0`. `failures` karşılığı yoktur. |
| absences_log1p | türetilebilir | `attendance` | `log1p(absent kayıt sayısı)`. |
| absence_bucket | türetilebilir | `attendance` | Absent sayısından sıra kodu: `0 → 0`, `1–5 → 1`, `6–10 → 2`, `11–20 → 3`, `21+ → 4`. |

## Hafta 10 için kullanılabilir sinyal

Erken uyarı (EARLY) bugün şemadan yalnızca şunlarla beslenebilir: `grades.subject`, devamsızlık sayısı ve bundan gelen `absences_log1p` / `absence_bucket`, nihai nottan üretilen etiket. Dönem başı modelinde G1 ve G2 vekilleri kullanılmaz. MIDTERM, erken tarih penceresindeki not ortalaması / 5 (G1 vekili) eklendikten sonra kurulabilir. Demografi, alkol, aile eğitimi, destek ve sınıf tekrarı canlı veride yoktur; bu sütunlar UCI deneyinde kalır, üretim skoruna taşınmaz.
