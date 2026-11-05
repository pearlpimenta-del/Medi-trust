import os
from datetime import date
from functools import wraps
from html import escape

from flask import (
    Flask, request, redirect, url_for,
    session, flash, abort, render_template_string
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-before-deployment")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///meditrust.db"
).replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

SLOTS = [
    "09:00", "09:30", "10:00", "10:30", "11:00",
    "11:30", "14:00", "14:30", "15:00", "15:30", "16:00"
]

# --------------------------------------------------
# DATABASE MODELS
# --------------------------------------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(10), nullable=False)
    full_name = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    specialization = db.Column(db.String(50))
    qualification = db.Column(db.String(100))
    experience = db.Column(db.Integer, default=0)
    fee = db.Column(db.Integer, default=0)
    about = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=True)

    dob = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    emergency_contact = db.Column(db.String(50))


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    date = db.Column(db.String(10))
    time = db.Column(db.String(5))
    type = db.Column(db.String(20))
    reason = db.Column(db.Text)
    status = db.Column(db.String(15), default="Pending")

    patient = db.relationship("User", foreign_keys=[patient_id])
    doctor = db.relationship("User", foreign_keys=[doctor_id])


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    doctor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    bp = db.Column(db.String(20))
    hr = db.Column(db.String(20))
    cholesterol = db.Column(db.String(20))
    sugar = db.Column(db.String(20))
    ecg = db.Column(db.String(100))
    echo = db.Column(db.String(100))
    diagnosis = db.Column(db.Text)
    notes = db.Column(db.Text)
    report_date = db.Column(
        db.String(10), default=lambda: date.today().isoformat()
    )

    patient = db.relationship("User", foreign_keys=[patient_id])
    doctor = db.relationship("User", foreign_keys=[doctor_id])
    medicines = db.relationship(
        "Medicine", backref="report", cascade="all, delete-orphan"
    )


class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("report.id"))
    name = db.Column(db.String(100))
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50))
    duration = db.Column(db.String(50))


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    message = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)


# --------------------------------------------------
# DESIGN AND HTML
# --------------------------------------------------

STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --navy: #173b3a;
    --green: #2c7168;
    --mint: #eaf3ef;
    --cream: #faf9f5;
    --text: #283b39;
    --muted: #788783;
    --border: #e5ebe7;
    --white: #ffffff;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: var(--cream);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

nav {
    background: white;
    border-bottom: 1px solid var(--border);
    padding: 17px 7%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 15px;
}

.logo {
    font-family: 'Playfair Display', serif;
    font-size: 27px;
    color: var(--navy);
    font-weight: bold;
}

.logo span { color: var(--green); }

.links {
    display: flex;
    flex-wrap: wrap;
    gap: 19px;
    align-items: center;
}

a {
    color: var(--green);
    text-decoration: none;
}

.links a {
    color: #52645f;
    font-size: 14px;
    font-weight: 600;
}

.links a:hover { color: var(--green); }

.container {
    width: 88%;
    max-width: 1150px;
    margin: 38px auto;
}

h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    color: var(--navy);
}

h1 { font-size: 38px; }
h2 { font-size: 27px; }
p { line-height: 1.7; }

.muted { color: var(--muted); }

.hero {
    background: linear-gradient(120deg, #e7f1eb, #f7f5ed);
    border-radius: 22px;
    padding: 65px 7%;
    margin-bottom: 30px;
}

.hero h1 {
    max-width: 650px;
    font-size: 48px;
    line-height: 1.2;
}

.hero p {
    max-width: 570px;
    color: #65746e;
}

.card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 20px;
    box-shadow: 0 5px 22px rgba(24, 58, 52, .035);
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 18px;
}

.stat {
    font-size: 30px;
    font-weight: 700;
    color: var(--green);
    margin-top: 8px;
}

button, .btn {
    display: inline-block;
    background: var(--green);
    color: white;
    border: 0;
    border-radius: 9px;
    padding: 12px 20px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
}

button:hover, .btn:hover {
    background: var(--navy);
    color: white;
}

.btn-light {
    background: var(--mint);
    color: var(--green);
}

