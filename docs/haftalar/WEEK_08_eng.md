# Week 8 — Data Science I: Data, EDA and Feature Engineering

**Smart School Information System — Internship Project · Week 8 / 12**

## Goal and scope

To lay the groundwork for the Week 10 risk integration, a public student-performance dataset was explored and model-ready feature sets were produced. **No model was trained this week**; model comparison, cross-validation and SHAP come in Week 9. Application code, mock data and eval were kept out of scope.

## Dataset

| Item | Value |
|---|---|
| Source | Cortez & Silva (2008), UCI Machine Learning Repository, CC BY 4.0 |
| Total records | 1044 (Maths 395, Portuguese 649) |
| Missing values | 0 |
| Students in both subjects | 366 (via `student_key`) |
| Grade scale | 0–20 (G1, G2 in-term; G3 final) |

sha256 checksums of the downloaded files are stored in `data/raw/CHECKSUMS.txt` and verified on every run.

## Target definition

`at_risk = 1` if `G3 < 10`. This threshold matches our system's pass grade exactly: `G3 × 5 < 50 = PASS_GRADE`.

| Subject | Pass rate | Risk rate |
|---|---|---|
| Maths | 67.1% | 32.9% |
| Portuguese | 84.6% | 15.4% |
| Total | 78.0% | 22.0% (230 students) |

## EDA findings

Top 10 relationships with G3 (Pearson):

| Feature | r |
|---|---|
| G2 | 0.91 |
| G1 | 0.81 |
| failures | −0.38 |
| Medu | 0.20 |
| studytime | 0.16 |
| Fedu | 0.16 |
| Dalc | −0.13 |
| age | −0.13 |
| Walc | −0.12 |
| traveltime | −0.10 |

- **Leakage risk:** G2 (0.91) and G1 (0.81) almost determine the final grade. Two feature sets were therefore defined: **EARLY** (no G1 or G2, start-of-term early warning) and **MIDTERM** (G1 included, no G2). G3 is in neither set; this is enforced by tests.
- **Strongest non-grade signal:** past failures (failures, −0.38). Parental education and study time are weakly positive; alcohol, age and travel time are weakly negative.
- **Absence (corrected finding, see Bug record 1):** In the first analysis, `absences` was not among the 10 strongest relationships. However, all 53 G3=0 records fall in the 0-absence bucket and suppress the relationship. Excluding them, absence is a meaningful signal:

| Correlation (absences–G3) | Incl. G3=0 | Excl. G3=0 |
|---|---|---|
| Pearson | −0.05 | −0.22 |
| Spearman | −0.11 | −0.24 |

| Absences | Students (excl.) | Pass rate (incl.) | Pass rate (excl.) |
|---|---|---|---|
| 0 | 306 | 76.6% | 89.9% |
| 1–5 | 368 | 83.4% | 83.4% |
| 6–10 | 202 | 78.7% | 78.7% |
| 11–20 | 92 | 66.3% | 66.3% |
| 21+ | 23 | 52.2% | 52.2% |

  - Pass rate falls steadily as absence rises. Still, half of the 21+ group passes (n=23, small sample): absence alone does not justify a decision.
  - Implication for our system: use unexcused absences instead of the raw count (Ali: 14 = 8 unexcused + 6 excused).

Figures (`data_science/reports/figures/`): `g3_distribution_by_subject.png`, `g1_g2_g3_scatter.png`, `absences_vs_g3.png`, `failures_vs_pass_rate.png`, `studytime_vs_g3.png`, `numeric_correlation_heatmap.png`. Numeric summary: `data_science/reports/eda_summary.json`.

## Data quality and decisions

| Topic | Value | Decision |
|---|---|---|
| G3 = 0 | 53 records (5.1%) | Not removed; a `g3_zero` flag was added. All have 0 absences; the reason (missed exam, dropout) is not stated. Relationship analyses should also be run without them. |
| Shared students | 366 | The literature reports 382; matching columns differ. Used as GroupKFold groups in Week 9. |
| Missing values | 0 | No imputation needed. |

## Feature engineering

Derived features:

- `parent_edu_max`: higher of the parents' education levels
- `alcohol_total`: Dalc + Walc
- `support_any`: school or family support
- `has_failures`: any past failure
- `absences_log1p` and `absence_bucket`

