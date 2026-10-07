"""MediTrust Clinic - beginner-friendly Flask app (Patient / Doctor / Admin)."""

from datetime import date
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.config["SECRET_KEY"] = "change-this-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meditrust.db"

db = SQLAlchemy(app)


SLOTS = [
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00"
]


# ============================================================
# MODELS
# ============================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(200),
        nullable=False
    )

    email = db.Column(
        db.String(100),
        unique=True
    )

    phone = db.Column(
        db.String(20)
    )

    role = db.Column(
        db.String(10),
        nullable=False
    )

    full_name = db.Column(
        db.String(100)
    )

    active = db.Column(
        db.Boolean,
        default=True
    )

    # Doctor fields
    specialization = db.Column(
        db.String(50)
    )

    qualification = db.Column(
        db.String(100)
    )

    experience = db.Column(
        db.Integer
    )

    fee = db.Column(
        db.Integer
    )

    about = db.Column(
        db.Text
    )

    approved = db.Column(
        db.Boolean,
        default=True
    )

    # Patient fields
    dob = db.Column(
        db.String(20)
    )

    gender = db.Column(
        db.String(10)
    )

    blood_group = db.Column(
        db.String(5)
    )

    emergency_contact = db.Column(
        db.String(50)
    )


class Appointment(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    date = db.Column(
        db.String(10)
    )

    time = db.Column(
        db.String(5)
    )

    type = db.Column(
        db.String(20)
    )

    reason = db.Column(
        db.Text
    )

    status = db.Column(
        db.String(15),
        default="Pending"
    )

    patient = db.relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = db.relationship(
        "User",
        foreign_keys=[doctor_id]
    )


class Report(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    bp = db.Column(db.String(20))
    hr = db.Column(db.String(20))
    cholesterol = db.Column(db.String(20))
    sugar = db.Column(db.String(20))

    ecg = db.Column(
        db.String(100)
    )

    echo = db.Column(
        db.String(100)
    )

    diagnosis = db.Column(
        db.Text
    )

    notes = db.Column(
        db.Text
    )

    report_date = db.Column(
        db.String(10),
        default=lambda: date.today().isoformat()
    )

    patient = db.relationship(
        "User",
        foreign_keys=[patient_id]
    )

    doctor = db.relationship(
        "User",
        foreign_keys=[doctor_id]
    )

    medicines = db.relationship(
        "Medicine",
        backref="report",
        cascade="all, delete-orphan"
    )


class Medicine(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    report_id = db.Column(
        db.Integer,
        db.ForeignKey("report.id")
    )

    name = db.Column(
        db.String(100)
    )

    dosage = db.Column(
        db.String(50)
    )

    frequency = db.Column(
        db.String(50)
    )

    duration = db.Column(
        db.String(50)
    )


class Notification(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    message = db.Column(
        db.String(200)
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )


# ============================================================
# HELPERS
# ============================================================

def current_user():
    if "uid" in session:
        return db.session.get(User, session["uid"])

    return None


def role_required(*roles):
    """Block pages for users who are not logged in or have the wrong role."""

    def deco(f):

        @wraps(f)
        def wrapper(*args, **kwargs):

            user = current_user()

            if not user:
                return redirect(url_for("login"))

            if user.role not in roles:
                abort(403)

            return f(*args, **kwargs)

        return wrapper

    return deco


def notify(user_id, msg):
    notification = Notification(
        user_id=user_id,
        message=msg
    )

    db.session.add(notification)


@app