.btn-danger { background: #a64d4d; }

form { max-width: 650px; }

input, select, textarea {
    width: 100%;
    padding: 12px 13px;
    border: 1px solid #dce5df;
    border-radius: 8px;
    margin: 7px 0 17px;
    font-family: inherit;
    font-size: 14px;
    background: white;
    color: var(--text);
}

input:focus, select:focus, textarea:focus {
    outline: 2px solid #b6d7ca;
    border-color: var(--green);
}

label {
    font-size: 13px;
    font-weight: 700;
    color: #53645e;
}

table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 12px;
    overflow: hidden;
}

th, td {
    padding: 14px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    font-size: 13px;
}

th {
    background: var(--mint);
    color: var(--navy);
}

.flash {
    padding: 13px 17px;
    background: #e6f3eb;
    color: #24634c;
    border-radius: 9px;
    margin-bottom: 15px;
}

.flash.error {
    background: #faeaea;
    color: #963f3f;
}

.auth {
    max-width: 520px;
    margin: 40px auto;
}

.auth .card { padding: 35px; }

footer {
    text-align: center;
    padding: 35px;
    color: var(--muted);
    font-size: 13px;
}

.badge {
    background: var(--mint);
    color: var(--green);
    border-radius: 20px;
    padding: 5px 11px;
    font-size: 12px;
}

@media(max-width:650px) {
    .container { width: 92%; }
    .hero { padding: 35px 7%; }
    .hero h1 { font-size: 34px; }
    nav { padding: 15px 4%; }
    .links { gap: 11px; }
    table { display: block; overflow-x: auto; }
}
</style>
"""

BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }} | MediTrust Clinic</title>
""" + STYLE + """
</head>
<body>
<nav>
    <a href="/" class="logo">Medi<span>Trust</span>.</a>
    <div class="links">
        <a href="/">Home</a>
        {% if me %}
            <a href="/dashboard">Dashboard</a>
            {% if me.role == 'patient' %}
                <a href="/doctors">Doctors</a>
                <a href="/book">Book appointment</a>
            {% endif %}
            {% if me.role in ['patient','doctor'] %}
                <a href="/appointments">Appointments</a>
            {% endif %}
            <a href="/reports">Reports</a>
            <a href="/notifications">Notifications ({{ unread }})</a>
            <a href="/profile">Profile</a>
            {% if me.role == 'admin' %}
                <a href="/admin/users">Users</a>
                <a href="/admin/appointments">All appointments</a>
            {% endif %}
            <a href="/logout">Logout</a>
        {% else %}
            <a href="/login">Login</a>
            <a href="/register">Register</a>
        {% endif %}
    </div>
</nav>

<main class="container">
{% for category, message in get_flashed_messages(with_categories=true) %}
    <div class="flash {{ 'error' if category == 'error' else '' }}">
        {{ message }}
    </div>
{% endfor %}
{{ content|safe }}
</main>

<footer>© 2026 MediTrust Clinic · Care with trust and compassion</footer>
</body>
</html>
"""


def page(title, content):
    return render_template_string(
        BASE, title=title, content=content, me=current_user(),
        unread=Notification.query.filter_by(
            user_id=current_user().id, is_read=False
        ).count() if current_user() else 0
    )


def e(value):
    return escape(str(value or ""))


def field(label, name, kind="text", required=True, value=""):
    req = "required" if required else ""
    return (
        f'<label>{e(label)}</label>'
        f'<input type="{e(kind)}" name="{e(name)}" '
        f'value="{e(value)}" {req}>'
    )


