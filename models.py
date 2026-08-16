from datetime import date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class School(db.Model):
    __tablename__ = "school"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    admission_fee = db.Column(db.Float, default=0)
    security_fee = db.Column(db.Float, default=0)


class SchoolClass(db.Model):
    __tablename__ = "classes"
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), unique=True, nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False)
    class_order = db.Column(db.Integer, nullable=False, default=0)


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    father_name = db.Column(db.String(150))
    cnic = db.Column(db.String(20))
    phone_number = db.Column(db.String(20))
    gender = db.Column(db.String(10), nullable=False)
    reg_number = db.Column(db.String(30), unique=True, nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    previous_class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=True)
    admission_date = db.Column(db.String(20), default=lambda: date.today().isoformat())
    status = db.Column(db.String(20), default="active")

    school_class = db.relationship("SchoolClass", backref="students", foreign_keys=[class_id])


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'user'
    must_change_password = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=True)

    student = db.relationship("Student", backref="user_account", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Scholarship(db.Model):
    __tablename__ = "scholarships"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'percentage' or 'fixed'
    value = db.Column(db.Float, nullable=False)
    granted_date = db.Column(db.String(20), default=lambda: date.today().isoformat())
    active = db.Column(db.Boolean, default=True)

    student = db.relationship("Student", backref="scholarships")


class Charge(db.Model):
    """A single amount added to a student's running dues balance
    (monthly fee, admission fee, security fee, or a misc fee like exams)."""
    __tablename__ = "charges"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'monthly', 'admission', 'security', 'misc'
    label = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.String(7), nullable=True)  # only set for type='monthly'
    date_added = db.Column(db.String(20), default=lambda: date.today().isoformat())

    student = db.relationship("Student", backref="charges")

    __table_args__ = (db.UniqueConstraint("student_id", "month", "type", name="uq_monthly_charge"),)


class Payment(db.Model):
    """A payment against a student's overall running dues balance (not tied to one month)."""
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    balance_after = db.Column(db.Float)
    payment_date = db.Column(db.String(20), default=lambda: date.today().isoformat())
    recorded_by = db.Column(db.String(50))

    student = db.relationship("Student", backref="payments")
