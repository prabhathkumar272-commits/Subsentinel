# SubSentinel — Subscription & Free Trial Tracker

![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Django 5.x](https://img.shields.io/badge/Django-5.x-green?logo=django)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-38BDF8?logo=tailwindcss)
![HTMX](https://img.shields.io/badge/HTMX-1.x-5D4EE6)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow)

**SubSentinel** helps you track every subscription and free trial you own,
so you never get surprised by an unexpected charge or miss the window to cancel a trial.
Upload a bank statement, let the AI detect recurring charges automatically, then manage
everything from a clean dashboard with renewal reminders delivered right to your inbox.

---

## ✨ Features

- 🔍 **Smart bank-statement import** — CSV upload with AI-powered recurring-charge detection
- 📋 **Subscription management** — Add, edit, pause, or cancel any subscription
- 🆓 **Trial tracker** — See exactly when each free trial expires before you're charged
- 🔔 **Renewal reminders** — Email (and in-app) alerts N days before each billing date
- 📊 **Rich dashboard** — Donut chart by category, 12-month spend trend, top-5 by cost
- 💡 **Smart insights** — Idle subscriptions, duplicate services, potential savings
- 📤 **CSV / PDF export** — Download a spreadsheet-ready CSV or a formatted subscription report
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
| **Email**          | Django `send_mail` / SendGrid (prod)     |
| **Data parsing**   | pandas, python-dateutil                  |
| **Testing**        | pytest-django, pytest-cov, factory_boy   |
| **Containerization**| Docker + docker-compose                 |

---

## 🚀 Quick Start

### Docker (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/yourname/subsentinel.git
cd subsentinel

# 2. Copy env file and adjust as needed
cp .env.example .env

# 3. Build and start all services
docker-compose up --build

# 4. In a second terminal, run migrations and seed demo data
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed_categories
docker-compose exec web python manage.py seed_demo
```

Open **http://localhost:8000** and log in with `demo@subsentinel.com` / `demo1234!`.

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
| `DATABASE_URL`            | Database connection string                    | SQLite (dev)     |
| `REDIS_URL`               | Redis broker URL for Celery                   | `redis://localhost:6379/0` |
| `EMAIL_HOST`              | SMTP host                                     | `localhost`      |
| `EMAIL_HOST_USER`         | SMTP username                                 | *(empty)*        |
| `EMAIL_HOST_PASSWORD`     | SMTP password                                 | *(empty)*        |
| `DEFAULT_FROM_EMAIL`      | Sender address for outgoing email             | `noreply@subsentinel.com` |
| `SENDGRID_API_KEY`        | SendGrid key (optional, prod only)            | *(empty)*        |

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
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
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