def notify(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


def current_user():
    if "uid" not in session:
        return None
    return db.session.get(User, session["uid"])


def role_required(*roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if user.role not in roles:
                abort(403)
            return function(*args, **kwargs)
        return wrapper
    return decorator


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------

@app.route("/")
def index():
    doctors = User.query.filter_by(
        role="doctor", approved=True, active=True
    ).limit(4).all()

    content = """
    <section class="hero">
        <span class="badge">WELCOME TO MEDITRUST</span>
        <h1>Your health deserves thoughtful care.</h1>
        <p>
            Connect with trusted healthcare professionals, book appointments
            and keep your medical information organised in one place.
        </p>
        <a class="btn" href="/register">Get started</a>
        <a class="btn btn-light" href="/login">Login</a>
    </section>

    <h2>Healthcare made simpler</h2>
    <div class="grid">
        <div class="card"><h3>01 · Find Doctors</h3>
        <p class="muted">Explore available healthcare professionals.</p></div>
        <div class="card"><h3>02 · Book Appointments</h3>
        <p class="muted">Choose a suitable date and time.</p></div>
        <div class="card"><h3>03 · Medical Reports</h3>
        <p class="muted">Access your reports in one place.</p></div>
    </div>
    <h2>Meet our doctors</h2>
    """

    for doctor in doctors:
        content += f"""
        <div class="card">
            <h3>Dr. {e(doctor.full_name)}</h3>
            <p>{e(doctor.specialization)}</p>
        </div>
        """

    return page("Home", content)


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form

        name = f.get("full_name", "").strip()
        username = f.get("username", "").strip()
        email = f.get("email", "").strip().lower()
        password = f.get("password", "")
        confirm = f.get("confirm", "")
        role = f.get("role", "patient")
        phone = f.get("phone", "").strip() or None

        if role not in ("patient", "doctor"):
            flash("Please select a valid account type.", "error")
        elif not all([name, username, email, password, confirm]):
            flash("Please complete all required fields.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            flash("Username or email already exists.", "error")
        elif role == "doctor" and not f.get("specialization", "").strip():
            flash("Doctor specialization is required.", "error")
        else:
            user = User(
                full_name=name,
                username=username,
                email=email,
                phone=phone,
                role=role,
                password_hash=generate_password_hash(password),
                approved=(role == "patient")
            )

            if role == "doctor":
                user.specialization = f.get("specialization", "").strip()
                user.qualification = f.get("qualification", "").strip()
                user.experience = int(f.get("experience") or 0)
                user.fee = int(f.get("fee") or 0)

            db.session.add(user)
            db.session.commit()

            message = "Account created successfully. Please log in."
            if role == "doctor":
                message = "Doctor account created. Please wait for admin approval."

            flash(message, "success")
            return redirect(url_for("login"))

    content = """
    <div class="auth">
    <div class="card">
        <h2>Create your account</h2>
        <p class="muted">Join MediTrust for simpler healthcare management.</p>
        <form method="POST">
            <label>Account type</label>
            <select name="role" id="role" onchange="doctorFields()" required>
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
            </select>
            """ + field("Full name", "full_name") + """
            """ + field("Username", "username") + """
            """ + field("Email address", "email", "email") + """
            """ + field("Phone number (optional)", "phone", "tel", False) + """
            <div id="doctorFields" style="display:none">
                """ + field("Specialization", "specialization", required=False) + """
                """ + field("Qualification (optional)", "qualification", required=False) + """
                """ + field("Years of experience (optional)", "experience", "number", False) + """
                """ + field("Consultation fee (optional)", "fee", "number", False) + """
            </div>
            """ + field("Password (minimum 8 characters)", "password", "password") + """
            """ + field("Confirm password", "confirm", "password") + """
            <button type="submit">Create account</button>
        </form>
        <p class="muted">Already registered? <a href="/login">Login here</a></p>
    </div></div>

    <script>
    function doctorFields() {
        const isDoctor = document.getElementById('role').value === 'doctor';
        document.getElementById('doctorFields').style.display =
            isDoctor ? 'block' : 'none';
    }
    </script>
    """
    return page("Register", content)


# --------------------------------------------------
# LOGIN AND LOGOUT
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "")

        user = User.query.filter(
            (User.username == username) | (User.email == username.lower())
        ).first()

        if not user or not check_password_hash(user.password_hash, password) or user.role != role:
            flash("Invalid login details or account type.", "error")
        elif not user.active:
            flash("Your account is inactive. Contact the administrator.", "error")
        elif user.role == "doctor" and not user.approved:
            flash("Your doctor account is waiting for admin approval.", "error")
        else:
            session.clear()
            session["uid"] = user.id
            return redirect(url_for("dashboard"))

    content = """
    <div class="auth"><div class="card">
        <h2>Welcome back</h2>
        <p class="muted">Login to your MediTrust account.</p>
        <form method="POST">
            """ + field("Username or email", "username") + """
            """ + field("Password", "password", "password") + """
            <label>Login as</label>
            <select name="role" required>
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
                <option value="admin">Admin</option>
            </select>
            <button type="submit">Login</button>
        </form>
        <p class="muted">New to MediTrust? <a href="/register">Create an account</a></p>
    </div></div>
    """
    return page("Login", content)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@role_required("patient", "doctor", "admin")
def dashboard():
    user = current_user()
    content = f"<h1>Hello, {e(user.full_name)}</h1><p class='muted'>Welcome to your dashboard.</p>"

    if user.role == "patient":
        appointments = Appointment.query.filter_by(patient_id=user.id).all()
        reports = Report.query.filter_by(patient_id=user.id).count()
        doctors = User.query.filter_by(role="doctor", approved=True).count()

        content += f"""
        <div class="grid">
            <div class="card">Appointments<div class="stat">{len(appointments)}</div></div>
            <div class="card">Medical reports<div class="stat">{reports}</div></div>
            <div class="card">Available doctors<div class="stat">{doctors}</div></div>
        </div>
        <br><a class="btn" href="/book">Book an appointment</a>
        """

    elif user.role == "doctor":
        appointments = Appointment.query.filter_by(doctor_id=user.id).all()
        patients = len({a.patient_id for a in appointments})
        pending = sum(a.status == "Pending" for a in appointments)
        reports = Report.query.filter_by(doctor_id=user.id).count()

        content += f"""
        <div class="grid">
            <div class="card">Appointments<div class="stat">{len(appointments)}</div></div>
            <div class="card">Patients<div class="stat">{patients}</div></div>
            <div class="card">Pending requests<div class="stat">{pending}</div></div>
            <div class="card">Reports created<div class="stat">{reports}</div></div>
        </div>
        <br><a class="btn" href="/generate-report">Create medical report</a>
        """

    else:
        content += f"""
        <div class="grid">
            <div class="card">Patients<div class="stat">{User.query.filter_by(role='patient').count()}</div></div>
            <div class="card">Doctors<div class="stat">{User.query.filter_by(role='doctor').count()}</div></div>
            <div class="card">Appointments<div class="stat">{Appointment.query.count()}</div></div>
            <div class="card">Reports<div class="stat">{Report.query.count()}</div></div>
        </div>
        <br><a class="btn" href="/admin/users">Manage users</a>
        """
    return page("Dashboard", content)


# --------------------------------------------------
# DOCTORS
# --------------------------------------------------

@app.route("/doctors")
@role_required("patient")
def doctors():
    search = request.args.get("q", "").strip()
    query = User.query.filter_by(role="doctor", approved=True, active=True)

    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") |
            User.specialization.ilike(f"%{search}%")
        )

    content = """
    <h1>Find a doctor</h1>
    <form method="GET">
        <input name="q" placeholder="Search by name or specialization"
               value=" """ + e(search) + """ ">
        <button>Search</button>
    </form>
    """

    for doctor in query.all():
        content += f"""
        <div class="card">
            <h3>Dr. {e(doctor.full_name)}</h3>
            <p>{e(doctor.specialization)}</p>
            <p class="muted">{e(doctor.qualification)}</p>
            <p>Experience: {doctor.experience or 0} years</p>
            <p>Consultation fee: ₹{doctor.fee or 0}</p>
            <a class="btn" href="/book?doctor_id={doctor.id}">Book appointment</a>
        </div>
        """
    return page("Doctors", content)


# --------------------------------------------------
# BOOK APPOINTMENT
# --------------------------------------------------

@app.route("/book", methods=["GET", "POST"])
@role_required("patient")
def book():
    doctors = User.query.filter_by(
        role="doctor", approved=True, active=True
    ).all()

    if request.method == "POST":
        f = request.form
        try:
            doctor_id = int(f.get("doctor_id"))
        except (TypeError, ValueError):
            flash("Please select a doctor.", "error")
            return redirect(url_for("book"))

        selected_date = f.get("date", "")
        selected_time = f.get("time", "")
        doctor = db.session.get(User, doctor_id)

        if not doctor or doctor.role != "doctor" or not doctor.approved:
            flash("Please select a valid doctor.", "error")
        elif selected_date < date.today().isoformat():
            flash("Please choose a future date.", "error")
        elif selected_time not in SLOTS:
            flash("Please select a valid time slot.", "error")
        elif Appointment.query.filter_by(
            doctor_id=doctor_id, date=selected_date, time=selected_time
        ).filter(Appointment.status != "Cancelled").first():
            flash("That time slot is already booked.", "error")
        else:
            appointment = Appointment(
                patient_id=current_user().id,
                doctor_id=doctor_id,
                date=selected_date,
                time=selected_time,
                type=f.get("type", "In-person"),
                reason=f.get("reason", "").strip(),
                status="Pending"
            )
            db.session.add(appointment)
            db.session.flush()

            notify(doctor_id, f"New appointment request from {current_user().full_name}.")
            notify(current_user().id, f"Your appointment request was submitted. ID: APT{1000 + appointment.id}")
            db.session.commit()

            flash("Appointment request submitted successfully.", "success")
            return redirect(url_for("appointments"))

    options = "".join(
        f'<option value="{d.id}">Dr. {e(d.full_name)} - {e(d.specialization)}</option>'
        for d in doctors
    )

    content = f"""
    <div class="card">
        <h2>Book an appointment</h2>
        <form method="POST">
            <label>Select doctor</label>
            <select name="doctor_id" required>
                <option value="">Choose a doctor</option>{options}
            </select>
            {field("Appointment date", "date", "date")}
            <label>Available time</label>
            <select name="time" required>
                <option value="">Select time</option>
                {''.join(f'<option value="{s}">{s}</option>' for s in SLOTS)}
            </select>
            <label>Appointment type</label>
            <select name="type">
                <option>In-person</option><option>Online</option>
            </select>
            <label>Reason for appointment (optional)</label>
            <textarea name="reason" rows="3"></textarea>
            <button type="submit">Submit request</button>
        </form>
    </div>
    """
    return page("Book Appointment", content)


# --------------------------------------------------
# APPOINTMENTS
# --------------------------------------------------

@app.route("/appointments")
@role_required("patient", "doctor")
def appointments():
    user = current_user()
    if user.role == "patient":
        items = Appointment.query.filter_by(patient_id=user.id).all()
    else:
        items = Appointment.query.filter_by(doctor_id=user.id).all()

    content = """
    <h1>Appointments</h1>
    <div class="card"><table>
    <tr><th>ID</th><th>Patient</th><th>Doctor</th><th>Date</th>
    <th>Time</th><th>Status</th><th>Action</th></tr>
    """

    for a in items:
        actions = ""
        if user.role == "doctor" and a.status == "Pending":
            actions = f"""
            <form method="POST" action="/appointment/{a.id}/accept">
                <button>Accept</button>
            </form>
            <form method="POST" action="/appointment/{a.id}/reject">
                <button class="btn-danger">Reject</button>
            </form>
            """
        elif user.role == "doctor" and a.status == "Confirmed":
            actions = f"""
            <form method="POST" action="/appointment/{a.id}/complete">
                <button>Complete</button>
            </form>
            """
        elif user.role == "patient" and a.status in ("Pending", "Confirmed"):
            actions = f"""
            <form method="POST" action="/appointment/{a.id}/cancel">
                <button class="btn-danger">Cancel</button>
            </form>
            """

        content += f"""
        <tr>
            <td>APT{1000+a.id}</td>
            <td>{e(a.patient.full_name)}</td>
            <td>Dr. {e(a.doctor.full_name)}</td>
            <td>{e(a.date)}</td><td>{e(a.time)}</td>
            <td><span class="badge">{e(a.status)}</span></td>
            <td>{actions}</td>
        </tr>
        """

    content += "</table></div>"
    return page("Appointments", content)


@app.route("/appointment/<int:id>/<action>", methods=["POST"])
@role_required("patient", "doctor", "admin")
def appointment_action(id, action):
    user = current_user()
    appointment = db.get_or_404(Appointment, id)

    allowed = {
        "cancel": "Cancelled",
        "accept": "Confirmed",
        "reject": "Cancelled",
        "complete": "Completed"
    }

    owner = (
        (user.role == "patient" and appointment.patient_id == user.id)
        or (user.role == "doctor" and appointment.doctor_id == user.id)
        or user.role == "admin"
    )

    if not owner or action not in allowed:
        abort(403)

    if user.role == "patient" and action != "cancel":
        abort(403)

    appointment.status = allowed[action]
    notify(
        appointment.patient_id,
        f"Your appointment on {appointment.date} is now {appointment.status}."
    )
    db.session.commit()
    flash("Appointment updated.", "success")
    return redirect(request.referrer or url_for("appointments"))


# --------------------------------------------------
# NOTIFICATIONS
# --------------------------------------------------

@app.route("/notifications")
@role_required("patient", "doctor", "admin")
def notifications():
    user = current_user()
    items = Notification.query.filter_by(
        user_id=user.id
    ).order_by(Notification.id.desc()).all()

    content = "<h1>Notifications</h1>"
    if not items:
        content += '<div class="card">You have no notifications.</div>'

    for item in items:
        content += f'<div class="card">{e(item.message)}</div>'
        item.is_read = True

    db.session.commit()
    return page("Notifications", content)


# --------------------------------------------------
# PROFILE
# --------------------------------------------------

@app.route("/profile", methods=["GET", "POST"])
@role_required("patient", "doctor", "admin")
def profile():
    user = current_user()

    if request.method == "POST":
        user.full_name = request.form.get("full_name", "").strip()
        user.phone = request.form.get("phone", "").strip()
        user.dob = request.form.get("dob", "")
        user.gender = request.form.get("gender", "")
        user.blood_group = request.form.get("blood_group", "")
        user.emergency_contact = request.form.get("emergency_contact", "")
        if user.role == "doctor":
            user.specialization = request.form.get("specialization", "")
            user.qualification = request.form.get("qualification", "")
            user.about = request.form.get("about", "")
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))

    content = f"""
    <div class="card">
        <h2>My profile</h2>
        <form method="POST">
            {field("Full name", "full_name", value=user.full_name)}
            {field("Phone", "phone", required=False, value=user.phone)}
            {field("Date of birth", "dob", "date", False, user.dob)}
            <label>Gender</label>
            <select name="gender">
                <option value="">Prefer not to say</option>
                <option>Male</option><option>Female</option><option>Other</option>
            </select>
            {field("Blood group", "blood_group", required=False, value=user.blood_group)}
            {field("Emergency contact", "emergency_contact", required=False, value=user.emergency_contact)}
    """

    if user.role == "doctor":
        content += field("Specialization", "specialization", value=user.specialization)
        content += field("Qualification", "qualification", required=False, value=user.qualification)
        content += '<label>About</label><textarea name="about">' + e(user.about) + '</textarea>'

    content += '<button>Save changes</button></form></div>'
    return page("Profile", content)


