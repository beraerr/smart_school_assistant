# Kesim günü 60 özellik listesi

Satır birimi (code_module, code_presentation, id_student). date_unregistration < 60 örneklemde yoktur. Sosyo-demografik sütunlar, num_of_prev_attempts ve studied_credits yoktur.

| sütun | tanım | kapsam | okul karşılığı |
| --- | --- | --- | --- |
| code_module | Modül kodu. | genel | ders bağlamı |
| code_presentation | Sunum kodu. | genel | ders bağlamı |
| id_student | Öğrenci kimliği. | genel | ders bağlamı |
| at_risk | final_result Fail veya Withdrawn ise 1, Pass veya Distinction ise 0. | genel | not |
| split | 2013B history, 2013J ve 2014B train, 2014J test. | genel | ders bağlamı |
| date_registration | Kayıt günü (modül başlangıcına göre). | genel | ders bağlamı |
| n_expected | Tarihi gün <= 60 olan ve türü Exam olmayan ödev sayısı. | genel | not |
| n_submitted | Bu ödevlerden date_submitted gün <= 60 olan teslim sayısı. | genel | not |
| n_unsubmitted | n_expected eksi n_submitted. | genel | not |
| score_mean | Kesim penceresindeki teslimlerin ağırlıksız ortalama notu. Not yoksa boş. | genel | not |
| score_weighted_mean | Aynı teslimlerin ağırlıklı ortalama notu. Ağırlık toplamı 0 ise boş. | genel | not |
| delay_mean | Aynı teslimlerde ortalama (date_submitted - date). | genel | not |
| n_banked | Kesim penceresindeki teslimlerde is_banked = 1 satır sayısı. Bu satırlar silinmez. | genel | not |
| vle_clicks | student_vle_daily içinde gün <= 60 toplam sum_click. | genel | devamsızlık |
| vle_active_days | Gün <= 60 olan farklı aktivite günü sayısı. | genel | devamsızlık |
| vle_days_to_cutoff | Kesim günü eksi son aktivite günü. Aktivite yoksa boş. | genel | devamsızlık |
| vle_click_forumng | Gün <= 60 için activity_type=forumng tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | devamsızlık |
| vle_click_subpage | Gün <= 60 için activity_type=subpage tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | devamsızlık |
| vle_click_oucontent | Gün <= 60 için activity_type=oucontent tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | devamsızlık |
| vle_click_homepage | Gün <= 60 için activity_type=homepage tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | devamsızlık |
| vle_click_resource | Gün <= 60 için activity_type=resource tıklama toplamı. Aynı pencerede en sık görülen, en fazla 5 activity_type için açılır (sıra: n_rows, eşitlikte sum_click, sonra ad). | genel | devamsızlık |
| has_history | Aynı code_module içinde sıraca önceki sunum varsa 1, yoksa 0. | geçmiş | ders bağlamı |
| hist_slot_mean | Öğrencinin kesimdeki ödev yuvalarının geçmiş ortalama notunun ortalaması. Yuva anahtarı (code_module, assessment_type, tür içinde tarihe göre sıra; eşit tarihte id_assessment). Yalnızca aynı modülün önceki sunumları. Eşleşen yuva yoksa boş. | geçmiş | not |
| hist_slot_submit_rate | Aynı yuvaların geçmiş teslim oranının ortalaması. Eşleşen yuva yoksa boş. | geçmiş | not |
| score_vs_hist | Öğrenci notu eksi yuvanın geçmiş ortalama notu; notu ve geçmişi olan yuvaların öğrenci bazında ortalaması. Doldurulmaz. | geçmiş | not |
| hist_module_risk_rate | Önceki sunumların, aynı örneklem tanımıyla at_risk oranı. Önceki örneklem yoksa boş. | geçmiş | ders bağlamı |
