# Week 12 — Going Live and Wrapping Up

## Summary
In the last week of the internship we put the system online: https://smartschoolassistant.com runs with Docker Compose on a Contabo VPS, and only Caddy is exposed. The assistant got a `get_risk` tool that calls the same code as the risk page, and stricter number rules. For the teacher's question "what is my class's rank in our school?" we wrote the `class_rank` function. On the live site we saw the model silently drop a student from a list, and we closed this structurally: for list requests the model does not see rows, and the app draws the full table.

The second half of the week went into wrapping up: the code was cleaned, silent error swallowing was removed, AI tool files were deleted, a README was written in two languages and the project was prepared for GitHub. In the interface we fixed the grades table, the risk reasons in both languages, the weekly reports page, the research page's summary cards and the phone layout.

## 1. Going live

### 1.1 Setup
| Service | Role |
|---|---|
| `db` | postgres:18.6; data in the `smartschool_db_data` volume; not exposed |
| `init` | One-off (`init` profile): `init_db.py` → `bootstrap_roles.py` → `enable_rls.py` → `seed_mock.py` |
| `backend` | uvicorn; health-checked; not exposed |
| `frontend` | Streamlit; `API_BASE_URL=http://backend:8000`; not exposed |
| `caddy` | caddy:2.10.0; 80/443; automatic certificates; gets no `.env` |

