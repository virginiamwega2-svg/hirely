Hirely — Flexible Jobs Platform

Hirely is a full-stack job platform designed for busy parents, where job flexibility is structured—not hidden in descriptions.

Instead of manually scanning job listings, candidates can filter roles by schedule type (Fixed, Flexible, Async), remote options, and working hours per day—reducing friction and saving time.
Employers get a lightweight dashboard to post roles, manage applicants, and track hiring decisions.

🔗 Live Demo
https://hirely-a0lx.onrender.com/

Why This Project Matters

Most job platforms treat flexibility as unstructured text, forcing users to open multiple listings just to understand if a role fits their schedule.

Hirely solves this by making flexibility a first-class, structured concept, enabling:

Faster job discovery
Better candidate-role matching
Reduced application friction

This reflects real-world product thinking beyond basic CRUD functionality.

Key Highlights
Structured flexibility filtering (Fixed / Flexible / Async + Remote + Hours/day)
One-step application flow (optional resume upload, no cover letter friction)
Candidate dashboard with application status tracking
Employer dashboard for job management and applicant review
CI/CD pipeline with production checks (GitHub Actions)
Fully deployed and production-ready (Render + Gunicorn)
Features
Candidate Experience
Job search with filters, sorting, and pagination
“Flex at a glance” job detail UX
One-click apply flow
Application status timeline (Pending / Seen / Accepted / Rejected)
Employer Experience
Post, edit, delete job listings
Toggle job visibility (live/inactive)
View applicants and update statuses
Lightweight hiring dashboard
Authentication
User registration
Email-based login/logout
Password reset flow
Tech Stack

Backend

Django

Frontend

Django Templates
Bootstrap 5
Bootstrap Icons

Forms

django-crispy-forms
crispy-bootstrap5

Database

SQLite (local development)
PostgreSQL (via DATABASE_URL in production)

DevOps & Deployment

Gunicorn (production server)
WhiteNoise (static file handling)
Render (deployment)
GitHub Actions (CI pipeline)
Architecture & Technical Decisions
Django for rapid development and built-in authentication system
Server-rendered templates for performance and simplicity (no heavy frontend framework)
WhiteNoise for efficient static asset delivery in production
Environment-based config using .env and DATABASE_URL
CI pipeline to enforce testing and deployment checks
Project Structure
hirely/        # Django project (settings, urls, wsgi)
jobs/          # Core app (models, views, forms, tests)
templates/     # HTML templates
static/        # Static files (CSS, JS, assets)
media/         # User uploads (resumes)
Local Setup (Windows / PowerShell)
1. Create & activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
2. Install dependencies
pip install -r requirements.txt
3. Configure environment variables

Copy .env.example to .env and update:

SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
4. Run migrations & start server
python manage.py migrate
python manage.py runserver
Access the app:
Home: http://127.0.0.1:8000/
Jobs: http://127.0.0.1:8000/jobs/
Admin: http://127.0.0.1:8000/admin/
Environment Variables

Required

SECRET_KEY

Common

DEBUG
ALLOWED_HOSTS
DATABASE_URL

Optional (Email)

EMAIL_BACKEND
EMAIL_HOST
EMAIL_PORT
EMAIL_USE_TLS
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL
Running Tests
python manage.py test --verbosity=2
Deployment

This project includes a Render blueprint (render.yaml).

Production setup:

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn hirely.wsgi

Static files are served via WhiteNoise.

CI/CD

GitHub Actions workflow:

.github/workflows/ci.yml
Runs tests on push/PR
Executes python manage.py check --deploy with production settings
Planned Improvements
Align Python runtime versions across environments
Add saved jobs and alerts system
Expand candidate profile features
Improve UI/UX polish and accessibility
Screenshots (Portfolio)
Home page (hero + schedule categories)
Job listings (filters + pagination)
Job detail view (“Flex at a glance”)
Application flow
Candidate dashboard
Employer dashboard
Applicant review system
Author

Full-stack developer focused on building practical tools for busy parents—combining product thinking with scalable backend systems.


