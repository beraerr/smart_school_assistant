# Week 9 — Data Science II: OULAD

## Summary
The Open University Learning Analytics Dataset (OULAD) was added to test the course-context hypothesis. The data was downloaded and verified, an early-warning sample was built with a day-60 cutoff, general and course-history features were produced, a leakage-free temporal split was created, and the `02_oulad_eda` notebook (TR/EN) was prepared. No model was trained this week; the comparison follows in Week 10.

## Work done
- **9a — Data:** `data_science/oulad/` package (`download`, `load`, `vle`, `validate`). Archive sha256 pinned: `f2ed1902616c1fe8d2824d872c0b7d2d72be435bf0124d077044fe4be2c6d3e4`. `studentVle` was read in chunks and reduced to a daily summary at `(module, presentation, student, day, activity type)` level (`student_vle_daily.parquet`).
- **9b — Features:** `dataset.py`. Unit `(code_module, code_presentation, id_student)`. Target `at_risk = final_result ∈ {Fail, Withdrawn}`. `CUTOFF_DAY = 60`. Output `features_cutoff60.parquet` (26 columns) and `feature_list.md`.
- **9c — Notebook:** `notebooks/02_oulad_eda.ipynb`, `02_oulad_eda_eng.ipynb` and HTML exports under `notebooks/html/`.

## Data
| Table | Rows | Note |
|---|---|---|
| studentInfo | 32,593 | Key unique; imd_band 1,111 missing |
| studentRegistration | 32,593 | date_registration 45, date_unregistration 22,521 empty |
| assessments | 206 | date 11 missing |
| studentAssessment | 173,912 | score 173 missing |
| vle | 6,364 | week_from/week_to 5,243 empty |
| courses | 22 | — |
| studentVle | 10,655,280 | Read in chunks |

Chunked summary check: the raw table and the daily summary match exactly in rows (10,655,280) and total clicks (39,605,099).

## Sample and rules
- Only assessments dated and submitted by day 60; final exam (`Exam`) excluded. Clicks up to day 60.
- Students unregistered before day 60 were excluded: 32,593 → 26,403 (6,190 records). Later unregistrations stay in the sample with `at_risk = 1`.
- Columns not used: sociocultural columns (`SOCIO_COLUMNS`), `num_of_prev_attempts`, `studied_credits`.
- Course history: for presentation P, only strictly earlier presentations of the same module. Assessment matching key `(module, type, order within presentation)`. Without history, `has_history = 0` and history columns stay NaN.

## Split
| Split | Presentations | Rows | at_risk | Has history |
|---|---|---|---|---|
| history | 2013B | 3,927 | 46.7% | 0.0% |
| train | 2013J + 2014B | 13,639 | 42.6% | 74.1% |
| test | 2014J | 8,837 | 38.3% | 100.0% |

## Course context (descriptive)
- Across all records, the Fail + Withdrawn rate ranges between modules from 29.0% (AAA) to 62.2% (CCC). Presentations of the same module differ by at most 6.5 points (EEE).
- In the sample, the lowest rate is AAA 2013J (23.4%) and the highest DDD 2013B (52.6%).
- This is a descriptive sign that course history carries information, not evidence. The evidence will come from the Week 10 model comparison.

## Missing-value consistency
- `hist_module_risk_rate` 7,465 missing = history 3,927 + train without history 3,538.
- `hist_slot_mean` 8,952 = 7,465 + 1,487 (data note 1).
- `score_weighted_mean` 4,172 = `score_mean` 3,995 + 177 (data note 2).
- Others: `score_vs_hist` 10,046, `vle_days_to_cutoff` 564, `date_registration` 7.

## Data notes (not bugs)
1. **GGG 2014B / 2014J:** all 1,487 rows have `n_expected = 0` (790 + 697). These presentations have no graded assessment by day 60. Only the activity signal exists at the cutoff.
2. **BBB 2014J:** a TMA with weight 0 falls before day 60. For the 177 students who submitted only that one, the weighted mean is undefined (NaN is correct).

## Bug records
**Bug 1 — test environment**
- Symptom: pytest stopped at collection (`ModuleNotFoundError: sklearn`); same error in the Week 8 folder.
- Root cause: scikit-learn was not installed in the shared virtual environment used by all weeks.
- Fix: `pip install -r requirements.txt` in the shared environment.
- Status: verified (237 passed after 9a, 243 passed after 9b).

## Verification
```
python -m data_science.oulad.download          # raw csv mevcut, checksum dogrulandi
python -m data_science.oulad.vle
python -m data_science.oulad.dataset           # features rows=26403 cols=26
python -m data_science.oulad.validate --features
python -m pytest -q | tail -3                  # 243 passed, 1 warning
```
- New tests use no network (9a: 4, 9b: 6).
- Both notebooks executed from scratch via nbconvert; 0 error cells. The OZET values in the last cell match the validate output.

## Mapping to the school system
| OULAD | Our counterpart | Status |
|---|---|---|
| score_mean | Grade average | Available |
| vle_* | Unexcused absence (approximate) | Approximate |
| n_unsubmitted | Missed exam | To verify |
| delay_mean | — | Missing |
| hist_* | Past-term grades | Synthetic (W10) |
| Sociocultural | — | Not used |

## Open items
- pytest warning identified: `StarletteDeprecationWarning` (httpx with the starlette test client). Not yet resolved.
- Alternative text missing on notebook figures: 6 in 01, 7 in 02_eng (nbconvert warning).
- Week 6 bug 4 (silent averaging in pivot) to be verified; Week 7 m5 and c4 open.

## Week 10
- General vs course-history model comparison, same test (2014J), uncertainty intervals and SHAP.
- Feature subset compatible with the system.
- Synthetic school-history generator (mock data untouched, separate file).
