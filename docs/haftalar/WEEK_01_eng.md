# Week 1 — Problem Definition, Architecture and Data Model

**Project:** Smart School Information System
**Scope:** Version 1 of the 12-week internship presentation program

---

## 1. Goal of this week

We design the project's architecture and data model this week. By the end
of this week **the code does not yet include an API** — only the database
schema, mock data, and the foundation of role-based access control will be
working.

## 2. Architecture decision: why PostgreSQL from the start

This project's core requirement is that a user (teacher, parent, student,
principal) can only access data within their own scope. We choose to
enforce this restriction not in application code (manually adding a
`WHERE` clause to every query), but **inside the database itself** — using
PostgreSQL's Row-Level Security (RLS) feature.

RLS lets a user's session declare a context ("this user's role is X, their
class is Y"), and the database then automatically returns only the
permitted rows on **every query, regardless of its shape**. This feature
doesn't exist in SQLite — only mature database engines like PostgreSQL
have it — so the project starts with PostgreSQL from day one, not SQLite.

This week sets up RLS policies, but no application code (FastAPI, the LLM)
uses them yet — we're proving they work correctly, independently, at the
database level. The API layer will be built on top of this foundation in
Week 2.

## 3. Deliverables

- [ ] PostgreSQL (a Docker container, a single `postgres:16` image)
- [ ] 5 SQLAlchemy models under `database/models/`: `User`, `Student`,
      `Teacher`, `Grade`, `Attendance`
- [ ] `database/init_db.py` — a script that creates the tables in
      PostgreSQL
- [ ] `database/seed_mock.py` — mock data with at least 10 students, 2
      teachers, 2 parents, and all 4 user roles
- [ ] `database/enable_rls.py` — Row-Level Security policies for the
      `students`, `grades`, `attendance` tables:
  - `students`: `principal` → all rows; `teacher` → only rows matching
    `class_name`; `parent`/`student` → only the row matching `id`
  - `grades`/`attendance`: only rows belonging to a student already
    visible in the RLS-filtered `students` table
- [ ] `backend/tests/test_rls.py` — tests proving RLS works correctly at
      the database level, independent of any API layer
- [ ] Architecture diagram and role/permission matrix

## 4. Out of scope (deliberately deferred)

- FastAPI / any API layer → Week 2
- Authentication (JWT/bcrypt) → Week 2
- Wiring RLS into application code (SQLAlchemy sessions) → Weeks 2–4
- LLM integration → Week 4
- Streamlit interface → Week 6

## 5. Acceptance criteria

1. The database comes up with `docker run ... postgres:16`.
2. `python database/init_db.py` runs without errors, creating all 5
   tables in PostgreSQL.
3. `python database/seed_mock.py` produces consistent, properly related
   (correct FKs) sample data.
4. `python database/enable_rls.py` enables RLS and defines policies for
   all 3 tables.
5. The tests in `backend/tests/test_rls.py` prove that changing the
   session variables (`app.role`, `app.class`, `app.student_id`) changes
   the row count returned from `students` correctly (`teacher` → 4,
   `principal` → 12, `parent` → 1).
6. The README explains in one paragraph what the project does and why it
   starts with PostgreSQL + RLS.

## 6. Demo flow for the presentation

1. Start PostgreSQL with `docker run`.
2. Run `init_db.py` → `seed_mock.py` → `enable_rls.py` in order.
3. Connect directly to the database with `psql`, run `SET LOCAL app.role =
   'teacher'; SET LOCAL app.class = '9-A';` then `SELECT COUNT(*) FROM
   students;` — show live that only **4** comes back.
4. On the same connection, try again with `SET LOCAL app.role =
   'principal';` — show that **12** comes back this time.
5. This is proof — with no application code (API, LLM) written yet —
   that the database itself correctly enforces role-based access.

## 7. Notes / rationale

- Setting up RLS policies this early (before the API) is deliberate:
  proving the security model works correctly at the database level,
  independent of application code, means everything built on top of it
  (the API, the LLM integration) benefits from this solid foundation.
- `requirements.txt` this week only lists `sqlalchemy`, `python-dotenv`,
  and `psycopg2-binary`; dependencies like `fastapi` or `anthropic` are
  not added yet.
- A single `docker run` command is used instead of Docker Compose —
  orchestration (multiple services, networking) is a later week's topic.
