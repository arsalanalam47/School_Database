# School Management System — Project Overview

## What this project is

A web-based **School Management System** that a school office can use to manage
students, classes, fees, scholarships, and payments — with two kinds of
logins: an **admin** (school staff) who manages everything, and **student/parent
accounts** who can only view their own dues and payment history.

It's not a generic template — it was built feature-by-feature to match a
specific school's workflow: admission with optional one-time fees, monthly
class-based tuition, scholarships that can be granted or cancelled, yearly
class promotion with manual overrides, and full payment tracking with
printable receipts.

---

## Language & environment

| Layer | Technology |
|---|---|
| Programming language | **Python 3.12** |
| Web framework | **Flask** (a lightweight Python web framework) |
| Database | **SQLite** (a single-file database — no separate database server needed) |
| Database toolkit | **Flask-SQLAlchemy** (lets you define database tables as Python classes instead of writing raw SQL) |
| Login/session handling | **Flask-Login** |
| Password security | **Werkzeug** (hashes passwords — plain-text passwords are never stored) |
| Frontend | **HTML templates (Jinja2)** + plain **CSS** — no JavaScript framework, kept intentionally simple |
| Editor | **VS Code** |
| Python installation | Your **MSYS2 Python** (`D:\Program Files\MSYS2\ucrt64\bin\python.exe`) — the same one you use for your C++ work, with `pip` and `tkinter` installed via MSYS2's `pacman` package manager |
| Database browser | **DB Browser for SQLite** (for inspecting the `.db` file directly when needed) |
| How you run it | `python app.py` starts a local web server; you open it in Chrome at `127.0.0.1:5000` |

### Why Flask instead of a desktop app
The project actually started as a Tkinter desktop app, then switched to Flask
partway through — because the requirements grew to include multiple people
logging in at once (admin plus every student's account) and a polished,
card-based visual style. That combination — many simultaneous users, a real
login system, a browser-quality UI — is what Flask (a *web* framework) is
built for; Tkinter (a *desktop* GUI toolkit) is built for one person using
one window on one machine at a time.

### What "running it" actually means technically
`python app.py` starts a small web server on your own PC. It's not hosted on
the internet — `127.0.0.1` means "this computer," so right now only your PC
can open it. When you're ready to hand this off to the school, the same code
can run on the school's office PC the same way, or be deployed to a proper
server later if they want it accessible from multiple computers over their
network.

---

## Project structure

```
school_web/
├── app.py               ← all the routes/logic (the "controller")
├── models.py             ← database table definitions (the "model")
├── config.py              ← app configuration (secret key, database path)
├── extensions.py           ← shared Flask extension instances
├── requirements.txt         ← list of Python packages to install
├── database/
│   └── school.db            ← the actual SQLite database file (auto-created)
├── static/css/style.css      ← all visual styling
└── templates/                ← every HTML page (the "view")
    ├── base.html               ← shared layout (header, nav) every page extends
    ├── setup.html, login.html, change_password.html
    ├── dashboard.html (admin), user_dashboard.html (student/parent)
    ├── students.html, manage_students.html, edit_student.html
    ├── classes.html, fee_settings.html, fees.html
    ├── payments_search.html, payment_detail.html, payment_slip.html, payment_history.html
    └── reports.html
```

This follows a common web-app pattern: **Model** (database structure) →
**Controller** (`app.py`, decides what happens when someone visits a URL or
submits a form) → **View** (the HTML templates that get displayed).

---

## The database — what's actually stored

Seven tables, each a Python class in `models.py`:

1. **School** — one row: the school's name, admission fee, and security fee
   (used school-wide, shown on every page header).
2. **SchoolClass** — each class: name, monthly fee, and an `order` number
   (this order is what "Move to next Year" uses to know which class comes next).
3. **Student** — name, father's name, gender, CNIC, phone, registration
   number (their login username), which class they're in, admission date,
   and active/inactive status.
4. **User** — login accounts. Role is either `admin` or `user`. A `user`
   account is linked to one `Student` row via `student_id`. Passwords are
   never stored in plain text — only a one-way hash.
5. **Scholarship** — which student, what type (percentage or fixed amount),
   the value, and whether it's currently active (admin can cancel anytime).
6. **Charge** — every amount ever billed to a student: monthly tuition,
   admission fee, security fee, or a misc fee like an exam fee. This is the
   "money owed" side of the ledger.
7. **Payment** — every payment a student has made: amount, date, who
   recorded it, and the resulting balance right after that payment. This is
   the "money received" side.

### The core idea: dues are a running balance, not per-month tracking
A student's current dues = **(sum of all their Charges) − (sum of all their
Payments)**. This is calculated fresh every time it's needed — nothing is
manually kept "in sync." It's what makes overpayment and next-month rollover
work correctly:

- Dues are 1200 → student pays 800 → dues become 400
- Dues are 1200 → student pays 2000 → dues become **−800** (a credit)
- Next month's 1000 fee gets charged → −800 + 1000 = **200** (credit absorbed automatically)

---

## Authentication & roles

- **First run** goes to a **setup wizard** — enter the school's name and
  create the first admin account. This only happens once; after that, the
  app redirects straight to login.
- **Admin accounts** are created manually (via setup, or you could add more
  through the database directly).
- **Student/parent accounts** are created *automatically* the moment an admin
  adds a student — username = the student's registration number, default
  password = `user1234`, and they're flagged `must_change_password`, so the
  very first thing they see after logging in is a forced password-change
  screen (which requires entering the old password — that default — to set a
  new one). Admin can also reset any user's password directly without
  needing the old one.
- Every page checks `current_user.role` to decide what to show — admins see
  the full navigation bar (Students, Manage Students, Classes, Fee Settings,
  Fees, Payments, History, Reports); a `user` account only ever sees their
  own dashboard.

---

## Feature walkthrough

**Dashboard**
- Admin: a search box to look up any student by name, reg. number, CNIC,
  father's name, or phone — results link straight to an edit form.
- Student/parent: greeted by their actual name, shown their current dues
  balance, and a full payment history table (newest first).

**Students** — the add-student form (name, father's name, gender, CNIC,
phone, reg. number, class, optional scholarship, checkboxes to
immediately charge admission/security fee) plus a read-only list.

**Manage Students** — a separate page just for status changes: Activate/
Deactivate toggle, Revert (undo a class promotion for one student), and
Delete (also removes their login and financial records).

**Classes** — add classes with a name, monthly fee, and an order number
that drives promotion logic.

**Fee Settings** — set the school-wide admission and security fee amounts,
apply either to every active student at once, and add one-off misc fees
(like an exam fee) targeted at either all students or one specific class.

**Fees** — filter students by class, see everyone's current dues, generate
next month's charges for the whole school with one click ("Move to next
Month"), and record a quick payment inline.

**Payments** — a lookup form with five separate fields (ID, name, father's
name, CNIC, phone) — fill in just one and it finds the student — leading to
their full charge/payment ledger, a payment form that generates a printable
slip (receipt), and a link to view any past slip again.

**Payment History** — every payment across the whole school, most recent
first, each linking back to its slip.

**Reports** — this month's and this year's total collections, outstanding
dues (filterable by class), and full monthly/yearly collection breakdowns.

**Promotion ("Move to next Year")** — bumps every active student to the
class with the next-higher order number, remembering their old class so
individual students can be reverted (kept back) afterward. Students already
in the senior-most class (no higher order exists) are automatically
deactivated instead — treated as graduated.

---

## What's still ahead
You mentioned a **marks/grades module** as a future addition — that would
follow the same pattern as everything above: a new `Marks` table in
`models.py`, new routes in `app.py`, and new templates, without needing to
touch anything that already works.
