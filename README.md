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
- `database/seed_mock.py` — loads the fixed sample in `database/mock_data.json` (≥10 students, 2 teachers, 2 parents, all roles)
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

## Reproducible mock data

`database/seed_mock.py` does not invent rows. It loads students, teachers, grades, attendance, and users from the fixed file `database/mock_data.json`. Dates in that file are absolute (`YYYY-MM-DD`). The known demo passwords are stored there in plain text and hashed when the seed runs. Loading the file again inserts the same rows, so averages and counts stay reproducible. `python database/export_mock_data.py` rewrites the file from the current database.

## Rate limiting

`/query` allows 10 requests per user inside a 60-second sliding window. The limiter keeps its counters in memory and is per process: counts are not shared across processes, workers, or restarts.

## Generated SQL

A `/query` response that ran one or more statements includes them as a list in `sql`. Replies that never ran a statement omit it. Set `SHOW_SQL=false` in `.env` to leave the field out of every response. The server log still records the statements that ran.

## student_rank

`student_rank` is `SECURITY DEFINER` because a parent or student session, under row-level security, can read only one student. A class or school rank has to be computed with the function owner's rights. The student id is not a parameter: the function reads `app.student_id` from the session and returns only that student's aggregate row, so a caller cannot request another student. Teacher and principal sessions get no row. `class_teacher()` follows the same pattern and returns only the class teacher's name. `EXECUTE` is granted only to `school_app`. Install or refresh both with `python database/enable_rls.py` (superuser, safe to re-run).

## Assistant

`/query` sends the question, a short schema summary, and tool rows to the Anthropic API. On real student data that transfer needs a KVKK / GDPR review. `history` is untrusted input: the server keeps the last 6 items, cuts each to 600 characters, and accepts only `user` and `assistant`. Authority stays with the JWT and row-level security. One question may run at most 3 `run_sql` calls. The model sees at most 50 rows plus the total count; the database still stops at 500 rows and the statement timeout.

For parent and student accounts the tables hold one student, so a plain `AVG` or `COUNT` describes only that child. When such a query runs without `student_rank`, the tool result carries a `scope_warning`, and the prompt tells the model to take class and school figures only from `student_rank`.

`PASS_GRADE` (default 50) is the subject pass grade on the 100-point scale and goes into the schema summary as school policy. `GRADE_LABELS` (default empty) holds an optional 5-point or letter mapping; when it is empty the assistant does not convert grades.

## Technologies (Week 1 only)

- Python 3.10+
- SQLAlchemy 2.x
- SQLite (`school.db`)
- python-dotenv (optional `DATABASE_URL`)
