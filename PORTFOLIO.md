# Hirely — Portfolio Case Study

## PROJECT NAME
Hirely — Flexible Jobs Platform for Busy Parents

Live demo: https://hirely-a0lx.onrender.com/

## PROBLEM
Most job boards treat flexibility as unstructured text, making it hard for parents and caregivers to find roles that match real-life constraints (school runs, childcare windows, remote requirements). Candidates waste time filtering and often abandon high-friction application flows (cover letters, long forms). Employers hiring for flexible talent also need a simple way to post roles, review applicants, and track decisions without adopting a full ATS.

## SOLUTION
I built a full-stack Django web application that makes flexibility a first-class concept in both the data model and the UI:
- Standardized jobs into clear schedule types (Fixed / Flexible / Async) plus “remote” and “hours/day” signals.
- Implemented a fast discovery flow (search + filters + pagination) optimized for scanning on mobile.
- Streamlined applications into a one-step flow (optional resume upload; no cover letter) with guardrails to prevent duplicate/self applications.
- Delivered an employer dashboard to post/edit/delete roles, toggle listings live/inactive, review applicants, and update application status.
- Added production-oriented configuration (environment-based settings, static asset strategy) plus CI automation for safe iteration.

## IMPACT
- Reduced user friction by designing the candidate journey around “apply quickly” patterns and clear decision signals (“Flex at a glance”).
- Improved employer operations with an opinionated workflow that supports quick review and status tracking.
- Increased engineering confidence via automated tests and CI deploy checks, making the project easier to maintain and extend.

## KEY FEATURES
- Job marketplace: search, schedule-type chips, remote filter, location filter, sorting, and pagination (`jobs/views.py`, `templates/jobs/job_list.html`)
- Job details: decision-focused layout, copy-link action, single primary CTA (`templates/jobs/job_detail.html`)
- Auth: registration, email-based login, safe redirect handling, logout, password reset (`hirely/urls.py`, `jobs/views.py`, `templates/registration/password_reset_form.html`)
- Applications: one-step submit, optional resume upload, protections against self/duplicate applies, email notifications (`jobs/views.py`, `jobs/models.py`, `templates/jobs/apply.html`)
- Candidate tracking: “My Applications” with human statuses (Pending/Seen/Accepted/Rejected) (`templates/jobs/my_applications.html`)
- Employer dashboard: manage roles, live/inactive toggle, applicant review, status updates + pagination (`jobs/views.py`, `templates/jobs/employer_dashboard.html`, `templates/jobs/job_applications.html`)
- Production + CI: WhiteNoise static handling, Postgres via `DATABASE_URL`, Gunicorn, Render deployment, GitHub Actions tests + `check --deploy` (`hirely/settings.py`, `render.yaml`, `.github/workflows/ci.yml`)

## ENGINEERING HIGHLIGHTS (WHAT I’D TALK THROUGH IN AN INTERVIEW)
- Data modeling for clarity: minimal schema (`Job`, `Application`) with constraints like `unique_together` to prevent duplicate applications (`jobs/models.py`).
- Derived signals: computed “flexibility score” from normalized fields to keep UI consistent without extra columns (`jobs/models.py`).
- Query performance: used `select_related`, `annotate`, and `Paginator` to keep list/detail views efficient under load (`jobs/views.py`).
- Security-aware auth: validated redirect targets to avoid open redirect issues (`jobs/views.py`).
- Production hardening: secure cookies and HSTS (when `DEBUG=False`) while supporting reverse-proxy TLS via `SECURE_PROXY_SSL_HEADER` (`hirely/settings.py`).
- Continuous verification: CI runs unit/integration tests plus Django’s deployment checks (`.github/workflows/ci.yml`, `jobs/tests.py`).

## WHAT I’D POLISH NEXT (HIGH ROI)
1. Add a real landing-page metrics loop (basic analytics events + funnel) to measure browse → detail → apply conversion.
2. Complete or remove “future” pages so every visible link is backed by routes/models (alerts/saved roles/profiles templates exist but aren’t fully wired).
3. Align runtime versions across `runtime.txt`, `render.yaml`, and `.github/workflows/ci.yml` for predictable deploys.
4. Add role-based access control (explicit employer vs candidate) and tighten permissions as features expand.
5. Improve observability: structured logs, request IDs, and error reporting (Sentry-style) for production debugging.

## HOW TO REVIEW (FOR RECRUITERS / REVIEWERS)
- Start at `templates/jobs/home.html` and browse roles → open a job → apply.
- Log in as an employer and use the dashboard to post a role and review applicants.
- Review test coverage in `jobs/tests.py` and CI checks in `.github/workflows/ci.yml`.
