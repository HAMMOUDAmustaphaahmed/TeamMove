# 🚀 TeamMove — Gestion des Déplacements du Personnel

A secure Flask web application for managing personnel, projects, and field deployments for construction companies.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database](#database)
- [Usage](#usage)
- [Security](#security)
- [Default Credentials](#default-credentials)

---

## Overview

TeamMove is a full-stack web application built with Flask that allows HR managers and general directors to track personnel deployments across construction sites. It provides real-time dashboards, CRUD management for personnel and projects, and deployment history with filtering by date.

---

## ✨ Features

- **Dashboard** — KPI cards, top mobile personnel (by days), deployments by company (doughnut chart), geographic distribution by region
- **Personnel Management** — Full CRUD with matricule, salary type (hourly/monthly), company affiliation, and soft delete
- **Project Management** — Manage construction sites with region, governorate, city, and address; deployment statistics per project
- **Deployments** — Multi-personnel assignment to projects with date/time ranges, live date filtering, quick-add from the personnel table
- **User Management** — Admin-only panel to create users, toggle active/inactive status, role management (Admin / User)
- **Authentication** — Secure login with brute-force protection (5 attempts lockout), session management, last login tracking
- **Responsive UI** — Bootstrap 5 dark theme with Chart.js visualizations

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Flask 2.3 |
| ORM | Flask-SQLAlchemy 3.0 |
| Database | MySQL (MariaDB via XAMPP) |
| Auth | Flask-Login 0.6 |
| Security | Flask-Talisman, Flask-WTF (CSRF), Flask-Limiter |
| Frontend | Bootstrap 5, Chart.js, Font Awesome, jQuery |
| Password Hashing | Werkzeug PBKDF2-SHA256 |

---

## 📁 Project Structure

```
TEAMMOVE/
│
├── app.py              # Application factory, extensions init, CSP config
├── config.py           # Configuration class (DB URI, secret key, session settings)
├── routes.py           # All blueprints and route handlers
├── models.py           # SQLAlchemy models (User, Personnel, Projet, Deplacement)
├── requirements.txt    # Python dependencies
│
├── static/
│   ├── css/
│   │   └── style.css   # Global dark theme styles and CSS variables
│   └── js/
│       └── script.js   # Client-side validation and utilities
│
└── templates/
    ├── base.html           # Base layout with navbar
    ├── landing.html        # Public landing page
    ├── login.html          # Login form
    ├── dashboard.html      # Dashboard with charts (DRH + DG views)
    ├── personnels.html     # Personnel CRUD with pagination
    ├── projets.html        # Projects CRUD with deployment stats
    ├── deplacements.html   # Deployments management with date filter
    └── users.html          # User management (admin only)
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.8+
- [XAMPP](https://www.apachefriends.org/) (Apache + MySQL)
- Node.js (optional, for frontend tooling)

### Steps

**1. Clone the repository**
```bash
git clone https://github.com/yourname/teammove.git
cd teammove
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Start XAMPP** — launch Apache and MySQL services.

**5. Create the database**

Open phpMyAdmin at `http://localhost/phpmyadmin` and run:
```sql
CREATE DATABASE teammove_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
Then import `teammove_db.sql` to create all tables and seed initial data.

**6. Run the application**
```bash
python app.py
```

**7. Open your browser**
```
http://localhost:5000
```

---

## 🔧 Configuration

Edit `config.py` to match your environment:

```python
# Database connection (default: XAMPP root with no password)
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/teammove_db'

# Secret key — CHANGE THIS in production!
SECRET_KEY = 'your-strong-secret-key-here'

# Session lifetime
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
```

Environment variables take precedence over hardcoded values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key for sessions and CSRF |
| `DATABASE_URL` | Full database connection string |

---

## 🗄️ Database

### Tables

| Table | Description |
|---|---|
| `users` | Authenticated users with roles and login tracking |
| `personnels` | Employees with matricule, salary, company, active status |
| `projets` | Construction sites with geographic data (region, governorate, city) |
| `deplacements` | Assignment records linking personnel ↔ project with date/time ranges |

### Relationships

```
personnels  1 ──── N  deplacements
projets     1 ──── N  deplacements
users       1 ──── N  deplacements  (created_by)
```

---

## 📖 Usage

### Accessing the App

| Page | URL | Access |
|---|---|---|
| Landing | `/` | Public |
| Login | `/login` | Public |
| Dashboard | `/dashboard` | Authenticated |
| Personnel | `/personnels` | Authenticated |
| Projects | `/projets` | Authenticated |
| Deployments | `/deplacements` | Authenticated |
| Users | `/users` | Admin only |

### Adding a Deployment

1. Go to **Déplacements**
2. Click **Nouveau Déplacement**
3. Search and select one or multiple personnel using the live search picker
4. Select a project, set start/end dates and times
5. Click **Enregistrer** — one deployment record is created per selected person

### Filtering Deployments by Date

Use the date filter on the Deployments page to see which personnel were on site on any given day. The "Projets actifs" column shows only the projects active on that specific date.

---

## 🔒 Security

| Protection | Implementation |
|---|---|
| CSRF | Flask-WTF token on every POST form (`{{ csrf_token() }}`) |
| XSS | Jinja2 auto-escaping + `html.escape()` on all inputs |
| SQL Injection | SQLAlchemy ORM parameterized queries only |
| Brute Force | 5 failed login attempts locks the session temporarily |
| Password Hashing | PBKDF2-SHA256 with 16-character salt via Werkzeug |
| Security Headers | Flask-Talisman: CSP, X-Frame-Options, X-Content-Type-Options |
| Rate Limiting | Flask-Limiter: 200/day, 50/hour per IP |
| Session Security | HttpOnly, SameSite=Lax cookies; 2-hour lifetime |

> ⚠️ **CSP Note:** `unsafe-inline` is used for inline scripts in templates. Do **not** enable `content_security_policy_nonce_in` in Talisman — when a nonce is present, browsers ignore `unsafe-inline`, which breaks all inline JS.

---

## 🔑 Default Credentials

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin123` |

> **Change the default password immediately after first login in any production environment.**

---

## 📦 Dependencies

```
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.2
Flask-Talisman==1.0.0
Flask-Limiter==3.3.0
Flask-WTF==1.1.1
PyMySQL==1.1.0
Werkzeug==2.3.7
bleach==6.0.0
python-dotenv==1.0.0
gunicorn==21.2.0          # Production WSGI server
```

---

## 🚀 Production Deployment

For production, replace the development server with Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Also make sure to:
- Set `SESSION_COOKIE_SECURE = True` in `config.py`
- Use a strong, random `SECRET_KEY` via environment variable
- Enable HTTPS (set `force_https=True` in Talisman)
- Use a dedicated MySQL user with limited privileges

---

## 📄 License

This project is proprietary. All rights reserved.