- **One image:** `smartschool-app:week12` (`python:3.14.9-slim`), dependencies installed exactly from `requirements.lock.txt`, non-root user. Backend and frontend share it.
- **Same versions as the local test setup:** Python 3.14.9, PostgreSQL 18. Cursor had written `postgres:16`; since the local tests run on PG 18, it became `postgres:18.6` (the lesson from Week 11's environment bug).
- **`.env` only on the server:** it does not enter the image; passwords and `SECRET_KEY` were regenerated for the server; `DEMO_TODAY=2026-11-09`.
- **Domain:** `smartschoolassistant.com` (Cloudflare Registrar and DNS). Certificates were obtained for the root domain and `www`; `www` redirects to the root.
- **Separate Postgres:** the n8n stack on the same server and its database were left untouched.
- **Roles and policies in code:** the `school_app` role and the permissive policies had been set up by hand in the local database. This came up during deploy preparation; `bootstrap_roles.py` was written and an equality test against `database/ref/sema.sql` was added. RLS can now be built from scratch.

### 1.2 Update flow
1. Full local test run.
2. `rsync` (excluding `.env`, `.venv`, raw data and `docs/sunumlar`).
3. Per-file md5 comparison, sorted with `LC_ALL=C`; the output must say `AYNI`.
4. On the server, `docker compose build` and `docker compose up -d backend frontend`.
5. Only if a database function changed: `docker compose exec backend python database/enable_rls.py`.

`init` is never run again; `seed_mock` empties the tables.

## 2. Assistant

### 2.1 `get_risk`
It calls the risk page's `read_risk` with the same session and RLS context; the calculation is not copied. The principal sees the whole school or one class, a class teacher only their own class. Asking for another class returns `forbidden` and logs `get_risk_denied`. Parents and students do not have the tool; a direct call is refused.

### 2.2 Number rules
Numbers are written exactly as in the result: no ranges, rounding or "about". A new number needs a new query. "This term" means from the start of the term to today; if the data covers less, the answer says so first. Turkish uses the decimal comma. In a live test the model answered a principal's question with "between 71 and 74"; the grounding check caught `71`. The fix went into the instructions; the check was not loosened.

### 2.3 List mode
On the live site, for "List the grades of the students in my class" the query returned 60 rows and the model received the first 50. The answer said "your 6 students" but listed 5; Zeynep Demir was missing. The grounding check could not catch it, because every number written was in the result; the problem was what was left out.

The fix is structural, not an instruction: `run_sql` got a `presentation` option. For list requests the model sends `table` and receives, instead of rows, only a summary computed from the whole result: `row_count`, `columns`, `distinct_counts` (no 200-row limit in this mode) and `date_range`. The app draws the full table under the answer. Since the model never sees the rows, it cannot drop or change them, and a class of 32 gets the same short answer as a class of 6.

### 2.4 `class_rank`
A class teacher only sees their own class in the tables, so a "school average" written in plain SQL would really be the class average. `class_rank` is `student_rank`'s counterpart for classes: `SECURITY DEFINER`, fixed `search_path`, it reads the class from the `app.class` session setting rather than a parameter, returns one row only for the `teacher` role (rank, number of classes, class average, school average) and carries the time gate itself. No other class's name or average is returned. The answer says in one sentence that the classes are at different grade levels and that the rank does not measure the teacher's performance.

### 2.5 Example questions
Teachers got "List the grades of the students in my class." and "What is my class's rank in our school?", the principal "List the grades of all students in the school." (with Turkish versions).

## 3. Interface
- **Grades table:** the pivot put names in the table's index, and since the index was hidden the names did not show; each date was its own row, so the table was sparse. Now each student is one row and each exam one column. If everyone's exam dates in a subject are the same, the header shows the date (`Fizik 29.09`); otherwise a sequence number and a short note. No computed numbers. The table sits right under the answer; "Show query" only holds the SQL.
- **Risk reasons:** they came in Turkish on the EN page too, and every row ended with "This is not a decision." `assess_risk` now takes `lang` (an unknown language raises an error), the `/risk` endpoint takes the language as a parameter, and the tie label is `(eşit)` / `(tie)`. The decision sentence was removed; the explanation is already at the top of the page.
- **Weekly reports page** (`?sayfa=haftalik`): no login; every week's presentation as slides and as a PDF. Slides are produced by `scripts/haftalik_slaytlar.py`.
- **Login cards:** "Data science study" and "Weekly reports".
- **Research page:** the summary cards sit in one grid with equal heights; the third card now shows the data scale (student-course records and course-presentations, from the package). The "unknown" card and the reading time label were removed.
- **Phone layout:** select boxes accepted typed text, so they opened the keyboard on phones; they became tap-only controls. On phones the "demo data" chip is hidden; the top bar fits and the sidebar arrow no longer overlaps it.

## 4. Cleanup and GitHub preparation
- `backend/app/main.py`: a startup error in the schema summary was swallowed with `except Exception: pass`; it is now logged as a warning (the summary is rebuilt on the first query).
- `data_science/oulad/explain.py`: SHAP silently tried 3 setups × 3 call styles. A small probe confirmed which path works with shap 0.54.1, and it was reduced to that single path; an unexpected shape raises an error. Two new tests.
- `eval/run_eval.py`: a failed evidence query was silently skipped; it is now written to stderr with the error type and the SQL.
- Unused imports and variables removed; the `database/__init__.py` docstring updated; `docs/architecture.md` (left over from Week 1) deleted.
- `.cursor/`, `*.mdc` and prompt files were removed from all week folders; tool wording in `docs/metin_yamasi.json` was rewritten neutrally.
- `.gitignore` rewritten. Raw and processed data are not in the repository (`studentVle.csv` is 453 MB); the README gives the download steps.
- README in English and Turkish: live demo and links, features, a section for parents, architecture and question-flow diagrams, security model, attention flag, research summary, setup, demo accounts, tests, deployment, limitations, data sources. Screenshots sit in their sections (`docs/img/`, TR and EN).
- The WEEK documents of all weeks are in `docs/haftalar/` (21 files; no Week 6 EN). The test that read `../week10` outside the repository now reads from there.

## 5. Decisions
| Decision | Reason |
|---|---|
| Deploy before the pending security items | User decision; the only condition was that `.env` stays out of the image |
| Public demo, every role included | For showcasing; the data is fully synthetic |
| Fixed `DEMO_TODAY` on the live site | Keep the demo consistent until the mock gate issue (bug 2) is fixed |
| The model sees no rows for list requests | No missing or altered rows can be written; a structural guarantee |
| Class rank for teachers | The principal can already compare classes; the rank covers only the teacher's own class, with a grade-level note |
| Risk reasons in the client's language, language required | No silent fallback to Turkish |
| Only week-12 in the repository | Weekly progress lives in the WEEK documents and the weekly page |
| Specs and pre-registration files stay in the repository | Code and tests depend on them; they back the pre-registration claim |

## 6. Bug records
| Bug | Root cause | Fix |
|---|---|---|
| Tests and app ran in different environments (from Week 11) | The environment was not documented; tests used `week-11/.venv`, the app the shared `.venv` (fastapi 0.162/0.142, pillow 13.0/12.3) | One environment, `requirements.lock.txt`; the same versions in deploy |
| The mock gate does not protect what the app shows | The gate looks at cumulative risk, the app at the term window; on 2027-04-15 Zeynep is unflagged in the app | Temporary: `DEMO_TODAY=2026-11-09`; permanent fix open |
| `_sor` name clash | Cursor added a same-named helper to `test_assistant.py`; 3 identity tests failed with `TypeError` (3 failed / 1289 passed) | New rule: no helper with an existing name |
| Blind asserts in weekly page tests | The counting helper used the proto name `imgs` and always counted 0; a re-run read the real asset folder (`assert 21 == 3`) | `at.get("image")`, root from the `HAFTALIK_DIZIN` environment variable |
| Roles, GRANTs and base policies not in code | Set up by hand in the local database | `bootstrap_roles.py` + `sema.sql` equality test |
| The assistant wrote a range | A rounded range; `71` was ungrounded | Instruction; check not loosened |
| Button overlapped the description on cards | Old `arastirma_ac` style rules also applied inside the card | Rules cleaned up |
| Server files stayed old | The test + rsync `&&` chain stopped silently | Every command ends with a confirmation word; md5 comparison |
| md5 totals differed, files were the same | `sort` used a different locale on each machine | `LC_ALL=C` and a per-file `diff` |
| No names in the grades table | The pivot put names in a hidden index | Name as a column; one column per exam |
| A student missing from a list | The model saw 50 of 60 rows and listed what it saw | List mode |
| Risk reasons in Turkish on the EN page | The reason was built in one language in the backend | `lang` required; `/risk?lang=` |
| 10 tests failed after the risk language change | Two `assess_risk` callers (`test_mock_uret.py`, `scripts/mock_uret.py`) were missed; the grep output had been cut | Both calls fixed; search output read in full |
| Example question test failed | New questions were added to the source but not to the expected list in the test | Expected list updated; comparison still exact |
| A test fails on a clean clone | It read `../week10/WEEK_10.md` | Source moved into `docs/haftalar` |
| Summary cards of different heights | Cards were in separate Streamlit columns | One CSS grid |
| Keyboard opened on phones | Select boxes accept search text | Tap-only controls |

**Known limit:** the UCI notebook figures are identical in the TR and EN versions (same md5); the TR labels are in English.

## 7. Known limits
- Request and login counters live in process memory: not shared between workers and reset on restart.
- The demo is public; anyone can log in with any role, including principal.
- The assistant sends the question, a schema summary and query results to an external API; real data would need a KVKK / GDPR review first.
- The attention flag uses only grades and absences; the research's strongest signal, unsubmitted homework, is not in the school data.
- The frontend service has no health check.

## 8. Outputs and verification
- **Server:** `grades|attendance|pg_policies` = `1440|6444|5`; `init` set up the role, RLS and policies; services are up, backend and db healthy; certificates obtained for the root domain and `www`.
- **Tests:** full run at the start of the week 1,335 passed. The last full run after the list mode, `class_rank` and risk language changes: **1,366 passed** (before the mobile interface fix).
- **Package:** `arastirma.json` unchanged (md5 `27f5279b8b574814c2682d070603798e`).
- **Repository:** forbidden files 0, `sk-ant-` traces 0, no file above 5 MB, 63 MB in total.

```
.venv/bin/python -m pytest -q
docker compose build && docker compose up -d backend frontend
docker compose exec backend python database/enable_rls.py
```

## 9. Open items
- Rotate the API key and set a spending limit in the Anthropic console.
- Login counter, question length limit, log masking; `seed_mock` prints the demo passwords to the log.
- Test the mock generation gate against the term window (bug 2).
- Regenerate `database/ref/sema.sql` with `class_rank`.
- Image size: the lock file also installs the jupyter and shap stack; runtime dependencies should be split out.
- On the server, n8n (5678) and render-service (8000) are exposed over plain HTTP; 70 pending updates.
- Move the plotting code into the package (UCI U1–U6, OULAD O1–O4), Turkish formatter, Turkish UCI figures.
- No Week 6 EN presentation.

## 10. Future work
- **Homework submission record:** the model's strongest signal in the research; if the school data had it, the attention flag could use it.
- **A comparison-free flag for parents:** based on the child's own history, without comparing to the class.
- **Subgroup audit:** checking that the flag works equally well for different groups of students.
- **Teacher effects:** neither dataset has them; the data and design needed to measure them.