# --------------------------------------------------
# MEDICAL REPORTS
# --------------------------------------------------

@app.route("/reports")
@role_required("patient", "doctor", "admin")
def reports():
    user = current_user()
    query = Report.query

    if user.role == "patient":
        query = query.filter_by(patient_id=user.id)
    elif user.role == "doctor":
        query = query.filter_by(doctor_id=user.id)

    items = query.order_by(Report.id.desc()).all()
    content = """
    <h1>Medical reports</h1>
    <div class="card"><table>
    <tr><th>Report</th><th>Patient</th><th>Doctor</th>
    <th>Date</th><th>Diagnosis</th><th>View</th></tr>
    """

    for report in items:
        content += f"""
        <tr>
            <td>#{report.id}</td>
            <td>{e(report.patient.full_name)}</td>
            <td>Dr. {e(report.doctor.full_name)}</td>
            <td>{e(report.report_date)}</td>
            <td>{e(report.diagnosis)}</td>
            <td><a href="/report/{report.id}">View report</a></td>
        </tr>
        """

    content += "</table></div>"
    if user.role == "doctor":
        content += '<a class="btn" href="/generate-report">Create report</a>'
    return page("Reports", content)


@app.route("/report/<int:id>")
@role_required("patient", "doctor", "admin")
def report_view(id):
    user = current_user()
    report = db.get_or_404(Report, id)

    if (
        user.role == "patient" and report.patient_id != user.id
    ) or (
        user.role == "doctor" and report.doctor_id != user.id
    ):
        abort(403)

    content = f"""
    <div class="card">
        <h1>Medical report #{report.id}</h1>
        <p><b>Patient:</b> {e(report.patient.full_name)}</p>
        <p><b>Doctor:</b> Dr. {e(report.doctor.full_name)}</p>
        <p><b>Date:</b> {e(report.report_date)}</p>
        <hr>
        <p><b>Blood pressure:</b> {e(report.bp)}</p>
        <p><b>Heart rate:</b> {e(report.hr)}</p>
        <p><b>Cholesterol:</b> {e(report.cholesterol)}</p>
        <p><b>Blood sugar:</b> {e(report.sugar)}</p>
        <p><b>ECG:</b> {e(report.ecg)}</p>
        <p><b>Echo:</b> {e(report.echo)}</p>
        <h3>Diagnosis</h3><p>{e(report.diagnosis)}</p>
        <h3>Doctor's notes</h3><p>{e(report.notes)}</p>
        <h3>Medicines</h3>
    """

    for medicine in report.medicines:
        content += f"""
        <p>{e(medicine.name)} · {e(medicine.dosage)}
        · {e(medicine.frequency)} · {e(medicine.duration)}</p>
        """

    content += "</div>"
    return page("Medical Report", content)


