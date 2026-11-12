# Week 7 — Security, Evaluation and the Conversational Assistant

**Project:** Smart School Information System
**Previous state:** Week 6's system with an interface (`week07/week-07/`, a copy of Week 6)

---

## 1. Goal of this week

In Weeks 1-6 every layer was verified by its own tests, but the system as a
whole was never tested as an attacker would, and the assistant's behaviour
was never measured systematically. This week no new user feature is added
at first: (1) we build a threat model with a test for each threat, (2) we
build an evaluation (eval) set that measures the assistant's behaviour.
Live testing then also pushed the endpoint to become a conversational
assistant (section 9).

## 2. Key hypothesis: privilege escalation through the model's SQL

RLS policies read the session setting (`app.role`). Validation only
checked "a single SELECT, allowed tables"; it did not look at functions. A
single SELECT like this could therefore pass validation:

```sql
WITH x AS (SELECT set_config('app.role','principal',true))
SELECT s.* FROM students s, x
```

This was a **hypothesis, not a proven hole.** Order of work: first try to
reproduce it with a test; if reproduced, close it; if not, document why it
is safe. Either way a permanent test and a function allowlist remain:
every unknown function is rejected.

## 3. Deliverables

- [ ] `backend/app/core/sql_safety.py` — function allowlist (`COUNT, SUM,
      AVG, MIN, MAX, ROUND, LOWER, UPPER, COALESCE`, date functions);
      every function not on the list is rejected (including `set_config`,
      `current_setting`, `pg_*`, `lo_*`, `dblink`)
- [ ] `backend/tests/test_adversarial.py` — adversarial SQL via a fake
      client: `set_config` (plain, CTE and subquery forms), `pg_sleep`,
      `current_setting`; each returns 400; no role goes beyond its own
      visibility (4 / 12 / 1 / 1)
- [ ] `student_rank` attack tests: cannot be called for another student
      (the identity is read from the session), no `PUBLIC` privilege, fixed
      `search_path`, no other student's individual data in the output;
      explicitly added to the function allowlist
- [ ] Login security: an unknown user and a wrong password give the same
      `401`; a per-username login rate limit (`429` when exceeded); a
      `CORS_ORIGINS` setting (`allow_origins=*` is removed)
- [ ] Log/response hygiene tests, also for `/auth/login`: no JWT, password
      or API key in any response or log
- [ ] `eval/questions.json` and `eval/run_eval.py` (runs against the
      running API with the real model and writes an `eval/report.md`
      pass/fail table; not part of pytest)
- [ ] `docs/SECURITY.md` — threat model table: threat, defending layer,
      proving test; known limitations

## 4. Out of scope

- New user features, interface changes (until the assistant work in
  section 9)
- Distributed rate limiting (Redis) and real deployment hardening →
  Week 12
- A subject-teacher model → future work

## 5. Acceptance criteria

1. SQL with `set_config` (plain, CTE and subquery forms) is rejected with
   `400`; in no test does a `teacher` see more than 4 students.
2. Functions on the allowlist run, functions not on it are rejected.
3. An unknown user and a wrong password return the same `401` body.
4. Consecutive wrong attempts for the same username are limited (`429`).
5. CORS origins are read from a setting.
6. No JWT, password or API key appears in any response or log.
7. The eval set runs and produces a report; failing items are listed
   openly in the report (not hidden).
8. All tests pass without an API key.
9. The code contains no tool/model self-references.

## 6. Demo flow

1. An adversarial question is typed; even if the model produces
   `set_config`, validation returns 400 and the user sees no extra rows.
2. The same question as `teacher1`: still 4 rows.
3. A wrong password and an unknown user: the same response.
4. The eval report is shown: how many questions passed, which failed and
   why.

## 7. Notes

- The allowlist is deliberately strict: if the model needs a new
  function, the need is verified and the function is added to the list.
- The eval set turns "does the model work correctly" from one-off tries
  into a repeatable measurement. Because the model can produce different
  SQL for the same question, results can change over time; the report is
  stored with the date and model name.
- The findings of this week are documented openly: what was tried, what
  was found, how it was closed.

## 8. Result: the hypothesis was confirmed

