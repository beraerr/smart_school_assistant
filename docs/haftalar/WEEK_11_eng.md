# Week 11 — Integration and Verification

## Summary
This week covered four workstreams. We regenerated the school's mock data to follow the Turkish Ministry of Education (MEB) calendar and added a date gate: the system no longer sees data after the demo's "today". We tightened the assistant: every number must rest on a query, with a correction round and a fallback for ungrounded numbers. We closed two holes in the SQL validator. We collected the work of Weeks 8–10 into a research page with no login, as the justification for the risk rule in the school system.

Finally, we questioned our own result: does the model really find struggling students, or only those who have already dropped the course? We wrote 10 expectations before the run, sealed them with md5, then tested them in two periods. **Result: 5 held, 3 did not hold, 2 inconclusive.** The doubt failed: the model and the rule find students who will fail more easily, and at a somewhat higher rate, than students who will withdraw. The rule in the system did not change.

## 1. Data and time

### 1.1 The mock data was regenerated
The mock data had been frozen since Week 7. This week we lifted the freeze; the decision record follows.

- **Why:** In the old mock, grades fell before the school year started, so date questions meant nothing in the demo. The generator also met some conditions with special code keyed on a student's name.
- **What was done:** `scripts/mock_uret.py` is deterministic (seed 20260914), school year 14.09.2026–25.06.2027. 6 classes × 6 students, 6 teachers, 1,440 grades (2 performance + 2 written per term), 6,444 attendance rows (179 school days). md5 `de7da13d07102011882382e467968e24`.
- **Safeguards:** Absences come from profile parameters; an AST test forbids branching on names. The demo stories (flagged and unflagged students, one student with a yearly average below 50) are protected by a generation gate.
- The old mock is archived: `database/archive/mock_data_hafta07-11.json`.

### 1.2 Date gate
| Component | What it does |
|---|---|
| `backend/app/services/takvim.py` | MEB 2026–2027: term 1 14.09–22.01, mid-term breaks 16–20.11 and 8–12.03, semester break 25.01–05.02, term 2 08.02–25.06; public and religious holidays |
| `DEMO_TODAY` (`.env`) | The demo's "today"; if empty, the Europe/Istanbul date |
| `app.today` + RLS | RESTRICTIVE policies on grades and attendance |
| `student_rank` | Date condition; empty values sorted last |
| Risk window | Risk is computed from the current term's window |

**A leak was closed.** `students.total_absences` carried the year-end total: in October, June's absences were visible, and the column disagreed with the attendance table. It was removed. Absences now come from attendance everywhere, with excused and unexcused counted separately.

## 2. Assistant and SQL validator

### 2.1 Assistant
- **Date block:** Each request gives the model today, the term, the visible data range and a calendar summary.
- **Number check:** Derived numbers are computed in SQL (LAG allowed). Numbers from earlier assistant messages are allowed. If an ungrounded number appears, the rejected numbers are listed and one extra tool call is allowed (4 at most).
- **Fallback:** If the correction round also fails, the query results are shown instead of an answer (the query section opens in the interface).
- **Logs:** `ungrounded_number`, `assistant_fallback` and `run_sql_exception` are written as structured logs.
- **Known limit:** the abs() match does not check direction.

### 2.2 SQL validator
| Problem | Effect | Fix |
|---|---|---|
| AND, CASE, NULLIF were treated as functions | Valid queries were rejected; the assistant said "I couldn't reach the records" | Operators separated from the function check; NULLIF allowed |
| DELETE could pass inside a CTE (audit 6.2) | The read-only guarantee could be broken | DML, DDL, INTO and locks rejected everywhere, including CTEs and subqueries |

The validator allows the public schema only. A new test checks that every example SQL in the assistant's instructions passes the validator.

## 3. Interface
- Logo in the sidebar header; the Türksat footer is sticky; Demo, Role, Language and Logout share one box style on a single sizing system in the top bar.
- The sidebar opens on login; the preview card on the login screen was replaced by an "Explore the research →" button (session and language are kept).
- The status of the role-based example question cache and of the favicon and config.toml task is not certain; to be verified in Week 12.

## 4. Research page (`?sayfa=arastirma`)
The risk tab in the school system does not come from a prediction model but from a transparent rule tested on open data. This page shows how we reached the rule, what worked and what is still unknown.

![Summary tab of the research page](figures/ekran_ozet_tr.png)

