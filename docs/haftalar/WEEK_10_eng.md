# Week 10 — Data Science III: Does course context transfer?

## Summary
This week we tested the hypothesis the project has carried from the start: a student's risk depends on the course context, and a model that knows this context predicts better than one that looks only at the student.

The answer has two parts. **Supported:** the difference in risk between courses is large and real. **Not supported:** features built from a course's past runs did not help rank students more accurately within their own class; on the test term they made predictions worse (ROC AUC difference, hgb −0.010 [−0.012; −0.007]). There are two reasons: the course base rate drifts between terms, and the past signal is learned from very few terms.

These findings turned into a concrete design for the school system: **a transparent three-signal rule that flags the top 20% within each class.** The rule captures 95–96% of the model's hits. It shows no probabilities and produces no flags in a course without a graded exam.

## 1. Why this experiment?
In real life, risk may depend on the course, the teacher, even the teacher's approach in a given year. A student who is safe in one course with certain grades may be at risk in another course with a hard final. If so, a general model that looks only at the student will be wrong, and a context-aware model should do better.

OULAD lets us test part of this question:

| Dimension | OULAD counterpart | Testable? |
|---|---|---|
| Course | Module identity and past runs of the course | Yes |
| Term | Presentation (2013B … 2014J): a rough proxy for "that year's conditions" | Yes |
| Teacher | Not in the dataset | No |

The teacher dimension could not be tested with this data; it moves to future work.

## 2. Experiment design
One comparison is not enough to say "context helps": the same gain might come from simply knowing the course's name. We therefore built three arms, and added two extra checks after the first results.

| Set | What it knows | Question it asks |
|---|---|---|
| GENERAL | The student's assessment and activity trace (up to day 60) | Baseline |
| GENERAL_MODULE | + course identity | Is knowing the course enough? |
| HISTORY | + past runs of the course (assessment difficulty, past risk rate) | Does knowing the course's past help? |
| HISTORY_SLOT * | HISTORY without the past risk rate | Is the problem a single column? |
| GENERAL_REL * | Position within the class (rank percentiles) | Does context transfer as within-class rank? |

\* Added after the first test results were seen, and therefore **exploratory**. From this point on, the test term was frozen and the validation term was reported separately.

**Protocol.** Two model types (logistic regression, HistGradientBoosting). Tuning was done only within the training data and in time order: trained on 2013J, selected on 2014B by log loss. The model trained with the selected settings on all training data (2013J + 2014B) was evaluated once on 2014J. Uncertainty was estimated with a module-stratified bootstrap (B = 1,000, seed 42); differences between sets were computed as paired differences on the same samples.

## 3. Findings

### 3.1 Course history did not improve prediction
| Set | hgb ROC AUC [95%] | logreg ROC AUC | Brier (hgb) |
|---|---|---|---|
| GENERAL | 0.792 [0.783–0.801] | 0.786 | 0.177 |
| GENERAL_MODULE | 0.799 [0.790–0.808] | 0.805 | 0.175 |
| HISTORY | 0.783 [0.773–0.792] | 0.773 | 0.190 |
| HISTORY_SLOT | 0.783 [0.774–0.793] | 0.775 | 0.190 |
| GENERAL_REL | 0.804 [0.795–0.813] | 0.792 | 0.169 |

Paired difference HISTORY − GENERAL (ROC AUC): hgb −0.010 [−0.012; −0.007], logreg −0.013 [−0.015; −0.012]. The intervals exclude 0, and Brier also gets worse.

### 3.2 Bug or finding?
When the result went against the hypothesis, we questioned the code first:
- **Assessment matching is correct.** Assessments come in the same order across runs, only shifted by a few days.
- **The past risk rate takes only 8 distinct values in the training data.** The model learns this column from 8 presentations, not from 13,639 rows.
- **Risk fell over time.** It was 42.6% in train and 38.3% in test. In BBB, for example, the past rate is 0.42 and the actual test rate is 0.339.

There is no code bug; the finding is real.

### 3.3 Context exists in the base rate, but it drifts
![Actual rate and mean prediction by module in the test period](figures/fig02_oran_kaymasi_en.png)

*Each row is a module. Dots show the actual rate and the mean prediction for the general, module-aware, and history sets. Dotted lines join values in the same module.*

In AAA the actual rate is 0.256, while GENERAL predicts 0.476 and HISTORY 0.574; course identity (0.287) corrects the gap. In BBB all three sets predict between 0.52 and 0.57 against an actual rate of 0.339. The past risk rate pushes predictions up in the test term. **Decision:** the system does not show absolute probabilities.