- **Finding:** `WITH x AS (SELECT set_config('app.role','principal',true))
  SELECT s.* FROM students s, x` (and the `WHERE (SELECT set_config(...))`
  form) returned 12 rows in the `teacher` context; in the same session a
  normal query returned 4. Cause: the RLS policy reads
  `current_setting('app.role')` during the scan; `set_config` in the same
  statement turns it into `principal` inside the transaction, and the scan
  sees the new role.
- **Scope:** the hole had existed since the `/query` endpoint arrived
  (Week 4); it was found in this week's security review. Validation only
  checked a single SELECT and allowed tables, not functions.
- **Fix:** `sql_safety` ties every function call in the parse tree to an
  allowlist; `set_config`, `current_setting`, `pg_*`, `lo_*`, `dblink` are
  rejected. The only table function allowed in `FROM` is `student_rank`.
- **Proof:** adversarial SQL returns 400 on `/query`; visibility does not
  go beyond 4 / 12 / 1 / 1. Tests: 168 passed. An unknown user and a wrong
  password give the same 401; after five wrong attempts, 429.
- **Eval:** 25 / 25 in the first live run (model
  `claude-sonnet-4-5-20250929`, report `eval/report.md`). The model did not
  produce `set_config` under adversarial prompts; but the real guarantee
  is the validation layer, not the model's behaviour. At that point the
  eval set did not yet measure conversational quality (follow-up
  questions, out-of-scope questions, questions asking for commentary).

## 9. The conversational assistant

