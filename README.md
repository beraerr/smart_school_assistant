# Smart School Information System — Week 1

Week 1 of a 12-week rebuild of the [school-assistant](https://github.com/beraerr/school-assistant) project. This version establishes the **relational data model** for a school portal: users with four roles (`principal`, `teacher`, `parent`, `student`), teachers, students, grades, and attendance. There is **no API, UI, or authentication service yet** — only SQLAlchemy models, table creation, seed data, and PostgreSQL row-level security so later weeks can attach FastAPI, JWT login, RBAC, LLM queries, and Streamlit without renaming columns or relationships.

Role checks will eventually be enforced **in the database**, using PostgreSQL row-level security, not only in application code. SQLite has no equivalent, so the project uses PostgreSQL from the start instead of migrating off SQLite in a later week.

## Roles

| Role        | Purpose |
|------------|---------|
| `principal`| School-wide access (future admin views) |
| `teacher`  | Linked to a `teachers` row via `users.related_id` and `users.related_class` |
| `parent`   | Linked to a child student via `users.related_id`; `students.parent_id` points back to the parent user |
| `student`  | Linked to own `students` row via `users.related_id` |

## This week's scope

- `database/models/` — `User`, `Student`, `Teacher`, `Grade`, `Attendance`
- `config/settings.py` — `DATABASE_URL` from `.env`
- `database/init_db.py` — creates the five tables
- `database/enable_rls.py` — row-level security policies (after `init_db.py`; before or after seed)
- `database/seed_mock.py` — sample data (≥10 students, 2 teachers, 2 parents, all roles)
- `backend/tests/test_rls.py` — proves the policies with no FastAPI layer
- `docs/architecture.md` — layer diagram and role matrix preview

**Deferred:** FastAPI, JWT/bcrypt (passwords in `password_hash` are **plaintext placeholders** until Week 2), rule engine, LLM, Streamlit, Docker Compose.

## Setup

PostgreSQL 16 (one container, no Compose):

```bash
docker run --name school-postgres \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=school \
  -p 5432:5432 \
  -d postgres:16
```

```bash
cd week-01
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` in the week-01 root:

```text
DATABASE_URL=postgresql://postgres:devpassword@localhost:5432/school
```

Create tables, policies, and sample rows. `enable_rls.py` can run before or after `seed_mock.py`; it must run after `init_db.py`. Seeding connects as the superuser in `DATABASE_URL`, and superusers bypass row-level security, so either order loads the same data.

```bash
python database/init_db.py
python database/enable_rls.py
python database/seed_mock.py
```

`enable_rls.py` also creates the login role `school_app` / `devpassword`. That role is not a superuser and does not bypass RLS. Queries that should be filtered — including `backend/tests/test_rls.py` — connect as `school_app` and set `app.role` (plus `app.class` or `app.student_id`) for the transaction.

Prove the policies:

```bash
pytest backend/tests/ -v
```

Inspect data as the superuser (every row is visible):

```bash
psql "postgresql://postgres:devpassword@localhost:5432/school" \
  -c "SELECT id, name, class_name FROM students WHERE class_name = '5-A';"
```

Same table as `school_app`, limited to class 9-A (4 students):

```bash
psql "postgresql://school_app:devpassword@localhost:5432/school" \
  -c "BEGIN; SET LOCAL app.role = 'teacher'; SET LOCAL app.class = '9-A'; SELECT id, name, class_name FROM students; COMMIT;"
```

## Technologies (Week 1 only)

- Python 3.10+
- SQLAlchemy 2.x
- PostgreSQL 16 (`psycopg2`)
- python-dotenv (`DATABASE_URL`)