@app.route("/generate-report", methods=["GET", "POST"])
@role_required("doctor")
def generate_report():
    doctor = current_user()

    patient_ids = {
        a.patient_id for a in Appointment.query.filter_by(
            doctor_id=doctor.id
        ).all()
    }
    patients = User.query.filter(User.id.in_(patient_ids)).all() if patient_ids else []

    if request.method == "POST":
        f = request.form
        try:
            patient_id = int(f.get("patient_id"))
        except (ValueError, TypeError):
            abort(400)

        if patient_id not in patient_ids:
            abort(403)

        report = Report(
            patient_id=patient_id,
            doctor_id=doctor.id,
            bp=f.get("bp", ""),
            hr=f.get("hr", ""),
            cholesterol=f.get("cholesterol", ""),
            sugar=f.get("sugar", ""),
            ecg=f.get("ecg", ""),
            echo=f.get("echo", ""),
            diagnosis=f.get("diagnosis", ""),
            notes=f.get("notes", "")
        )

        db.session.add(report)
        db.session.flush()

        names = request.form.getlist("med_name")
        doses = request.form.getlist("med_dose")
        frequencies = request.form.getlist("med_freq")
        durations = request.form.getlist("med_dur")

        for name, dose, frequency, duration in zip(
            names, doses, frequencies, durations
        ):
            if name.strip():
                report.medicines.append(Medicine(
                    name=name, dosage=dose,
                    frequency=frequency, duration=duration
                ))

        notify(patient_id, f"A new medical report has been added by Dr. {doctor.full_name}.")
        db.session.commit()
        flash("Medical report created.", "success")
        return redirect(url_for("reports"))

    options = "".join(
        f'<option value="{p.id}">{e(p.full_name)}</option>' for p in patients
    )

    content = f"""
    <div class="card">
        <h2>Create medical report</h2>
        <form method="POST">
            <label>Select patient</label>
            <select name="patient_id" required>
                <option value="">Choose patient</option>{options}
            </select>
            {field("Blood pressure", "bp", required=False)}
            {field("Heart rate", "hr", required=False)}
            {field("Cholesterol", "cholesterol", required=False)}
            {field("Blood sugar", "sugar", required=False)}
            {field("ECG", "ecg", required=False)}
            {field("Echo", "echo", required=False)}
            <label>Diagnosis</label><textarea name="diagnosis"></textarea>
            <label>Notes</label><textarea name="notes"></textarea>
            <h3>Medicine</h3>
            {field("Medicine name", "med_name", required=False)}
            {field("Dosage", "med_dose", required=False)}
            {field("Frequency", "med_freq", required=False)}
            {field("Duration", "med_dur", required=False)}
            <button>Create report</button>
        </form>
    </div>
    """
    return page("Create Report", content)


