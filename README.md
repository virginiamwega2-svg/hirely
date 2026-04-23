# Hirely
Flexible jobs platform built with Django. Hirely makes “flexibility” a first‑class concept (Fixed / Flexible / Async schedules + Remote + Hours/day), so candidates can filter quickly and apply with minimal friction, while employers can post roles and manage applicants from a lightweight dashboard.

![CI/CD](https://github.com/virginiamwega2-svg/hirely/actions/workflows/ci.yml/badge.svg)

## Live Demo
- https://hirely-a0lx.onrender.com/

## Features
- Job marketplace with search, filters, sorting, and pagination
- Job detail UX with “Flex at a glance” and a single primary CTA
- Authentication: register, email-based login, logout, password reset
- One-step applications (optional resume upload; no cover letter)
- Candidate tracking: application status timeline (Pending / Seen / Accepted / Rejected)
- Employer dashboard: post/edit/delete roles, live/inactive toggle, review applicants and update status
- CI via GitHub Actions (tests + `check --deploy`)

## Tech Stack
- Backend: Django (`hirely/`, `jobs/`)
- Templates/UI: Django templates + Bootstrap 5 + Bootstrap Icons (`templates/`, `static/`)
- Forms: `django-crispy-forms` + `crispy-bootstrap5`
- DB: SQLite for local dev by default; Postgres supported via `DATABASE_URL`
- Static: WhiteNoise (compressed + hashed assets)
- Prod server: Gunicorn
- Deployment: Render blueprint (`render.yaml`) and `Procfile`

## Project Structure
- `hirely/`: Django project (settings/urls/wsgi)
- `jobs/`: Primary app (models, views, forms, urls, tests, migrations)
- `templates/`: Global + app templates
- `static/`: Static assets (includes hero video)
- `media/`: Uploaded resumes (created at runtime)

## Local Setup (Windows / PowerShell)
1. Create and activate a venv
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies
```powershell
pip install -r requirements.txt
```

3. Configure environment variables  
Copy `.env.example` to `.env` and set a real `SECRET_KEY`.

`.env.example`:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

4. Migrate + run
```powershell
python manage.py migrate
python manage.py runserver
```

Then visit:
- Home: `http://127.0.0.1:8000/`
- Jobs: `http://127.0.0.1:8000/jobs/`
- Admin: `http://127.0.0.1:8000/admin/`

## Environment Variables
Required:
- `SECRET_KEY`: Django secret key

Common:
- `DEBUG`: `True`/`False`
- `ALLOWED_HOSTS`: comma-separated list (e.g. `127.0.0.1,localhost`)
- `DATABASE_URL`: optional; if set, uses Postgres/etc via `dj-database-url` (otherwise SQLite)

Email (optional; defaults to console backend):
- `EMAIL_BACKEND` (default: console)
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`
- `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `DEFAULT_FROM_EMAIL`

## Running Tests
```powershell
python manage.py test --verbosity=2
```

## Screenshots (Portfolio)
- Home (hero + schedule categories)
- Job list (filters + pagination)
- Job detail (“Flex at a glance”)
- Apply flow (optional resume upload)
- My Applications (status UX)
- Employer dashboard (live toggle + applicant counts)
- Applicant review (status dropdown)

## Deployment Notes (Render)
This repo includes a Render blueprint in `render.yaml`. The start command runs:
- `python manage.py migrate`
- `python manage.py collectstatic --noinput`
- `gunicorn hirely.wsgi`

Static files are served via WhiteNoise (`hirely/settings.py`).

## CI
GitHub Actions workflow: `.github/workflows/ci.yml`
- Runs tests on push/PR
- Runs `python manage.py check --deploy` with production-style settings

## Known Polish Items
- Align Python versions: `runtime.txt` currently differs from CI/Render config (`render.yaml`, `.github/workflows/ci.yml`).
- Some templates exist for future features (alerts/saved roles/profiles) but are not currently wired to routes/views; keep nav links aligned with shipped routes to avoid dead ends.
