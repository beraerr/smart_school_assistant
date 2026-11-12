# Kesim günü 60 özellik listesi

Satır birimi (code_module, code_presentation, id_student). date_unregistration < 60 örneklemde yoktur. Sosyo-demografik sütunlar, num_of_prev_attempts ve studied_credits yoktur.

| sütun | tanım | kapsam | okul karşılığı | school counterpart | grup |
| --- | --- | --- | --- | --- | --- |
| code_module | Modül kodu. | genel | Tanımlayıcı; modele girmez | Identifier; not a model input |  |
| code_presentation | Sunum kodu. | genel | Tanımlayıcı; modele girmez | Identifier; not a model input |  |
| id_student | Öğrenci kimliği. | genel | Tanımlayıcı; modele girmez | Identifier; not a model input |  |
| at_risk | final_result Fail veya Withdrawn ise 1, Pass veya Distinction ise 0. | genel | Hedef; özellik değil | Target; not a feature |  |
| split | 2013B history, 2013J ve 2014B train, 2014J test. | genel | Tanımlayıcı; modele girmez | Identifier; not a model input |  |
| date_registration | Kayıt günü (modül başlangıcına göre). | genel | Okulda karşılığı yok | No school counterpart | KAYIT |
| n_expected | Tarihi gün <= 60 olan ve türü Exam olmayan ödev sayısı. | genel | Ödev teslim kaydı (okulda yok) | Assignment submission record (not in the school data) | TESLİM |
| n_submitted | Bu ödevlerden date_submitted gün <= 60 olan teslim sayısı. | genel | Ödev teslim kaydı (okulda yok) | Assignment submission record (not in the school data) | TESLİM |
| n_unsubmitted | n_expected eksi n_submitted. | genel | Ödev teslim kaydı (okulda yok) | Assignment submission record (not in the school data) | TESLİM |
| score_mean | Kesim penceresindeki teslimlerin ağırlıksız ortalama notu. Not yoksa boş. | genel | Not ortalaması (var) | Grade average (available) | NOT |
| score_weighted_mean | Aynı teslimlerin ağırlıklı ortalama notu. Ağırlık toplamı 0 ise boş. | genel | Not ortalaması (var) | Grade average (available) | NOT |
| delay_mean | Aynı teslimlerde ortalama (date_submitted - date). | genel | Ödev teslim kaydı (okulda yok) | Assignment submission record (not in the school data) | TESLİM |
| n_banked | Kesim penceresindeki teslimlerde is_banked = 1 satır sayısı. Bu satırlar silinmez. | genel | Ödev teslim kaydı (okulda yok) | Assignment submission record (not in the school data) | TESLİM |
| vle_clicks | student_vle_daily içinde gün <= 60 toplam sum_click. | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_active_days | Gün <= 60 olan farklı aktivite günü sayısı. | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_days_to_cutoff | Kesim günü eksi son aktivite günü. Aktivite yoksa boş. | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_click_forumng | Gün <= 60 için activity_type=forumng tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_click_subpage | Gün <= 60 için activity_type=subpage tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_click_oucontent | Gün <= 60 için activity_type=oucontent tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_click_homepage | Gün <= 60 için activity_type=homepage tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| vle_click_resource | Gün <= 60 için activity_type=resource tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | Mazeretsiz devamsızlık (yaklaşık) | Unexcused absence (approximate) | ETKİNLİK |
| has_history | Aynı code_module içinde sıraca önceki sunum varsa 1, yoksa 0. | geçmiş | Geçmiş dönem notları (okulda henüz yok) | Past-term grades (not yet in the school data) | GEÇMİŞ |
| hist_slot_mean | Öğrencinin kesimdeki ödev yuvalarının geçmiş ortalama notunun ortalaması. Yuva anahtarı (code_module, assessment_type, tür içinde tarihe göre sıra; eşit tarihte id_assessment). Yalnızca aynı modülün önceki sunumları. Eşleşen yuva yoksa boş. | geçmiş | Geçmiş dönem notları (okulda henüz yok) | Past-term grades (not yet in the school data) | GEÇMİŞ |
| hist_slot_submit_rate | Aynı yuvaların geçmiş teslim oranının ortalaması. Eşleşen yuva yoksa boş. | geçmiş | Geçmiş dönem notları (okulda henüz yok) | Past-term grades (not yet in the school data) | GEÇMİŞ |
| score_vs_hist | Öğrenci notu eksi yuvanın geçmiş ortalama notu; notu ve geçmişi olan yuvaların öğrenci bazında ortalaması. Doldurulmaz. | geçmiş | Geçmiş dönem notları (okulda henüz yok) | Past-term grades (not yet in the school data) | GEÇMİŞ |
| hist_module_risk_rate | Önceki sunumların, aynı örneklem tanımıyla at_risk oranı. Önceki örneklem yoksa boş. | geçmiş | Geçmiş dönem sonuçları (okulda yok) | Past-term outcomes (not in the school data) | GEÇMİŞ |