*Summary tab of the Turkish interface. Screenshot taken before the 20% format fix.*

- No login; it does not touch school data or the backend. No findings are drawn from the synthetic school data.
- 11 tabs: Summary, Datasets, UCI exploration, OULAD exploration, Modelling, Decision rule, Additional analyses, Teacher effect, Bridge to the system, Errors and fixes, Limits and sources. Each tab has an "In this section" box.
- One package: `scripts/arastirma_paketi.py` → `frontend/assets/arastirma/arastirma.json` + 52 images. Numbers in the texts are not typed by hand; placeholders are resolved from the package (`coz`), and derived values (`turev.*`) are computed in the page layer.
- In-cell computations in notebooks 01, 02 and 03 moved to the package (`data_science/absence.py`, `oulad/eda.py`, `oulad/model_tables.py`); outputs are identical.

## 5. Additional analyses: testing our own result

### 5.1 The doubt
![Thought map on the research page](figures/ekran_harita_tr.png)

*Thought map (Turkish interface): stops H8–H11, questions E1–E4 and the doubt box.*

Our target is "failed or withdrew". A student who withdraws also stops logging in and submitting; perhaps the model sees only that. If so, the risk tab shows not the struggling student but the one who has already left. We asked four questions: which signal carries the information (E1), who is easier to find (E2), how early (E3), and what the literature says (E4).

### 5.2 Pre-registration
![10 expectations written before the run](figures/fig07a_beklentiler_once_en.png)

*Expectations B1–B10 were written before the run and sealed with md5. Results are not shown in this chart: each card has a "?" and a gray strip.*

We wrote 10 expectations with numeric criteria and recorded the files' md5: `ek_analizler_on_kayit.md` (eb367fbb…), `_eki.md` (updated once before the run: 20f75feb… → f8cb24be…), `_eki2.md` (5cd0e828…, the E3 exclusion rule and fixed cohort). The analysis code (`data_science/oulad/ek.py`) refuses to run if the latest record does not match. **Decision rule:** an expectation held if it was met in both validation (2014B) and test (2014J), did not hold if met in neither, and is inconclusive if the periods disagree.

Signal groups: GRADES (`score_mean`, `score_weighted_mean`), SUBMISSION (`n_expected`, `n_submitted`, `n_unsubmitted`, `delay_mean`, `n_banked`), ACTIVITY (`vle_*`), REGISTRATION (`date_registration`).

### 5.3 The doubt fails (E2)
![Finding students who will fail is easier than finding students who will withdraw](figures/fig03_hedef_ayristirma_en.png)

*Three panels show three targets: reference (Fail or Withdrawn), KALDI (Fail; Withdrawn excluded) and BIRAKTI (Withdrawn; Fail excluded). The filled dot is test and the hollow dot is validation ROC AUC (hgb).*

We predicted "failed" and "withdrew" separately. GENERAL hgb ROC AUC: KALDI 0.843 (validation) and 0.815 (test); BIRAKTI 0.805 and 0.778. We expected withdrawals to be easier to find (B4): **did not hold**. For BIRAKTI, the strongest single group is submission (test 0.751), not activity: B5 did not hold either.

![The rule catches students who will fail at a somewhat higher rate than those who will withdraw](figures/fig04_kural_yakalama_en.png)

*Hits among the within-class top 20% flags of the two-signal rule, split by final_result; each bar is the share of positives in that group caught by the rule.*

The rule catches 42.5% (671 / 1,578, validation) and 41.3% (742 / 1,798, test) of students who will fail, and 30.2% (285 / 945) and 37.8% (503 / 1,329) of those who will withdraw. In test, 742 hits are Fail and 503 Withdrawn: most of the rule's hits do not come from withdrawals (B7 **did not hold**).

### 5.4 Where is the information? (E1)
![A single signal group is not enough](figures/fig02_sinyal_gruplari_en.png)

*Each row is a feature set (hgb, reference target). The filled dot shows test ROC AUC with its ninety-five percent interval, the hollow dot the validation value.*

Test ROC AUC: GRADES 0.712, SUBMISSION 0.735, ACTIVITY 0.732, GRADES + SUBMISSION 0.780, GENERAL 0.798. No single group reaches the full model (B1 held). Grades and submission together trail the full model by 0.011 (validation) and 0.017 (test) (B3 held). The strongest single group changes between periods (B2 inconclusive). **For the school:** the main carrier of the risk flag is not attendance but grades and assignment records. The school has no submission records today; this work shows they are the most valuable missing signal.