# --------------------------------------------------
# ADMIN
# --------------------------------------------------

@app.route("/admin/users")
@role_required("admin")
def admin_users():
    users = User.query.order_by(User.role).all()
    content = """
    <h1>Manage users</h1>
    <div class="card"><table>
    <tr><th>Name</th><th>Username</th><th>Role</th>
    <th>Approval</th><th>Account</th><th>Actions</th></tr>
    """

    for user in users:
        if user.role == "admin":
            actions = "Administrator"
        else:
            actions = ""
            if user.role == "doctor" and not user.approved:
                actions += f"""
                <form method="POST" action="/admin/user/{user.id}/approve">
                    <button>Approve</button>
                </form>
                """
            actions += f"""
            <form method="POST" action="/admin/user/{user.id}/toggle">
                <button class="btn-light">{'Deactivate' if user.active else 'Activate'}</button>
            </form>
            """

        content += f"""
        <tr>
            <td>{e(user.full_name)}</td>
            <td>{e(user.username)}</td>
            <td>{e(user.role)}</td>
            <td>{'Approved' if user.approved else 'Pending'}</td>
            <td>{'Active' if user.active else 'Inactive'}</td>
            <td>{actions}</td>
        </tr>
        """

    content += "</table></div>"
    return page("Manage Users", content)


