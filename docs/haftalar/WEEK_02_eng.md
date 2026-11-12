# Week 2 — FastAPI Skeleton and Authentication

**Project:** Smart School Information System
**Previous state:** Week 1's PostgreSQL + Row-Level Security setup (`week2/week-02/`, a copy of Week 1)

---

## 1. Goal of this week

In Week 1, we proved the database itself correctly enforces role-based
access — but no user could log in, and there was no concept of "who is
making this request" anywhere. This week adds FastAPI + JWT
authentication, and — most importantly — sets up **a mechanism that
declares the logged-in user's context (role, class, student id) to the
PostgreSQL session on every request**. This means Week 1's database-level
proof will now also be verified through a real API request.

## 2. Deliverables

- [ ] `backend/app/main.py` — FastAPI app, router registration, `/health`
- [ ] `backend/app/core/security.py` — `verify_password`,
      `get_password_hash`, `create_access_token`, `decode_access_token`
- [ ] `backend/app/api/auth.py` — `POST /auth/login`; the JWT payload now
      carries `sub`, `role`, `related_class`, `related_id`
- [ ] `backend/app/api/dependencies.py`:
  - `get_current_user()` — token verification
  - `get_db_with_context()` — **the most important piece this week**:
    opens a separate, restricted `school_app` database connection, runs
    `SET LOCAL app.role`, `app.class`, `app.student_id` in the same
    transaction, then hands that session to the endpoint
- [ ] `config/settings.py` — `APP_DATABASE_URL` (not a superuser — a
      separate connection string using the `school_app` role)
- [ ] `backend/app/api/debug.py` — a **temporary**
      `GET /debug/students` endpoint, only to prove the context chain
      works end to end (will be removed once the LLM arrives in Week 4)
- [ ] Converting Week 1's plaintext seed passwords to bcrypt hashes
- [ ] `requirements.txt` update: `fastapi`, `uvicorn[standard]`,
      `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`

## 3. Out of scope (deliberately deferred)

- Natural language → SQL, LLM integration → Week 4
- Any data-returning endpoint beyond `/debug/students` → Week 4
- Streamlit interface → Week 6
- Rate limiting, CORS hardening → later, once scope settles

## 4. Acceptance criteria

1. `uvicorn backend.app.main:app --reload` starts without errors;
   `/docs` (Swagger UI) is reachable.
2. Each of the 4 roles (`principal`, `teacher1`, `parent1`, `student1`)
   returns `200` with a valid JWT when posting the correct password to
   `POST /auth/login`.
3. An incorrect password returns `401 Unauthorized`.
4. Calling `GET /debug/students` with a valid token returns a row count
   that exactly matches Week 1's `test_rls.py` results: `principal` →
   12, `teacher1` → 4, `parent1` → 1, `student1` → 1.
5. The `school_app` database role is **not a superuser** — this is the
   precondition for RLS to actually be enforced (see Week 1's notes:
   superusers bypass RLS automatically).
6. `APP_DATABASE_URL` is read only from `.env`, never hardcoded in
   source.

## 5. Demo flow for the presentation

1. Log in as `teacher1` via `POST /auth/login`, get a token.
2. Call `GET /debug/students` with that token — show that only **4**
   rows (class 9-A) come back.
3. Repeat the same request with a `principal` token — show that **12**
   rows come back this time.
4. This proves that what we showed manually with `psql` in Week 1 now
   works exactly the same way through a real, authenticated HTTP
   request.

## 6. Notes / rationale

- `get_db_with_context()` using a separate connection (`school_app`) is
  deliberate: administrative scripts like `init_db.py`/`seed_mock.py`
  continue running as the superuser (creating tables, defining RLS
  policies requires superuser privileges), but **real application
  traffic must never use a superuser connection** — otherwise RLS gets
  silently bypassed.
- Keeping `/debug/students` in its own file (`debug.py`) is deliberate —
  removing this temporary code in Week 4 will be as simple as deleting
  one file, without touching the real query logic at all.
- By the end of this week, Week 3's original plan (building a
  `RuleEngine` class) no longer applies — that job is now done by
  PostgreSQL itself, at the database level. Week 3's scope will be
  re-evaluated.
