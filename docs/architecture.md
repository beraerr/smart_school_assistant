# Architecture — Week 1 baseline

This document mirrors the presentation deck: what exists now versus what later weeks add.

## Target system (end of internship)

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐     ┌────────────┐
│  Streamlit  │────▶│   FastAPI   │────▶│ Rule engine /    │────▶│ PostgreSQL │
│  (Week 6+)  │     │  (Week 2+)  │     │ LLM (Week 3–4+)  │     │ (Week 11+) │
└─────────────┘     └─────────────┘     └──────────────────┘     └────────────┘
                            │
                            ▼
                    JWT auth (Week 2)
                    RBAC rules (Week 3)
```

**Week 1** implements only the bottom-right persistence concept, simplified to **SQLite** and five ORM tables. No HTTP layer, no auth middleware, no business rules yet.

## Data model (this week)

| Table        | Purpose |
|-------------|---------|
| `users`     | Login accounts and `UserRole` (`principal`, `teacher`, `parent`, `student`) |
| `teachers`  | Teacher profiles and assigned `class_name` |
| `students`  | Student profiles; `parent_id` → `users.id` |
| `grades`    | Scores per student/subject/date |
| `attendance`| Daily presence per student |

Key foreign keys:

- `students.parent_id` → `users.id`
- `grades.student_id` → `students.id`
- `attendance.student_id` → `students.id`

## Role / permission matrix (preview)

Full enforcement arrives in Week 3 (rule engine). Planned capabilities:

| Capability              | Principal | Teacher | Parent | Student |
|-------------------------|:---------:|:-------:|:------:|:-------:|
| View all students       | ✓         | class   | child  | self    |
| Edit grades             | ✓         | ✓       | —      | —       |
| View attendance         | ✓         | class   | child  | self    |
| Natural-language query  | ✓         | ✓       | ✓      | ✓       |

“Class” means rows where `students.class_name` matches the teacher’s `related_class` on their user record.
