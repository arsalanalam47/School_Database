import os
from datetime import date
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func, or_

from config import Config
from extensions import db, login_manager
from models import School, User, SchoolClass, Student, Scholarship, Charge, Payment

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "database"), exist_ok=True)

db.init_app(app)
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_school_name():
    school = School.query.first()
    return {"school_name": school.name if school else "School Management System"}


def setup_complete():
    return School.query.first() is not None and User.query.filter_by(role="admin").first() is not None


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper


def student_dues(student_id):
    total_charges = db.session.query(func.sum(Charge.amount)).filter_by(student_id=student_id).scalar() or 0
    total_paid = db.session.query(func.sum(Payment.amount)).filter_by(student_id=student_id).scalar() or 0
    return total_charges - total_paid


def add_month(month_str):
    year, month = map(int, month_str.split("-"))
    month += 1
    if month > 12:
        month = 1
        year += 1
    return f"{year:04d}-{month:02d}"


def calculate_monthly_charge(student_id, class_monthly_fee):
    scholarship = Scholarship.query.filter_by(student_id=student_id, active=True).first()
    if not scholarship:
        return class_monthly_fee
    discount = (
        class_monthly_fee * (scholarship.value / 100)
        if scholarship.type == "percentage"
        else scholarship.value
    )
    return max(class_monthly_fee - discount, 0)


# ---------- Auth ----------

@app.route("/about-developer")
def about_developer():
    return render_template("about_developer.html")


