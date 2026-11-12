# Architecture — Week 1 baseline

This document mirrors the presentation deck: what exists now versus what later weeks add.

## Why PostgreSQL in Week 1

Role-based access will be enforced in the database with PostgreSQL row-level security, not only in a later application rule engine. SQLite cannot express those policies, so the project starts on PostgreSQL. Application code will set `app.role`, `app.class`, and `app.student_id` on each transaction; the policies below already filter `students`, `grades`, and `attendance` from those settings.

Superusers bypass row-level security. `init_db.py` and `seed_mock.py` use that path. Filtered reads connect as `school_app`, the non-superuser role created by `database/enable_rls.py`.

## Target system (end of internship)

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│ Rule engine /    │────▶│ PostgreSQL + RLS    │
│  (Week 6+)  │     │  (Week 2+)  │     │ LLM (Week 3–4+)  │     │ (Week 1)            │
└─────────────┘     └─────────────┘     └──────────────────┘     └─────────────────────┘
                            │
                            ▼
                    JWT auth (Week 2)
                    RBAC rules (Week 3)
```

**Week 1** implements the persistence layer: five ORM tables on PostgreSQL, plus row-level security on `students`, `grades`, and `attendance`. No HTTP layer, no auth middleware, and no business-rule engine yet. The policies are the database half of the role matrix; Week 3 still adds the application rules that choose which session settings to set.

## Data model (this week)

| Table        | Purpose |
|-------------|---------|
| `users`     | Login accounts and `UserRole` (`principal`, `teacher`, `parent`, `student`) |
| `teachers`  | Teacher profiles and assigned `class_name` |
| `students`  | Student profiles; `parent_id` → `users.id`. RLS on. |
| `grades`    | Scores per student/subject/date. RLS on. |
| `attendance`| Daily presence per student. RLS on. |

Key foreign keys:

- `students.parent_id` → `users.id`
- `grades.student_id` → `students.id`
- `attendance.student_id` → `students.id`

## Row-level security

`students` allows a row when:

- `app.role` is `principal` (every row), or
- `app.role` is `teacher` and `class_name` equals `app.class`, or
- `app.role` is `parent` or `student` and `id` equals `app.student_id`.

`grades` and `attendance` allow a row when `student_id` is among the `students` rows visible under that same policy. The subquery is filtered by `students` RLS, so a teacher sees grades and attendance only for their class.

## Role / permission matrix (preview)

Full application enforcement arrives in Week 3 (rule engine). The database policies already match the read side of this matrix:

| Capability              | Principal | Teacher | Parent | Student |
|-------------------------|:---------:|:-------:|:------:|:-------:|
| View all students       | ✓         | class   | child  | self    |
| Edit grades             | ✓         | ✓       | —      | —       |
| View attendance         | ✓         | class   | child  | self    |
| Natural-language query  | ✓         | ✓       | ✓      | ✓       |

“Class” means rows where `students.class_name` matches the teacher’s `related_class` on their user record. The Week 1 policy reads that class from `app.class`, which a later request handler will copy from the logged-in teacher.
