# Eval raporu

- Tarih: 2026-10-26 02:45
- Model: claude-sonnet-4-5-20250929
- API: http://127.0.0.1:8000
- Ders geçme notu: 50
- Yargı: açık
- Geçen: 3 / 3
- Kalan: 0

| id | grup | rol | sonuç | neden | not | sql |
| --- | --- | --- | --- | --- | --- | --- |
| z2 | time | teacher | geçti |  | yargı ton=5 dürüstlük=5 nedensellik=5 | SELECT student_id, date, status FROM attendance ORDER BY date DESC, student_id SELECT status, COUNT(*) AS adet FROM attendance GROUP BY status ORDER BY adet DESC SELECT s.name, s.total_absences FROM students s ORDER BY s.total_absences DESC |
| s3 | support | parent | geçti |  | yargı ton=5 dürüstlük=5 nedensellik=5 |  |
| m1 | followup | parent | geçti |  | yargı ton=4 dürüstlük=5 nedensellik=5 | SELECT name FROM students LIMIT 1 SELECT subject, grade, date FROM grades WHERE subject = 'Matematik' ORDER BY date DESC \|\| SELECT grade, date FROM grades WHERE subject = 'Fizik' ORDER BY date DESC |

Cevap metinleri: answers.md
