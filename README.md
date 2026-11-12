# Smart School Information System — Week 1

Week 1 of a 12-week rebuild of the [school-assistant](https://github.com/beraerr/school-assistant) project. This version establishes the **relational data model** for a school portal: users with four roles (`principal`, `teacher`, `parent`, `student`), teachers, students, grades, and attendance. There is **no API, UI, or authentication service yet** — only SQLAlchemy models, table creation, and seed data on local SQLite so later weeks can attach FastAPI, JWT login, RBAC, LLM queries, and Streamlit without renaming columns or relationships.

## Roles

| Role        | Purpose |
|------------|---------|
| `principal`| School-wide access (future admin views) |
| `teacher`  | Linked to a `teachers` row via `users.related_id` and `users.related_class` |
| `parent`   | Linked to a child student via `users.related_id`; `students.parent_id` points back to the parent user |
| `student`  | Linked to own `students` row via `users.related_id` |

## This week's scope

- `database/models/` — `User`, `Student`, `Teacher`, `Grade`, `Attendance`
- `database/init_db.py` — creates tables in `school.db` (override with `DATABASE_URL` in `.env`)
- `database/seed_mock.py` — sample data (≥10 students, 2 teachers, 2 parents, all roles)
- `docs/architecture.md` — layer diagram and role matrix preview

**Deferred:** FastAPI, JWT/bcrypt (passwords in `password_hash` are **plaintext placeholders** until Week 2), rule engine, LLM, Streamlit, Docker, PostgreSQL.

## Setup

```bash
cd week-01
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python database/init_db.py
python database/seed_mock.py
```

Inspect data (example from the presentation demo):

```bash
sqlite3 school.db "SELECT id, name, class_name FROM students WHERE class_name = '5-A';"
```

## Technologies (Week 1 only)

- Python 3.10+
- SQLAlchemy 2.x
- SQLite (`school.db`)
- python-dotenv (optional `DATABASE_URL`)