@app.route("/admin/user/<int:id>/<action>", methods=["POST"])
@role_required("admin")
def admin_user_action(id, action):
    user = db.get_or_404(User, id)

    if user.role == "admin":
        abort(403)

    if action == "approve":
        user.approved = True
    elif action == "toggle":
        user.active = not user.active
    else:
        abort(400)

    db.session.commit()
    flash("User updated successfully.", "success")
    return redirect(url_for("admin_users"))


@app.route("/admin/appointments")
@role_required("admin")
def admin_appointments():
    items = Appointment.query.order_by(Appointment.date.desc()).all()
    content = """
    <h1>All appointments</h1>
    <div class="card"><table>
    <tr><th>Patient</th><th>Doctor</th><th>Date</th>
    <th>Time</th><th>Status</th></tr>
    """

    for a in items:
        content += f"""
        <tr>
            <td>{e(a.patient.full_name)}</td>
            <td>Dr. {e(a.doctor.full_name)}</td>
            <td>{e(a.date)}</td><td>{e(a.time)}</td>
            <td>{e(a.status)}</td>
        </tr>
        """

    content += "</table></div>"
    return page("All Appointments", content)


# --------------------------------------------------
# ERROR PAGES
# --------------------------------------------------

@app.errorhandler(403)
def forbidden(error):
    return page("Access denied", "<div class='card'><h1>Access denied</h1><p>You do not have permission to view this page.</p></div>"), 403


