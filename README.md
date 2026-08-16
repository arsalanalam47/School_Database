# School Management System

A web-based School Management System built with **Python (Flask)** and **SQLite**, designed for a school office to manage students, classes, fees, scholarships, and payments — with separate admin and student/parent logins.

Built end-to-end as a solo project, from database design through a packaged Windows `.exe` ready for non-technical handoff.

---

## Features

- **Two account types**: an admin with full access, and student/parent accounts (auto-created on admission) that can only view their own dues and payment history
- **Student records**: name, father's name, gender, CNIC, phone number, registration number, class
- **Class management** with per-class monthly fees and a promotion order
- **Running dues ledger**: charges (monthly tuition, admission fee, security fee, misc fees) and payments are tracked separately; a student's dues are always `total charges − total payments`, so overpayments automatically carry forward as credit
- **Scholarships**: percentage or fixed amount, grantable and cancellable per student
- **Fee settings**: school-wide admission/security fee amounts, bulk-apply to all students, and custom misc fees (e.g. exam fees) targeted at one class or everyone
- **Year-end promotion**: bumps every active student to their next class in one click; students in the senior-most class are automatically deactivated (graduated), and individual students can be reverted if they're being kept back
- **Payments**: multi-field student lookup (ID, name, father's name, CNIC, phone), full charge/payment ledger per student, and a printable payment slip for every transaction
- **Reports**: this month's/this year's collections, outstanding dues (filterable by class), and full monthly/yearly breakdowns
- **Activate/Deactivate/Delete** students from a dedicated management screen
- Packaged as a **standalone Windows `.exe`** via PyInstaller — no Python installation required on the target machine

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Web framework | Flask |
| Database | SQLite |
| ORM | Flask-SQLAlchemy |
| Auth | Flask-Login, Werkzeug password hashing |
| Frontend | Jinja2 templates, plain HTML/CSS |
| Packaging | PyInstaller |

## Project structure

```
school-management-system/
├── app.py               # routes / application logic
├── models.py             # database models (SQLAlchemy)
├── config.py              # configuration, database path
├── extensions.py            # shared Flask extension instances
├── requirements.txt
├── database/                # SQLite database lives here (gitignored)
├── static/css/style.css       # all styling
├── templates/                  # Jinja2 HTML templates
└── docs/
    ├── user_guide.pdf            # full end-user manual
    ├── project_overview.md        # technical write-up / architecture notes
    └── erd.png                     # entity-relationship diagram
```

## Getting started (development)

```bash
git clone https://github.com/arsalanalam47/school-management-system.git
cd school-management-system
python -m pip install -r requirements.txt
python app.py
```

Open `127.0.0.1:5000` in your browser. On first run you'll be taken through a one-time setup screen to name the school and create the admin account.

## Building a standalone `.exe` (Windows)

```bash
pip install pyinstaller
pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" --name SchoolManagementSystem app.py
```

The finished executable is in `dist/`. It needs an (initially empty) `database/` folder sitting next to it, which is created automatically on first run.

See `docs/user_guide.pdf` for the complete end-user manual, and `docs/project_overview.md` for a deeper technical breakdown of the architecture and database design.

## License

Not yet licensed — add a `LICENSE` file (MIT is a common default for personal/portfolio projects) if you want this to be reusable by others.

## Author

**Arsalan Alam**
- Portfolio: [arsalanalam.netlify.app](https://arsalanalam.netlify.app)
- GitHub: [@arsalanalam47](https://github.com/arsalanalam47)
- LinkedIn: [linkedin.com/in/arsalanalam47](https://linkedin.com/in/arsalanalam47)
