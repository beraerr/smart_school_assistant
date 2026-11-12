# Week 3 — Rule Engine (Role-Based Access Control)

**Project:** Smart School Information System
**Previous state:** Week 2's FastAPI + JWT auth layer (`week3/week-03/`, a copy of Week 2)

---

## 1. Goal of this week

In Week 2 we could answer "who are you" (JWT token). This week we write the
rule engine that answers "what can you see." This engine is not wired to any
API endpoint yet — it's tested on its own, in isolation. Connecting it to a
real endpoint happens in Week 4, when LLM-generated SQL gets passed through
this engine.

## 2. Deliverables

- [ ] `backend/app/services/rule_engine.py` — a `RuleEngine` class with a
      static method that produces a bound-parameter SQL filter for each of
      the 4 roles
- [ ] Filter logic per role:
  - `principal` → no filter (`1=1`)
  - `teacher` → `class_name = :class_name` (`related_class` required)
  - `parent` → `id = :student_id` (`related_id` required — a parent
    account's `related_id` already stores the child's `students.id`, so the
    `parent` filter uses the exact same logic as `student`; the
    `students.parent_id` column is not used for this filter)
  - `student` → `id = :student_id` (`related_id` required)
  - Unknown role or missing `related_id`/`related_class` → `ValueError`
- [ ] `backend/tests/test_rule_engine.py` — unit tests (each role, error
      cases, unknown role)
- [ ] Integration tests — running a real SQLAlchemy query against Week 1–2's
      seed data and confirming the correct rows come back
- [ ] A test covering an SQL injection attempt (proving a value like
      `related_class = "9-A' OR '1'='1"` is treated as plain data)
- [ ] `requirements-dev.txt` — `pytest`, `pytest-cov`

## 3. Out of scope (deliberately deferred)

- A data-returning FastAPI endpoint like `/query` → Week 4
- Natural language → SQL, LLM integration → Week 4
- Streamlit interface → Week 6
- Rate limiting → Week 5

## 4. Acceptance criteria

1. `pytest backend/tests/ -v` — all tests return `PASSED`.
2. For the `teacher` role, `RuleEngine` produces a filter containing only that
   user's `related_class` value.
3. For the `parent`/`student` role, `RuleEngine` produces a filter containing
   only that user's `related_id` value.
4. No raw (interpolated) value appears anywhere in the generated SQL text —
   every variable is bound as `:param`.
5. Calling the `teacher` role without `related_class` raises `ValueError`.
6. The integration test confirms, against the real `school.db`, that
   `teacher1` sees only students in class 9-A and `parent1` sees only their
   own child.
7. `RuleEngine` is not yet wired to any FastAPI route — there is no new file
   under `backend/app/api/` for this week.

## 5. Demo flow for the presentation

1. Run `pytest backend/tests/test_rule_engine.py -v`, show all tests passing.
2. In a Python console, call
   `RuleEngine.build_student_filter("teacher", None, "9-A")` and print the
   resulting `(sql, params)` pair — show that the SQL contains `:class_name`
   and the raw `"9-A"` value lives in the `params` dict, not in the SQL text.
3. Repeat the same call with a malicious `related_class` value
   (`"9-A' OR '1'='1"`) — highlight that the SQL text doesn't change; the
   value is only ever carried inside `params`.
4. Show the integration test running against the real database, returning
   exactly 4 students (class 9-A) for `teacher1`.

## 6. Notes / rationale

- We deliberately don't wire `RuleEngine` to any endpoint this week. Reason:
  in Week 4 the LLM's generated SQL will also pass through this same engine,
  so proving the rule itself works correctly first — rather than building
  both at once — gives a more solid foundation.
- `pytest`/`pytest-cov` are kept in a separate `requirements-dev.txt`; these
  packages aren't part of the running application, only needed during
  development.
- Integration tests use the real `school.db` file, not a mock/fake database —
  a deliberate choice to prove the rule works correctly on real data, not
  just in theory.