### 5.5 How early? (E3)
![Cost of early warning](figures/fig05_erkenlik_en.png)

*ROC AUC by cutoff day in the fixed cohort (hgb, reference target): solid line test, dashed line validation. Fixed cohort: 14,059 students still registered on day 120.*

We ran the same pipeline for days 14, 30, 60, 90 and 120. Test GENERAL: 0.675, 0.711, 0.788, 0.821, 0.864. Performance rose at every step (B8), and most of the gain came early (B9). On day 14, activity alone is almost as good as the full model (0.669 vs 0.675; B10). The day-60 choice is justified in hindsight: most of the gain is in, and there is still time to intervene.

Before running, we noticed that on day 14 no course in the test period has a graded assignment. "No flag in a class without graded work" is the school system's rule, not the model's evaluation rule, so it was not applied in E3. The decision was written to `_eki2.md` before any result was seen.

![Late withdrawals are harder to see early](figures/fig06_erkenlik_hedef_en.png)

*GENERAL ROC AUC for KALDI and BIRAKTI in the fixed cohort. BIRAKTI here means withdrawing after day 120; early withdrawals are not in this chart.*

On day 14, KALDI 0.692 and BIRAKTI 0.628; the gap narrows by day 120 (0.870 and 0.849).

### 5.6 Comparison with the literature (E4)
Published OULAD values often exceed 90%; our day-60 test value is ROC AUC 0.792. These numbers are not directly comparable: prediction point, split method, target and the use of demographic features differ between studies.

| Study | Prediction point | Demographics | Reported value |
|---|---|---|---|
| This study | Day 30, fixed cohort | No | ROC AUC 0.711 |
| Wu, Jia and Pham (2026) | Day 28, temporal | No | ROC AUC 0.709 |
| Wu et al. (2026) | Day 28, grouped by student | Yes | ROC AUC 0.775 |
| Adnan et al. (2021) | 20% of the course | Yes | Precision 0.79 |

The closest design is Wu et al. (2026): an early fixed day, exclusion of students who withdrew before the cutoff, temporal validation and a model without demographic features. The numbers are very close, but the setups are not identical; this is not a validation, only a sign that our numbers are in a plausible range for this protocol family. In Wu et al., predicting withdrawal (0.697) is also harder than predicting failure (0.720): our B4 result replicates independently (B11, qualitative; small sample). We could not verify the split type for Adnan et al. (2021) and *Scientific Reports* (2025).

### 5.7 Result
![10 pre-registered expectations: 5 held, 3 did not hold, 2 inconclusive](figures/fig07_beklentiler_en.png)

*Each card gives the result as both color and text.*

| Result | Expectations |
|---|---|
| Held | B1, B3, B8, B9, B10 |
| Did not hold | B4, B5, B7 |
| Inconclusive | B2, B6 |
| Supported (qualitative) | B11 |

The three that did not hold were the three legs of the doubt that "the model only finds withdrawals".

### 5.8 What changed, what did not
- **Changed:** The doubt failed; we know what the system catches. The day-60 choice is justified. The most valuable missing signal for the school is identified: assignment submission records.
- **Unchanged:** The rule in the system. The analyses were for understanding; any change would be tested separately under a new pre-registration.
- **Teacher effect:** Not measurable; neither dataset has teacher data. The system is built to be insensitive to it (within-class relative rank). The data needed to measure it is listed. It must not become a teacher-ranking tool.

## 6. Decisions
| Decision | Reason |
|---|---|
| The mock freeze was lifted | Calendar alignment and the demo value of date questions |
| `total_absences` removed | Year-end leak and inconsistency with attendance |
| No ungrounded numbers in the assistant | Number check, correction round, fallback |
| Research page has no login and is independent of school data | No findings are drawn from synthetic school data |
| Additional analyses do not change the rule | A change proposal is tested under a new pre-registration |
| Teacher effect is reported as a result | Not measurable; system insensitive to it; not a teacher-ranking tool |

## 7. Bug log
Records from the start of the week (H11-1..7): mock md5, identity guessing, invented number, extra round, Streamlit cache, example question contract, sticky top bar. Details are in the records from the start of the week. Added during the rest of the week:

| Bug | Root cause | Fix |
|---|---|---|
| Grades before school started | The mock was generated without the calendar | Deterministic regeneration on the calendar |
| Generator fixed by name | Conditions were met with special code for one student | Profile parameters; no-branching-on-names test |
| `total_absences` leak | The year-end total was visible on every date and disagreed with attendance | Column removed; absences from attendance |
| "I couldn't reach the records" dead end | The validator treated AND, CASE, NULLIF as functions | Operator set separated; NULLIF added |
| DELETE inside a CTE (audit 6.2) | The check did not cover CTE bodies | DML, DDL, INTO and locks rejected everywhere |
| Assistant numbers | `distinct_counts` was not in the allowed set; earlier-turn numbers were not allowed over HTTP; month name + number was masked wrongly | Fixed |
| Fragile UI tests | Cards were found by their border, tabs by short labels | Tests find them by their own markers |
| In-cell computation in notebooks | Computations in 01, 02, 03 lived in the notebook | Moved to the package; outputs identical |
| `.venv` copy and wrong Jupyter kernel | The copied environment pointed to week08's Python | `staj-week11` kernel; verified that `explain.json` was produced with TreeExplainer |
| feature_list "school counterpart" | The Week 9 classification was wrong (at_risk and submission counters as "grade") | Fixed |
| feature_group `vle_click_*` | Dynamic columns fell outside the groups; an existing slice test caught it | Prefix rule and a new test |
| Pre-registration check | It read the first md5 record | It reads the latest record |
| Structure test broke | After the text patch, placeholders were searched unresolved | Test bound to the page's resolver (`coz`) |
| UCI TR images in English | The TR notebook kept English chart labels; the test did not look at image content | Known limit; plotting code moves to the package in Week 12 |

**Open:** in `explain.py` `_attribute`, `except Exception` silently switches method (did not affect today's output); to be fixed.

## 8. Known limits
- TR versions of the UCI and OULAD exploration charts are in English or use decimal points; the TR formatter is also not applied to the Modelling and Decision rule charts.
- Group assignment lives in two places (`dataset.py` prefix rule, `ek.py` fixed `GROUP_OF`); a single `group_of()` later. `ek.py` is not changed now; if it changes, the additional analyses are rerun.
- Figure outputs live under `data_science/oulad/reports/`, inconsistent with `reports/` at the project root.
- The additional analyses are exploratory; there is one validation period.

## 9. Outputs and verification
- **Code:** `data_science/oulad/ek.py`, `figures.py` (`--rule2 --ek`), `scripts/arastirma_paketi.py`, `scripts/mock_uret.py`, `backend/app/services/takvim.py`, `backend/app/core/bugun.py`; reports `data_science/oulad/reports/ek_metrics.json` and `figures/week11/` (8 charts, TR/EN).
- **Documents:** `docs/ek_analizler_on_kayit*.md`, `docs/on_kayit_md5.txt`, `docs/ek_analizler_sonuc.md`, `docs/metin_yamasi.json`.
- **Tests:** Full suite on 7 November: 1,210 passed, 3 skipped. After the text and interface fixes on 8 November, the frontend tests passed.
- **Package diff:** No existing key changed value; the only new key, `rule.flag_rate`, comes from the rule's own constant (`rule.py` `FLAG_RATE`).
- **Parquet:** Accidentally rewritten once on 7 November; 26,403 rows, same split counts and rates; additional analyses rerun, e1, e2, e3 and expectations identical.

```
python -m data_science.oulad.ek
python -m data_science.oulad.ek --e3
python -m data_science.oulad.figures --rule2 --ek
python scripts/arastirma_paketi.py
python -m pytest -q
```

## 10. Open items
- `get_risk` tool; "say up front if the asked month has no data" polish; consistent Turkish decimal commas.
- Audit cleanup (low-risk findings, `notebooks/_figtmp_*`, `explain.py`).
- Research page: interactive charts (S2–S5), mobile and accessibility (S6).
- Week 6 bug 4; Week 7 m5 and c4; pytest Starlette warning.

## 11. Week 12
- Security before deploy: SECRET_KEY, login counter, question length limit, log masking, `.env.example`, `.gitignore`; rerun the eval with the new data and DEMO_TODAY.
- Docker deploy on the Contabo VPS: all notebooks rerun and compared in a clean environment; plotting code moves to the package.
- README, KVKK scope, demo; future work: submission records, a comparison-free flag for parents, subgroup audit, the data needed for the teacher effect.