### 3.4 The set leading on test comes last on validation
![Rankings change between validation and test: ROC AUC for five sets](figures/fig01_roc_egim_en.png)

*Each line joins validation and test ROC AUC for one feature set. The thick lines are the general and relative general sets; the others are thin. Only the test point has a ninety-five percent interval. The validation point has no interval.*

GENERAL_REL has the highest ROC AUC on test (0.804) and the lowest on validation (0.782). This set was designed after looking at test results. Its failure to hold up in an independent term shows that the test gain was largely specific to that term. **Decision:** GENERAL_REL was not adopted. **Lesson:** designing against the test set can pick a lucky winner.

### 3.5 Within a class, the sets are almost identical
| Set | Within-module ROC AUC, test 2014J | Within-module ROC AUC, validation 2014B |
|---|---|---|
| GENERAL | 0.796 | 0.810 |
| GENERAL_MODULE | 0.797 | 0.811 |
| HISTORY | 0.793 | 0.811 |
| HISTORY_SLOT | 0.794 | 0.811 |
| GENERAL_REL | 0.800 | 0.795 |

Values are unweighted means across modules (hgb); per-module n and positive counts are in notebook 03. Differences are a few thousandths, and the ordering changes between terms. **No context recipe consistently helped identify who is at risk in both terms.** Context matters at the level between courses, in the base rate, not in within-class ranking.

### 3.6 Unseen course
![Mean prediction and actual rate for a course unseen in training](figures/fig03_gorulmemis_ders_en.png)

*Each row is a course never seen in training. Dots show the actual rate and the mean prediction for the general and relative general sets. The highlighted row is the course with no graded assessment before the cutoff day.*

Each course was left out of training in turn (leave-one-module-out). Mean ROC AUC: GENERAL 0.784, GENERAL_MODULE 0.785, GENERAL_REL 0.787, HISTORY 0.782. Course identity does not transfer to a new course; differences are small and no intervals were computed in this analysis.

In GGG the model predicts a risk of ~0.93; the actual rate is 0.36. GGG has no graded assessment by day 60, and the model reads "no assessment yet" as "did not submit" (Week 9, data note 1). **Rule:** no flag is shown in a course with no exam yet.

### 3.7 What does the model rely on?
![Features the model relies on most](figures/fig05_shap_en.png)

*The left panel compares mean absolute SHAP across features. The right panel shows observed values of the feature with the highest mean absolute SHAP together with SHAP. Positive SHAP shows the direction in which the model increases predicted risk; it is not a causal effect.*

TreeExplainer for GENERAL hgb, on the full test term (8,837 rows). Mean |SHAP| (log-odds): `n_unsubmitted` 0.586, `score_mean` 0.462, `vle_days_to_cutoff` 0.443. Their counterparts in the school system are missed exams, grade average and attendance. SHAP describes the model's behaviour; it does not mean "not submitting causes risk".

### 3.8 Decision rule: top 20% within class
![Precision by flag rate for global and within-class ranking](figures/fig04_kapasite_en.png)

*Lines show precision as the flag rate changes. One ranks students together and the other ranks inside each module. The dashed line shows the selected flag rate, and the pale band shows the range where within-class ranking is ahead.*

At a 20% flag rate, precision is 0.797 with global ranking and 0.818 with within-class ranking. Within-class ranking leads between 10% and 35%; global ranking leads at 5% (0.984 / 0.962); from 45% the two are equal. Within-class rank is not affected by base-rate drift and gives every teacher the same follow-up capacity. There is a cost: precision drops in low-risk classes (AAA 0.62).

### 3.9 Bridge to the system: transparent rule vs model
The rule was fixed in advance, before any results were seen:
- In each class, take the rank percentiles of three signals: unsubmitted assessments, grade average (reversed) and active days (reversed).
- Flag the top 20% within the class by the mean of the three.
- Produce no flag in a course without a graded assessment.
- The rule is not trained and does not use the outcome (`at_risk`).

| Term | Rule precision | Model (GENERAL hgb) precision | Hits rule / model |
|---|---|---|---|
| 2014B | 0.900 | 0.934 | 975 / 1,012 |
| 2014J | 0.787 | 0.829 | 1,283 / 1,352 |

Within-class 20% flag; GGG excluded in both terms. The model leads in both terms, with a higher within-module ROC AUC in 11 of 11 module-terms (gap 0.001–0.029). The rule captures 95–96% of the model's hits.

