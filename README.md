# SubSentinel — Subscription & Free Trial Tracker

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Django 5.x](https://img.shields.io/badge/Django-5.x-green?logo=django)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-38BDF8?logo=tailwindcss)
![HTMX](https://img.shields.io/badge/HTMX-1.x-5D4EE6)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

**SubSentinel** helps you track every subscription and free trial you own,
so you never get surprised by an unexpected charge or miss the window to cancel a trial.
Upload a bank statement and review recurring-charge candidates detected by a transparent,
rule-based process, then manage everything from a dashboard with renewal reminders.

---

## ✨ Features

- 🔍 **Bank-statement import** — CSV parsing with rule-based recurring-charge detection and review
- 📋 **Subscription management** — Add, edit, pause, or cancel any subscription
- 🆓 **Trial tracker** — See exactly when each free trial expires before you're charged
- 🔔 **Renewal reminders** — Email (and in-app) alerts N days before each billing date
- 📊 **Currency-safe dashboard** — Spend totals stay separate by currency; charts show the selected currency and confirmed history
- 🧾 **Renewal verification** — Due renewals are marked expected until you confirm the charge
- 💡 **Smart insights** — Idle subscriptions, duplicate services, potential savings
- 📤 **CSV export** — Download spreadsheet-ready subscription data
- 🌙 **Dark mode** — System-aware with manual toggle
- 🔒 **Per-user data isolation** — All data scoped to the authenticated user
- 📱 **Mobile-first responsive layout**

---

## 🛠️ Tech Stack

| Layer              | Technology                               |
|--------------------|------------------------------------------|
| **Backend**        | Python 3.11, Django 5.x                  |
| **Frontend**       | Tailwind CSS 3, HTMX 1, Alpine.js        |
| **Database**       | PostgreSQL (prod) / SQLite (dev)         |
| **Background Jobs**| Celery + Redis                           |
| **Email**          | Django SMTP backend                       |
| **Data parsing**   | pandas                                   |
| **Testing**        | pytest-django, pytest-cov                |
| **Containerization**| Docker + docker-compose                 |

---

## 🚀 Quick Start

### Docker (local demo)

```bash
# 1. Clone the repo
git clone https://github.com/prabhathkumar272-commits/Subsentinel.git
cd subsentinel

# 2. Copy env file, generate a secret key, and set DB_PASSWORD
cp .env.example .env
# Generate a key with:
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Paste it into SECRET_KEY in .env. Replace the sample DB password as well.

# 3. Build and start all services
docker-compose up --build

# 4. In a second terminal, migrate and seed local demo data
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_categories
docker-compose exec web python manage.py seed_demo
```

Open **http://localhost:8000** and log in with `demo@subsentinel.com` / `demo1234!`.
The demo seed is for local development only. Do not run `seed_demo` on a public deployment.

### Live deployment checklist

The Compose file provides the Django app, PostgreSQL, Redis, Celery worker, and Celery Beat.
Before deploying, set a unique `SECRET_KEY`, a strong `DB_PASSWORD`, your real
`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`, `ADMIN_EMAIL`, and valid SMTP credentials in the hosting
platform's secret/environment settings. Set `ADMIN_EMAIL` to the address that should
receive Django server-error alerts. Point DNS at your hosting platform or TLS-enabled reverse proxy
and route requests to the app port. Set `APP_BIND_ADDRESS=127.0.0.1` when the proxy runs
on the same host; use the platform's required bind address otherwise. PostgreSQL and
Redis are not published publicly. The container honors the platform's `PORT` variable
(defaults to 8000); `APP_PORT` controls only the published host port in Compose.

Use the production Compose overlay to force HTTPS redirects and secure cookies. First
start the database and Redis, then migrate, and then start the full stack:

```bash
docker compose up -d db redis
docker compose run --rm web python manage.py migrate
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Set `SECURE_HSTS_SECONDS` to a positive value only after HTTPS is confirmed end-to-end.

The app exposes `/health/live/` and `/health/ready/`; Compose also checks database and
Redis readiness with `check_runtime`. Production request and application logs go to
container stdout/stderr, and Django sends server-error alerts to `ADMIN_EMAIL` through
SMTP. Configure platform-level uptime/error alerts as well.

After deployment, verify SMTP with:

```bash
docker compose exec web python manage.py sendtestemail --admins
```

The SMTP test requires valid `ADMIN_EMAIL` and mail settings. Inspect service logs while
exercising reminders.

Create an on-demand PostgreSQL archive with `python ops/database_backup.py backup`.
Schedule this command (or use the hosting provider's managed backup service), encrypt and
store archives outside the app host, and set a retention policy. Restore only after reviewing
the target; this replaces objects in the current database. Practice restores in staging:

```bash
python ops/database_backup.py restore --file backups/<archive>.dump --confirm
```

Do not seed demo users or rely on the sample SMTP values in production. Configure and
test real email delivery. Dependabot checks Python, Docker, and GitHub Actions dependencies weekly.

---

### Local Development

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (copy and edit)
cp .env.example .env
# Generate a key with `python -c "import secrets; print(secrets.token_urlsafe(64))"`
# and paste it into SECRET_KEY in .env.

# 4. Run database migrations
python manage.py migrate

# Collect static assets for WhiteNoise / production-style serving
python manage.py collectstatic --noinput

# 5. Seed default categories and demo account
python manage.py seed_categories
python manage.py seed_demo

# 6. Start the development server
python manage.py runserver
```

---

## 🔧 Environment Variables

| Variable                  | Description                                   | Default          |
|---------------------------|-----------------------------------------------|------------------|
| `SECRET_KEY`              | Django secret key                             | *(required)*     |
| `DEBUG`                   | Enable debug mode                             | `True`           |
| `ALLOWED_HOSTS`           | Comma-separated allowed host names            | `localhost`      |
| `DB_ENGINE`               | Django database backend                       | SQLite in base settings |
| `DB_NAME`                 | Database name or SQLite file path             | `db.sqlite3`      |
| `DB_USER`, `DB_PASSWORD`  | Database credentials                          | *(empty)*         |
| `DB_HOST`, `DB_PORT`      | Database host and port                        | *(empty)*         |
| `DB_SSLMODE`              | PostgreSQL TLS mode (`require` for providers that enforce TLS) | `prefer` |
| `CELERY_BROKER_URL`       | Redis broker URL for Celery                   | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND`   | Celery result backend                         | `redis://localhost:6379/0` |
| `EMAIL_HOST`              | SMTP host                                     | `localhost`      |
| `EMAIL_HOST_USER`         | SMTP username                                 | *(empty)*        |
| `EMAIL_HOST_PASSWORD`     | SMTP password                                 | *(empty)*        |
| `DEFAULT_FROM_EMAIL`      | Sender address for outgoing email             | `noreply@subsentinel.com` |
| `ADMIN_EMAIL`             | Recipient for production error alerts         | Required in production |
| `EMAIL_PORT`, `EMAIL_USE_TLS` | SMTP connection settings                  | `587`, `True`    |
| `CSRF_TRUSTED_ORIGINS`    | Comma-separated origins including scheme      | Set for your domain |
| `SECURE_SSL_REDIRECT`     | Redirect HTTP to HTTPS in production          | `True` in prod settings |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | Send cookies over HTTPS only | `True` in prod settings |

---

## ⚙️ Running Celery

**Worker** (processes background tasks):

```bash
celery -A config worker --loglevel=info
```

**Beat** (periodic scheduler — sends reminders, checks trials):

```bash
celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Both can be run together during development with:

```bash
celery -A config worker --beat --loglevel=info
```

---

## 🧪 Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=apps --cov-report=term-missing

# Run a specific test file
pytest tests/test_models.py -v

# Run only service tests
pytest tests/test_services.py -v

# Run with HTML coverage report
pytest --cov=apps --cov-report=html
# Then open htmlcov/index.html
```

---

## 📁 Project Structure

```
subsentinel/
├── apps/
│   ├── accounts/          # CustomUser model, auth views, settings
│   ├── core/              # Dashboard, landing page, template tags
│   │   ├── management/
│   │   │   └── commands/  # seed_demo, seed_categories
│   │   └── templatetags/  # core_tags (format_money, days_color …)
│   ├── subscriptions/     # Subscription, Category, PaymentRecord models + services
│   ├── notifications/     # Notification model + Celery tasks (reminders, trials)
│   ├── insights/          # Insight engine (idle subs, duplicates, savings tips)
│   └── imports/           # CSV import, bank-statement parser, detect_recurring
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── templates/
│   ├── base.html
│   ├── core/              # landing.html, dashboard.html
│   ├── subscriptions/     # list.html, detail.html, form.html
│   └── notifications/
├── static/
│   ├── css/               # Tailwind output
│   └── js/                # HTMX, Alpine, Chart.js, app.js
├── sample_data/
│   └── sample_statement.csv
├── tests/
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_views.py
│   └── test_tasks.py
├── requirements.txt       # Runtime and development dependencies
├── docker-compose.yml
├── Dockerfile
├── manage.py
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository and create a feature branch (`git checkout -b feat/my-feature`)
2. Write tests for any new behaviour
3. Ensure the full test suite passes (`pytest`)
4. Submit a pull request with a clear description of the change

Please follow the existing code style (PEP 8, Django conventions) and keep commits atomic.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