@app.route("/setup", methods=["GET", "POST"])
def setup():
    if setup_complete():
        return redirect(url_for("login"))
    if request.method == "POST":
        school_name = request.form.get("school_name", "").strip()
        admin_username = request.form.get("admin_username", "").strip()
        admin_password = request.form.get("admin_password", "")
        if not school_name or not admin_username or not admin_password:
            flash("All fields are required.", "danger")
            return redirect(url_for("setup"))

        db.session.add(School(name=school_name))
        admin = User(username=admin_username, role="admin", must_change_password=False)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

        flash("Setup complete. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("setup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not setup_complete():
        return redirect(url_for("setup"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            if user.must_change_password:
                return redirect(url_for("change_password"))
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        if not current_user.check_password(old_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        current_user.set_password(new_password)
        current_user.must_change_password = False
        db.session.commit()
        flash("Password updated.", "success")
        return redirect(url_for("dashboard"))
    return render_template("change_password.html")


# ---------- Dashboard ----------

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == "user":
        student = current_user.student
        payments = Payment.query.filter_by(student_id=student.id).order_by(
            Payment.payment_date.desc(), Payment.id.desc()
        ).all()
        total_due = student_dues(student.id)
        return render_template(
            "user_dashboard.html", student=student, payments=payments, total_due=total_due
        )

    q = request.args.get("q", "").strip()
    results = []
    if q:
        results = Student.query.filter(
            or_(
                Student.name.ilike(f"%{q}%"),
                Student.reg_number == q,
                Student.cnic == q,
                Student.father_name.ilike(f"%{q}%"),
                Student.phone_number == q,
            )
        ).all()
    return render_template("dashboard.html", query=q, results=results)


# ---------- Classes ----------

@app.route("/classes", methods=["GET", "POST"])
@login_required
@admin_required
def classes():
    if request.method == "POST":
        class_name = request.form.get("class_name", "").strip()
        monthly_fee = request.form.get("monthly_fee", "").strip()
        class_order = request.form.get("class_order", "").strip()
        if not class_name or not monthly_fee or not class_order:
            flash("Class name, fee, and order are required.", "danger")
        elif SchoolClass.query.filter_by(class_name=class_name).first():
            flash("That class already exists.", "danger")
        else:
            try:
                fee_value = float(monthly_fee)
                order_value = int(class_order)
            except ValueError:
                flash("Fee must be a number and order must be a whole number.", "danger")
                return redirect(url_for("classes"))
            db.session.add(SchoolClass(class_name=class_name, monthly_fee=fee_value, class_order=order_value))
            db.session.commit()
            flash("Class added.", "success")
        return redirect(url_for("classes"))

    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()
    return render_template("classes.html", classes=all_classes)


# ---------- Students: add, list, edit ----------

@app.route("/students", methods=["GET", "POST"])
@login_required
@admin_required
def students():
    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()
    school = School.query.first()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        father_name = request.form.get("father_name", "").strip()
        gender = request.form.get("gender", "")
        cnic = request.form.get("cnic", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        reg_number = request.form.get("reg_number", "").strip()
        class_id = request.form.get("class_id")
        scholarship_type = request.form.get("scholarship_type", "")
        scholarship_value = request.form.get("scholarship_value", "").strip()
        charge_admission = request.form.get("charge_admission") == "on"
        charge_security = request.form.get("charge_security") == "on"

        if not name or not reg_number or not class_id or not gender:
            flash("Name, gender, registration number, and class are required.", "danger")
            return redirect(url_for("students"))

        if Student.query.filter_by(reg_number=reg_number).first():
            flash("That registration number is already in use.", "danger")
            return redirect(url_for("students"))

        student = Student(
            name=name, father_name=father_name, gender=gender, cnic=cnic,
            phone_number=phone_number, reg_number=reg_number, class_id=class_id
        )
        db.session.add(student)
        db.session.flush()

        account = User(username=reg_number, role="user", must_change_password=True, student_id=student.id)
        account.set_password("user1234")
        db.session.add(account)

        if scholarship_type and scholarship_value:
            try:
                value = float(scholarship_value)
                db.session.add(Scholarship(student_id=student.id, type=scholarship_type, value=value, active=True))
            except ValueError:
                pass

        if charge_admission:
            db.session.add(Charge(
                student_id=student.id, type="admission", label="Admission fee", amount=school.admission_fee
            ))
        if charge_security:
            db.session.add(Charge(
                student_id=student.id, type="security", label="Security fee", amount=school.security_fee
            ))

        db.session.commit()
        flash(f"Student added. Login username: {reg_number} | default password: user1234", "success")
        return redirect(url_for("students"))

    all_students = Student.query.order_by(Student.name).all()
    return render_template("students.html", students=all_students, classes=all_classes, school=school)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()

    if request.method == "POST":
        student.name = request.form.get("name", "").strip()
        student.father_name = request.form.get("father_name", "").strip()
        student.gender = request.form.get("gender", student.gender)
        student.cnic = request.form.get("cnic", "").strip()
        student.phone_number = request.form.get("phone_number", "").strip()
        student.class_id = request.form.get("class_id")

        new_reg = request.form.get("reg_number", "").strip()
        if new_reg and new_reg != student.reg_number:
            if Student.query.filter_by(reg_number=new_reg).first():
                flash("That registration number is already in use.", "danger")
                return redirect(url_for("edit_student", student_id=student.id))
            student.reg_number = new_reg
            account = User.query.filter_by(student_id=student.id).first()
            if account:
                account.username = new_reg

        db.session.commit()
        flash("Student record updated.", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_student.html", student=student, classes=all_classes)


# ---------- Manage students: activate/deactivate, revert, delete ----------

@app.route("/manage-students")
@login_required
@admin_required
def manage_students():
    all_students = Student.query.order_by(Student.name).all()
    return render_template("manage_students.html", students=all_students)


@app.route("/students/<int:student_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_student_status(student_id):
    student = Student.query.get_or_404(student_id)
    student.status = "inactive" if student.status == "active" else "active"
    db.session.commit()
    flash(f"{student.name} is now {student.status}.", "success")
    return redirect(url_for("manage_students"))


@app.route("/students/<int:student_id>/revert", methods=["POST"])
@login_required
@admin_required
def revert_student(student_id):
    student = Student.query.get_or_404(student_id)
    if student.previous_class_id:
        student.class_id = student.previous_class_id
        student.previous_class_id = None
        db.session.commit()
        flash(f"{student.name} reverted to their previous class.", "success")
    else:
        flash("No previous class on record for this student.", "danger")
    return redirect(url_for("manage_students"))


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    User.query.filter_by(student_id=student.id).delete()
    Scholarship.query.filter_by(student_id=student.id).delete()
    Charge.query.filter_by(student_id=student.id).delete()
    Payment.query.filter_by(student_id=student.id).delete()
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted.", "success")
    return redirect(url_for("manage_students"))


@app.route("/students/promote", methods=["POST"])
@login_required
@admin_required
def promote_students():
    """Moves every active student to the class with the next-higher class_order.
    Students already in the senior-most class are deactivated (graduated).
    Does NOT touch fees."""
    students_list = Student.query.filter_by(status="active").all()
    promoted = 0
    graduated = 0
    for s in students_list:
        current_class = SchoolClass.query.get(s.class_id)
        next_class = SchoolClass.query.filter_by(class_order=current_class.class_order + 1).first()
        if next_class:
            s.previous_class_id = s.class_id
            s.class_id = next_class.id
            promoted += 1
        else:
            s.status = "inactive"
            graduated += 1
    db.session.commit()
    flash(
        f"Promoted {promoted} student(s). {graduated} were in the senior-most class and have been deactivated.",
        "success"
    )
    return redirect(url_for("manage_students"))


# ---------- Fee settings: admission, security, misc ----------

@app.route("/fee-settings", methods=["GET", "POST"])
@login_required
@admin_required
def fee_settings():
    school = School.query.first()
    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_fees":
            try:
                school.admission_fee = float(request.form.get("admission_fee", 0))
                school.security_fee = float(request.form.get("security_fee", 0))
            except ValueError:
                flash("Fees must be numbers.", "danger")
                return redirect(url_for("fee_settings"))
            db.session.commit()
            flash("Fee settings updated.", "success")

        elif action == "apply_admission":
            targets = Student.query.filter_by(status="active").all()
            for s in targets:
                db.session.add(Charge(
                    student_id=s.id, type="admission", label="Admission fee", amount=school.admission_fee
                ))
            db.session.commit()
            flash(f"Admission fee applied to {len(targets)} student(s).", "success")

        elif action == "apply_security":
            targets = Student.query.filter_by(status="active").all()
            for s in targets:
                db.session.add(Charge(
                    student_id=s.id, type="security", label="Security fee", amount=school.security_fee
                ))
            db.session.commit()
            flash(f"Security fee applied to {len(targets)} student(s).", "success")

        elif action == "add_misc":
            label = request.form.get("misc_label", "").strip()
            amount_str = request.form.get("misc_amount", "").strip()
            class_id = request.form.get("misc_class_id", "")
            if not label or not amount_str:
                flash("Misc fee needs a label and amount.", "danger")
                return redirect(url_for("fee_settings"))
            try:
                amount = float(amount_str)
            except ValueError:
                flash("Amount must be a number.", "danger")
                return redirect(url_for("fee_settings"))

            targets_query = Student.query.filter_by(status="active")
            if class_id:
                targets_query = targets_query.filter_by(class_id=int(class_id))
            targets = targets_query.all()
            for s in targets:
                db.session.add(Charge(student_id=s.id, type="misc", label=label, amount=amount))
            db.session.commit()
            flash(f"'{label}' ({amount}) applied to {len(targets)} student(s).", "success")

        return redirect(url_for("fee_settings"))

    return render_template("fee_settings.html", school=school, classes=all_classes)


# ---------- Fees: monthly charge rollover, class-filtered dues, quick pay ----------

@app.route("/fees")
@login_required
@admin_required
def fees():
    class_id = request.args.get("class_id", type=int)
    query = Student.query.filter_by(status="active")
    if class_id:
        query = query.filter_by(class_id=class_id)
    students_list = query.order_by(Student.name).all()

    rows = [{"student": s, "dues": student_dues(s.id)} for s in students_list]

    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()
    return render_template("fees.html", rows=rows, classes=all_classes, selected_class=class_id)


@app.route("/fees/generate-month", methods=["POST"])
@login_required
@admin_required
def generate_month():
    latest = db.session.query(func.max(Charge.month)).filter(Charge.type == "monthly").scalar()
    next_month = add_month(latest) if latest else date.today().strftime("%Y-%m")

    students_list = Student.query.filter_by(status="active").all()
    created = 0
    for s in students_list:
        if Charge.query.filter_by(student_id=s.id, month=next_month, type="monthly").first():
            continue
        amount = calculate_monthly_charge(s.id, s.school_class.monthly_fee)
        db.session.add(Charge(
            student_id=s.id, type="monthly", label=f"{next_month} monthly fee",
            amount=amount, month=next_month
        ))
        created += 1
    db.session.commit()
    flash(f"Generated {next_month} charges for {created} student(s).", "success")
    return redirect(url_for("fees"))


@app.route("/fees/<int:student_id>/pay", methods=["POST"])
@login_required
@admin_required
def pay_fee(student_id):
    try:
        amount = float(request.form.get("amount", "").strip())
    except ValueError:
        flash("Enter a valid amount.", "danger")
        return redirect(url_for("fees"))

    balance_after = student_dues(student_id) - amount
    db.session.add(Payment(
        student_id=student_id, amount=amount, recorded_by=current_user.username, balance_after=balance_after
    ))
    db.session.commit()
    flash("Payment recorded.", "success")

    class_id = request.form.get("class_id")
    return redirect(url_for("fees", class_id=class_id) if class_id else url_for("fees"))


# ---------- Payments: multi-field lookup, detail, slip, history ----------

@app.route("/payments")
@login_required
@admin_required
def payments_search():
    reg_number = request.args.get("reg_number", "").strip()
    name = request.args.get("name", "").strip()
    father_name = request.args.get("father_name", "").strip()
    cnic = request.args.get("cnic", "").strip()
    phone_number = request.args.get("phone_number", "").strip()

    has_query = any([reg_number, name, father_name, cnic, phone_number])
    results = []
    if has_query:
        conditions = []
        if reg_number:
            conditions.append(Student.reg_number == reg_number)
        if name:
            conditions.append(Student.name.ilike(f"%{name}%"))
        if father_name:
            conditions.append(Student.father_name.ilike(f"%{father_name}%"))
        if cnic:
            conditions.append(Student.cnic == cnic)
        if phone_number:
            conditions.append(Student.phone_number == phone_number)
        results = Student.query.filter(or_(*conditions)).all()

    prefill = results[0] if len(results) == 1 else None

    return render_template(
        "payments_search.html", results=results, prefill=prefill,
        reg_number=reg_number, name=name, father_name=father_name,
        cnic=cnic, phone_number=phone_number
    )


@app.route("/payments/<int:student_id>")
@login_required
@admin_required
def payment_detail(student_id):
    student = Student.query.get_or_404(student_id)
    charges = Charge.query.filter_by(student_id=student.id).order_by(Charge.date_added).all()
    payments = Payment.query.filter_by(student_id=student.id).order_by(
        Payment.payment_date.desc(), Payment.id.desc()
    ).all()
    dues = student_dues(student.id)
    return render_template(
        "payment_detail.html", student=student, charges=charges, payments=payments, dues=dues
    )


@app.route("/payments/<int:student_id>/pay", methods=["POST"])
@login_required
@admin_required
def make_payment(student_id):
    try:
        amount = float(request.form.get("amount", "").strip())
    except ValueError:
        flash("Enter a valid amount.", "danger")
        return redirect(url_for("payment_detail", student_id=student_id))

    balance_after = student_dues(student_id) - amount
    payment = Payment(
        student_id=student_id, amount=amount, recorded_by=current_user.username, balance_after=balance_after
    )
    db.session.add(payment)
    db.session.commit()

    return redirect(url_for("payment_slip", payment_id=payment.id))


@app.route("/payments/slip/<int:payment_id>")
@login_required
@admin_required
def payment_slip(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    student = payment.student
    return render_template("payment_slip.html", payment=payment, student=student)


@app.route("/payments/history")
@login_required
@admin_required
def payment_history():
    all_payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    return render_template("payment_history.html", payments=all_payments)


# ---------- Reports ----------

@app.route("/reports")
@login_required
@admin_required
def reports():
    class_id = request.args.get("class_id", type=int)

    students_query = Student.query
    if class_id:
        students_query = students_query.filter_by(class_id=class_id)
    total_dues = sum(student_dues(s.id) for s in students_query.all())

    all_classes = SchoolClass.query.order_by(SchoolClass.class_order).all()

    today = date.today()
    this_month = today.strftime("%Y-%m")
    this_year = today.strftime("%Y")

    this_month_total = db.session.query(func.sum(Payment.amount)).filter(
        func.substr(Payment.payment_date, 1, 7) == this_month
    ).scalar() or 0
    this_year_total = db.session.query(func.sum(Payment.amount)).filter(
        func.substr(Payment.payment_date, 1, 4) == this_year
    ).scalar() or 0

    monthly = (
        db.session.query(
            func.substr(Payment.payment_date, 1, 7).label("period"),
            func.sum(Payment.amount).label("total"),
        ).group_by("period").order_by("period").all()
    )
    yearly = (
        db.session.query(
            func.substr(Payment.payment_date, 1, 4).label("period"),
            func.sum(Payment.amount).label("total"),
        ).group_by("period").order_by("period").all()
    )

    return render_template(
        "reports.html", monthly=monthly, yearly=yearly,
        total_dues=total_dues, classes=all_classes, selected_class=class_id,
        this_month=this_month, this_month_total=this_month_total,
        this_year=this_year, this_year_total=this_year_total,
    )
@app.route("/")
def index():
    if not setup_complete():
        return redirect(url_for("setup"))
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)