The school system has no labelled history showing which students eventually failed, so a model was never an option there. What this comparison measures is the **cost of transparency**: about 4 points of precision. In return, the teacher can read the reasons behind every flag, and no data or model moves from OULAD into the system.

## 4. Decisions
| Decision | Evidence |
|---|---|
| HISTORY rejected | Paired difference negative for both model types; interval excludes 0 |
| GENERAL_REL not adopted | Lowest on validation; test gain is exploratory |
| Reference model: GENERAL hgb | Simple, stable across both terms, transferable to any course |
| No probabilities shown | The base rate drifts between terms |
| Top 20% within class | Capacity curve: within-class leads between 10% and 35% |
| Transparent 3-signal rule in the system | No labels at school; cost ~4 points of precision |
| No flag in a course without exams | GGG: ~0.93 predicted in an unseen course |

## 5. Answer to the hypothesis
- **Supported:** Risk differs a lot between courses, and the difference is real. Course identity improves calibration and overall ranking on the test term.
- **Not supported:** Knowing a course's past does not help rank students more accurately within their class. The past risk rate drifts over time and is learned from few terms.
- **Not testable:** The teacher and the teacher's approach in a given year (not in OULAD). Testable on school data as outcome labels accumulate.

In short: risk does depend on the course, but this information does not transfer from the course's past to the student. What works is judging a student within their own class.

## 6. Explanation log
While interpreting the findings we proposed two explanations; neither held up under a check. No unverified explanation was reported as a result.

| Guess | Check | Result |
|---|---|---|
| The drop comes only from the past risk rate | That column was removed (HISTORY_SLOT): result unchanged | Wrong: past assessment features do not generalise either |
| GENERAL_REL only misses the level; its ranking is sound | Ranking (ROC AUC) measured on validation: lowest | Wrong: the set was not adopted |

## 7. Bug records
**Bug 1 — figure alternative text**
- Symptom: the alt text of the unseen-course figure described the highlighted row as "the course left out of training".
- Root cause: in this analysis every row is a course unseen in training. GGG is highlighted for another reason: it has no graded assessment by day 60.
- Fix: title, alt text (TR/EN) and an explanatory note on the GGG row were updated.
- Status: verified (figures.json and the regenerated figure were checked).

## 8. Limitations
- One institution (the Open University), one country.
- Fail and Withdrawn are in the same class; they may be different processes.
- There is only one validation term; stability across terms rests on two points.
- No uncertainty intervals were computed for the LOMO results.
- The test term was seen more than once. This was for evaluation only; the sets added later are therefore marked as exploratory.
- SHAP is not causality.
- The school-schema counterpart of "missed exam", the rule's first signal, is not yet verified.

## 9. Outputs and verification
- **Code:** `model.py`, `relative.py`, `explain.py`, `figures.py`, `rule.py` under `data_science/oulad/`; reports under `data_science/oulad/reports/` (`model_metrics.json`, `explain.json`, `rule_metrics.json`, `figures/week10/`). `shap==0.54.1` added to requirements.txt.
- **Notebook:** `notebooks/03_oulad_model.ipynb`, `03_oulad_model_eng.ipynb` and the HTML exports under `notebooks/html/`. The notebook contains no model, metric or plotting code; everything is called from the package, and the same PNGs are used in this report and in the deck.
- **Tests:** 266 passed, 1 warning.
- **Notebook execution:** executed from scratch in the user's terminal (3 min 42 s for both notebooks); 0 error cells. The HTML files were exported after the notebooks, with no alt text warning. The values in the OZET cell match the raw outputs exactly.

```
python -m data_science.oulad.model --lomo
python -m data_science.oulad.explain
python -m data_science.oulad.figures
python -m data_science.oulad.rule
python -m pytest -q | tail -3          # 266 passed, 1 warning
```

## 10. Open items
- `n_unsubmitted` ↔ "missed exam": to verify in the school schema (the rule's first signal).
- The pytest warning (StarletteDeprecationWarning, httpx) is not resolved.
- Alternative text: solved in notebook 03; still open in 01 and 02.
- Week 6 bug 4; Week 7 m5 and c4 open.

## 11. Week 11
- Risk tab = the transparent rule: top 20% within class with a reason text for every flag; no probabilities; no flag in a course without exams.
- `get_risk` tool for the assistant: respects RLS, invents no causes.
- Data Science tab (notebook summaries), tests, Docker, security.