Live trials showed that the SQL-translator approach was insufficient for
natural conversation (stock texts, follow-up questions not working,
irrelevant rows for questions with no answer in the database). This week
`/query` was turned into a tool-using assistant: the model asks for data
only through the `run_sql` tool; every executed query goes through the
same validation, allowlist, RLS, 5-second limit and 500-row limit; there
are at most 3 tool calls per question. Conversation history (the last 6
messages) is untrusted input. The separate intent call, the stock chat
text and the comparison refusal were removed. An extra database function:
`class_teacher()` (the class teacher's name). Result rows are sent to the
model's API; with real data this would require KVKK/GDPR compliance
(`docs/SECURITY.md`).

## 10. Bugs found in live testing and their fixes

1. **Silently wrong class average** (verified, eval). Symptom: Ali and the
   class average were the same (69.79); the real class average was 74.75
   (with that day's seed data; the data was later frozen, see 8 below).
   Root cause: in the parent account RLS shows only the child's grades;
   with plain SQL a "class average" again gives the child's own average.
   Because it raised no error, it was the most dangerous kind. Fix:
   class/school-wide figures only through `student_rank`; a
   `scope_warning` on aggregate results for parent/student; the eval
   compares with the real value via `truth_sql`.
2. **Conflicting rules: pass grade** (verified, eval). Symptom: "What is
   the pass grade?" got "it is not in the database". Root cause: the schema
   summary listed the pass grade under "DOES NOT EXIST". Fix: school policy
   through `PASS_GRADE` (50, per the Ministry of Education regulation; the
   notice that class-passing has extra rules is kept). Because the 5-point
   conversion could not be verified, `GRADE_LABELS` is left empty.
3. **The eval checker raised false alarms** (verified). The first full run
   showed 51/64; the number check only looked at the last query's rows and
   treated "74,10" and 74.1 as different numbers. Every executed query is
   now re-run under the same `school_app` and RLS context and numbers are
   compared by value.
4. **Robotic tone** (partial). "I can't give advice" retreats, stock
   answers with bold headings. The prompt now has short data-grounded
   support, a school-counsellor suggestion, and opening with an
   understanding sentence. Open: the model can still speculate about
   causes ("Maths could be the reason for losing interest in school").
5. **The model counts by itself** (verified, eval). Symptom: it counted
   "4 students" from a 60-row list; the number was right but its source
   was not a query. Fix: `distinct_counts` per column added to the tool
   result; the model takes counts from `row_count`, `total_students` and
   `distinct_counts`.
6. **The eval ran blind** (verified): it ignored `Retry-After` and wrote no
   progress. Fixed.
7. **Inconsistent absence data** (verified). Symptom: for Ali the recorded
   total was 3 against 10 non-attending records in attendance (old seed
   data); the assistant gave conflicting numbers. Root cause: the seed
   generated `total_absences` and the attendance records independently at
   random (10 of 12 students mismatched). Fix: `total_absences` is now the
   number of non-`present` attendance records; the schema summary defines
   the total and the detail.
8. **The seed changed the data on every run** (verified). Symptom: after
   re-running the seed, Ali's average moved from 69.79 to 79.05 and the 9-A
   average from 74.75 to 76.93. Root cause: the seed was not fixed and the
   dates were computed backwards from today. Fix: the data was frozen into
   `database/mock_data.json` (absolute dates); the seed loads from this
   file. The data digest (md5) is identical across three runs. Lesson:
   figures in documents depend on the data; figures written before the
   data is frozen go stale.
9. **A parent-style address to a student** (verified, eval). Symptom: in a
   student account, "talk to your child". Fix: role-based address rules and
   a forbidden-phrase check in the eval.
10. **The eval ran on old code** (verified, process lesson). Symptom: after
    the fixes, the eval repeated the same failures (z2, m1). Root cause: the
    server had been started without `--reload` before the fixes, so the
    eval measured old code. Fix: the server was restarted. Lesson: an eval
    result is only meaningful if the measured server is known to run the
    current code.

## 11. Eval result (frozen)

Last full live run: **59 / 65** (model `claude-sonnet-4-5-20250929`, judge
on; report `eval/report.md`, answer texts `eval/answers.md`). The six
remaining items:

- **d1** (false alarm, verified): the judge said the counts were not in the
  rows; but the numbers in the answer match the database exactly (Ali 14 =
  8 unexcused + 6 excused, Zeynep 13 = 7 + 6, Mehmet 9 = 6 + 3, Kerem 9 =
  4 + 5). The judge had only seen the first rows.
- **c4** (small model error, known limitation): in "a 73-82 band" the
  maths value 73.98 was truncated to "73" (74 when rounded). The number
  checker caught it correctly; harmless but inconsistent.
- **z2** (real bug, fixed): for a relative-date question ("yesterday",
  "this week") the assistant said "no data" although data existed. Root
  cause: the model does not know today's date and the result was cut at 50
  rows. Fix: a reference date and the data range are added to the context;
  "no data" is not said when the result is truncated.
- **m1** (real bug, fixed): in a follow-up asking about two subjects,
  only one was answered. Fix: a prompt rule (answer every topic asked).
- **m5** (known limitation): on an emotional topic, after the grades are
  shown, the model may still speculate about causes; a prompt rule is not a
  guarantee.
- **s3** (the check was too strict, fixed): the word "absence" was
  forbidden in the first answer, while the real rule is that no data is
  used in the first answer (already ensured by the "no query in the first
  turn" check). The rule is narrowed to no digits and no causal claims.

**Re-run:** after the fixes were applied and the server was restarted,
`z2`, `m1`, `s3` (and `d1`) were re-run and passed. The full eval was not
re-run after these fixes; the prompt changes may have affected other items
(not measured). Remaining open: `m5` and `c4`. The eval is frozen from
this point on: re-running it costs extra tokens and time, and the items
above are written into the report without being hidden.

## 12. Changed and developed technologies

| Technology | What changed | Why |
|---|---|---|
| Tool-using assistant (tool use) | Instead of an SQL translator the model calls `run_sql`, sees the result and writes the answer in natural language; the last 6 messages are context | Follow-up questions, honest answers, a natural tone |
| Function allowlist (`sqlglot`) | An allowlist instead of a denylist | The privilege escalation through the model's SQL is closed |
| `SECURITY DEFINER` functions | `student_rank`, `class_teacher`: identity is read from the session | A parent sees their child's rank; nobody else's data is opened |
| Chat interface (Streamlit) | `st.chat_message`, `st.chat_input`; table and SQL in expandable sections | A conversation experience |
| Eval set + LLM judge | 65 questions; real values via `truth_sql`, tone and honesty via a judge | Assistant quality is measured repeatably |
| Frozen mock data | `database/mock_data.json`, absolute dates | Figures and tests are reproducible |
| Policy through configuration | `PASS_GRADE`, `REFERENCE_DATE`, `SHOW_SQL`, `CORS_ORIGINS` | Policy lives in settings, not code |
| Login hardening | Uniform 401, per-username rate limit, allowed CORS origins | Brute force and username leakage |