@app.errorhandler(404)
def not_found(error):
    return page("Not found", "<div class='card'><h1>Page not found</h1><p>The page you requested does not exist.</p><a class='btn' href='/'>Go home</a></div>"), 404


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

with app.app_context():
    db.create_all()

    # Create demo accounts only when the database is empty.
    if User.query.count() == 0:
        admin = User(
            username="admin",
            email="admin@meditrust.com",
            full_name="MediTrust Admin",
            role="admin",
            password_hash=generate_password_hash("admin123")
        )

        patient = User(
            username="patient1",
            email="patient@meditrust.com",
            full_name="Demo Patient",
            role="patient",
            password_hash=generate_password_hash("patient123")
        )

        db.session.add_all([admin, patient])

        demo_doctors = [
            ("doctor1", "Dr. Smith", "Cardiologist"),
            ("doctor2", "Dr. Jane", "Dermatologist"),
            ("doctor3", "Dr. John", "Neurologist"),
            ("doctor4", "Dr. Akriti", "Dentist"),
            ("doctor5", "Dr. Manish", "Physician")
        ]

        for username, name, specialization in demo_doctors:
            db.session.add(User(
                username=username,
                email=username + "@meditrust.com",
                full_name=name,
                role="doctor",
                specialization=specialization,
                password_hash=generate_password_hash("doctor123"),
                approved=True,
                active=True
            ))

        db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
