# Week 4 — Natural Language → SQL

**Project:** Smart School Information System
**Previous state:** Week 3's safe RLS context (`week04/week-04/`, a copy of Week 3)

---

## 1. Goal of this week

In Weeks 1-3 we set up role-based access at the database level, carried
the context into the API, and made that context injection-safe. But no
real data-returning endpoint existed; there was only a temporary
`/debug/students`.

This week the first real endpoint arrives: `POST /query`. The user asks a
question in natural language, Claude generates SQL, the SQL is
validated and then run **as-is** under the RLS context. We don't modify,
wrap, or rewrite the SQL Claude produces: the database's RLS policies
decide which rows come back.

## 2. Three layers of defense

| Layer | What it stops | Example |
|---|---|---|
| Validation (`sqlglot`) | SQL that should never run | `DROP TABLE`, multiple statements, `users` |
| Database privileges (least privilege) | Access to sensitive tables even if validation were skipped | `SELECT * FROM users` as `school_app` |
| RLS | Unauthorized rows | A teacher writing `SELECT * FROM students` still sees 4 rows |

The `users` table holds password hashes and has no RLS. So we don't rely
on validation alone: the `school_app` role has no privileges at all on
`users` and `teachers`, and only `SELECT` on `students`, `grades`,
`attendance`.

## 3. Deliverables

- [ ] `database/enable_rls.py` update: least privilege for `school_app`
- [ ] `backend/app/services/llm_service.py` —
      `translate_question_to_sql(question, client=None) -> str`;
      `temperature=0`; schema and rules in the prompt; markdown code
      fence cleanup; a fake client can be injected
- [ ] `backend/app/core/sql_safety.py` — `validate_select_only(sql)`;
      with `sqlglot`: single statement, SELECT, only
      `students`/`grades`/`attendance`; pure Python
- [ ] `backend/app/api/query.py` — `POST /query`; the SQL runs as-is in
      the `get_db_with_context` session; a 5-second `statement_timeout`;
      at most 500 rows; the generated SQL is not placed in the response,
      only logged; an Anthropic 529 becomes a 503
- [ ] `config/settings.py` — `ANTHROPIC_API_KEY`, `LLM_MODEL`
- [ ] `requirements.txt` — `anthropic`, `sqlglot`
- [ ] `backend/app/api/debug.py` and its tests are removed; the RLS
      context tests run through `/query`

## 4. Out of scope (deliberately deferred)

- Intent detection (chat or data query), explanation text → Week 5
- Rate limiting, structured logging → Week 5
- Prompt improvements (name search, identity columns) → Week 5
- Streamlit interface → Week 6

## 5. Acceptance criteria

1. `POST /query` with a valid token returns `200` and a result list.
2. The same SQL (`SELECT * FROM students`) gives `principal` 12,
   `teacher` 4, `parent` 1, `student` 1 rows; the aggregate query
   (`SELECT COUNT(*) AS total FROM students`) gives the same numbers.
3. SQL touching the `users` or `teachers` table returns `400`; also, a
   direct `SELECT * FROM users` as `school_app` gives a database
   privilege error.
4. `DROP TABLE` and multiple statements are rejected with `400`.
5. A query running over 5 seconds is cancelled; at most 500 rows are
   read.
6. The generated SQL does not appear in the response.
7. An Anthropic 529 error returns `503` with a clear message.
8. `/debug/students` is removed; Weeks 2-3's RLS context tests run
   through `/query` and the results (4 / 12 / 1 / 1) are unchanged.
9. All tests pass without an API key.
10. The code contains no tool or model self-references; `.gitignore`
    contains `.env`.

## 6. Demo flow for the presentation

1. Log in as `teacher1` and ask "Who are the students in my class?";
   only the 9-A students come back.
2. Ask the same question as `principal`; 12 students come back.
3. Show the generated SQL in the server log; stress that it is not in
   the response.
4. Show a request asking for the `users` table: `400`; then show the
   database-level privilege error.

## 7. Notes / rationale

- Validation only asks "is this SQL fit to run"; "which rows are
  visible" is the database's job. Thanks to this split, every SQL shape
  (aliases, JOINs, aggregates, subqueries) is filtered the same way.
- RLS filters rows but doesn't bound a query's cost. The time and row
  limits are therefore a separate safeguard.
- The `client=None` parameter and `monkeypatch` let code that depends on
  Claude be tested without Claude.
- `ANTHROPIC_API_KEY` is read only from `.env`.