Preprocessing (`build_preprocessor`):

- Binary categories are encoded as 0/1.
- Nominal categories are one-hot encoded (`handle_unknown="ignore"`).
- Ordinal columns are kept as is.
- The pipeline is returned **unfitted**; it will be fitted inside CV folds in Week 9, so no leakage occurs.

Outputs: `processed/features_early.parquet`, `processed/features_midterm.parquet`.

## Mapping to our system

| UCI feature | Our schema | Status |
|---|---|---|
| G1 / G2 | Grade average ÷ 5 | Derivable |
| absences | Attendance records (with excuse flag) | Available |
| failures | — | Missing |
| studytime, Medu/Fedu, support | — | Missing |

Our system only stores grades and attendance. The Week 10 risk indicator will therefore be designed as an **attention flag** shown with its reasons, not as a verdict. Detailed mapping: `data_science/feature_mapping.md`.

## Notebooks

- `notebooks/01_uci_eda.ipynb` (Turkish) and `notebooks/01_uci_eda_eng.ipynb` (English); HTML copies under `notebooks/html/`.
- Sections: dataset, target definition, G3 distribution, correlations, leakage, absence analysis, feature sets, conclusion.
- Logic is imported from the `data_science` package; numbers are not typed into markdown but read from cell outputs. Notebooks were executed from scratch and saved with outputs.

## How to run

```bash
python -m data_science.download
python -m data_science.eda
python -m data_science.features
```

## Verification

```
233 passed, 1 warning
```

- Tests use no network; they run on a 30-row synthetic fixture CSV.
- Both notebooks executed from scratch without errors via `jupyter nbconvert --execute`.
- Checked: target threshold (G3=9 → 1, G3=10 → 0), no G1/G2/G3 in the sets, NaN-free transform and unknown categories.
- The pytest warning has not been reviewed yet.

## UCI's limits, hypothesis and change of direction

**What UCI provides (a general risk signal):** Early grades strongly reflect the final (G1–G3 r = 0.81). Past failures are the strongest non-grade signal (r = −0.38). Absence is meaningful once G3=0 is excluded, but not decisive on its own.

**What UCI lacks (context):** The data covers one school year, two subjects and two schools. There is no course, teacher or exam context, and no exam dates or order, so no real early warning can be built. The sample is also small: about 678 unique students, about 230 at risk.

**Hypothesis:** Risk depends more on the course context than on a student's absolute grade. For example, one teacher's final exam was harder than others last year and many students' grades dropped. A student who was borderline in the first two exams is at higher risk in that course than a student with the same grades in another course.

**Decision:** UCI stays as the general (baseline) model. The context hypothesis is tested on a larger, time-stamped dataset, OULAD:

| Week | Step |
|---|---|
| 8 | UCI: general model baseline |
| 9 | OULAD: data and course-history features |
| 10 | Comparison: general vs course-history model (temporal test) |
| 11 | Applying the validated feature recipe in the system: risk tab |

**Principles:** Risk is an attention flag shown with its reasons, not a verdict. The system uses no sociocultural features; only grades, unexcused absence and course context. No data or model moves from OULAD into the system, only the validated feature recipe.

## Bug records

**Bug record 1: absence analysis**

- **Symptom:** In the first EDA, absence was not among the 10 strongest relationships with G3; it was concluded to be a "weak indicator".
- **Root cause:** All 53 G3=0 records fall in the 0-absence bucket. These records (possible missed exam/dropout) suppressed the relationship.
- **Fix:** Correlation and bucket analysis computed separately with and without G3=0 (notebook, section f).
- **Status:** Verified. Excluding G3=0, Pearson −0.22; pass rate falls from 89.9% to 52.2% across buckets.

## Open items

- Week 6 bug 4 (silent averaging in pivot): to be verified.
- Week 7 eval: m5 (causal speculation) and c4 (73.98 → "73") still open.
- The pytest warning will be reviewed.
- Alternative text missing on notebook figures (6 images).

## Week 9 plan

- Larger, time-stamped data: OULAD (Open University Learning Analytics Dataset)
- Course-history features: a student's grade relative to the course's past average
- Temporal split: train on 2013 presentations, test on 2014
- Presented in notebook `02`
