"""MediTrust Clinic - beginner-friendly Flask app (Patient / Doctor / Admin)."""
import random
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meditrust.db'
db = SQLAlchemy(app)

SLOTS = ['09:00', '09:30', '10:00', '10:30', '11:00', '11:30', '14:00', '14:30', '15:00', '15:30', '16:00']

# ---------------- MODELS ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(10), nullable=False)  # patient / doctor / admin
    full_name = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    # doctor fields
    specialization = db.Column(db.String(50))
    qualification = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    fee = db.Column(db.Integer)
    about = db.Column(db.Text)
    approved = db.Column(db.Boolean, default=True)
    # patient fields
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    emergency_contact = db.Column(db.String(50))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.String(10))
    time = db.Column(db.String(5))
    type = db.Column(db.String(20))
    reason = db.Column(db.Text)
    status = db.Column(db.String(15), default='Pending')
    patient = db.relationship('User', foreign_keys=[patient_id])
    doctor = db.relationship('User', foreign_keys=[doctor_id])

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    bp = db.Column(db.String(20)); hr = db.Column(db.String(20))
    cholesterol = db.Column(db.String(20)); sugar = db.Column(db.String(20))
    ecg = db.Column(db.String(100)); echo = db.Column(db.String(100))
    diagnosis = db.Column(db.Text); notes = db.Column(db.Text)
    report_date = db.Column(db.String(10), default=lambda: date.today().isoformat())
    patient = db.relationship('User', foreign_keys=[patient_id])
    doctor = db.relationship('User', foreign_keys=[doctor_id])
    medicines = db.relationship('Medicine', backref='report', cascade='all, delete-orphan')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    name = db.Column(db.String(100)); dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50)); duration = db.Column(db.String(50))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    message = db.Column(db.String(200))
    is_read = db.Column(db.Boolean, default=False)

# ---------------- HELPERS ----------------
def current_user():
    return db.session.get(User, session['uid']) if 'uid' in session else None

def role_required(*roles):
    """Block pages for users who are not logged in or have the wrong role."""
    def deco(f):
        @wraps(f)
        def wrapper(*a, **kw):
            u = current_user()
            if not u:
                return redirect(url_for('login'))
            if u.role not in roles:
                abort(403)
            return f(*a, **kw)
        return wrapper
    return deco

def notify(user_id, msg):
    db.session.add(Notification(user_id=user_id, message=msg))

@app.context_processor
def inject():
    u = current_user()
    unread = Notification.query.filter_by(user_id=u.id, is_read=False).count() if u else 0
    return dict(me=u, unread=unread)

# ---------------- PUBLIC / AUTH ----------------
@app.route('/')
def index():
    docs = User.query.filter_by(role='doctor', approved=True).limit(5).all()
    return render_template('index.html', docs=docs)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        f = request.form
        if f['password'] != f['confirm']:
            flash('Passwords do not match', 'error')
        elif len(f['password']) < 6:
            flash('Password must be at least 6 characters', 'error')
        elif User.query.filter((User.username == f['username']) | (User.email == f['email'])).first():
            flash('Username or email already exists', 'error')
        else:
           u = User(username=f['username'], email=f['email'], phone=f['phone'], role=f['role'],
         full_name=f['full_name'], password_hash=generate_password_hash(f['password']),
         active=True)
            if f['role'] == 'doctor':
                u.specialization = f.get('specialization'); u.qualification = f.get('qualification')
                u.experience = int(f.get('experience') or 0); u.fee = int(f.get('fee') or 0)
                u.approved = False  # admin must approve
            else:
                u.dob = f.get('dob'); u.gender = f.get('gender')
                u.blood_group = f.get('blood_group'); u.emergency_contact = f.get('emergency_contact')
            db.session.add(u); db.session.commit()
            flash('Registered! Please login.' + (' Doctor accounts need admin approval.' if u.role == 'doctor' else ''), 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        f = request.form
        u = User.query.filter((User.username == f['username']) | (User.email == f['username'])).first()
        if not u or not check_password_hash(u.password_hash, f['password']) or u.role != f['role']:
            flash('Invalid username, password or role', 'error')
        elif not u.active or (u.role == 'doctor' and not u.approved):
            flash('Account is inactive or awaiting approval', 'error')
        else:
            session['uid'] = u.id
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@role_required('patient', 'doctor', 'admin')
def dashboard():
    u = current_user()
    if u.role == 'patient':
        appts = Appointment.query.filter_by(patient_id=u.id).all()
        stats = dict(total=len(appts), reports=Report.query.filter_by(patient_id=u.id).count(),
                     doctors=User.query.filter_by(role='doctor', approved=True).count())
        upcoming = [a for a in appts if a.status in ('Pending', 'Confirmed') and a.date >= date.today().isoformat()]
        upcoming.sort(key=lambda a: (a.date, a.time))
        return render_template('dashboard.html', stats=stats, upcoming=upcoming[:1],
                               docs=User.query.filter_by(role='doctor', approved=True).all())
    if u.role == 'doctor':
        appts = Appointment.query.filter_by(doctor_id=u.id).all()
        stats = dict(today=sum(a.date == date.today().isoformat() for a in appts),
                     patients=len({a.patient_id for a in appts}),
                     pending=sum(a.status == 'Pending' for a in appts),
                     reports=Report.query.filter_by(doctor_id=u.id).count())
        return render_template('dashboard.html', stats=stats)
    stats = dict(patients=User.query.filter_by(role='patient').count(),
                 doctors=User.query.filter_by(role='doctor').count(),
                 appointments=Appointment.query.count(),
                 completed=Appointment.query.filter_by(status='Completed').count(),
                 cancelled=Appointment.query.filter_by(status='Cancelled').count(),
                 reports=Report.query.count())
    return render_template('dashboard.html', stats=stats)

# ---------------- PATIENT ----------------
@app.route('/doctors')
@role_required('patient')
def doctors():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='doctor', approved=True, active=True)
    if q:
        query = query.filter(User.full_name.ilike(f'%{q}%') | User.specialization.ilike(f'%{q}%'))
    return render_template('doctors.html', docs=query.all(), q=q)

@app.route('/book', methods=['GET', 'POST'])
@role_required('patient')
def book():
    u = current_user()
    docs = User.query.filter_by(role='doctor', approved=True).all()
    doc_id = request.values.get('doctor_id', type=int)
    sel_date = request.values.get('date', '')
    taken = []
    if doc_id and sel_date:
        taken = [a.time for a in Appointment.query.filter_by(doctor_id=doc_id, date=sel_date)
                 if a.status != 'Cancelled']
    if request.method == 'POST' and request.form.get('time'):
        f = request.form
        if f['time'] in taken:
            flash('That slot was just booked. Pick another.', 'error')
        elif f['date'] < date.today().isoformat():
            flash('Date cannot be in the past', 'error')
        else:
            a = Appointment(patient_id=u.id, doctor_id=int(f['doctor_id']), date=f['date'], time=f['time'],
                            type=f['type'], reason=f['reason'])
            db.session.add(a)
            notify(a.doctor_id, f'New appointment request from {u.full_name} on {a.date} {a.time}')
            notify(u.id, f'Appointment booked for {a.date} at {a.time}')
            db.session.commit()
            flash(f'Appointment booked successfully! ID: APT{1000 + a.id}', 'success')
            return redirect(url_for('appointments'))
    free = [s for s in SLOTS if s not in taken]
    return render_template('book.html', docs=docs, doc_id=doc_id, sel_date=sel_date, free=free,
                           today=date.today().isoformat(), followup=request.args.get('followup'))

@app.route('/appointments')
@role_required('patient', 'doctor')
def appointments():
    u = current_user()
    col = Appointment.patient_id if u.role == 'patient' else Appointment.doctor_id
    appts = Appointment.query.filter(col == u.id).order_by(Appointment.date.desc()).all()
    return render_template('appointments.html', appts=appts)

@app.route('/appointment/<int:id>/<action>', methods=['POST'])
@role_required('patient', 'doctor', 'admin')
def appointment_action(id, action):
    u = current_user(); a = db.get_or_404(Appointment, id)
    allowed = {'cancel': 'Cancelled', 'accept': 'Confirmed', 'reject': 'Cancelled', 'complete': 'Completed'}
    owner = (u.role == 'patient' and a.patient_id == u.id) or (u.role == 'doctor' and a.doctor_id == u.id) or u.role == 'admin'
    if not owner or action not in allowed or (u.role == 'patient' and action != 'cancel'):
        abort(403)
    a.status = allowed[action]
    notify(a.patient_id, f'Your appointment on {a.date} is now {a.status}')
    db.session.commit()
    flash(f'Appointment {a.status.lower()}', 'success')
    return redirect(request.referrer or url_for('appointments'))

@app.route('/notifications')
@role_required('patient', 'doctor', 'admin')
def notifications():
    u = current_user()
    items = Notification.query.filter_by(user_id=u.id).order_by(Notification.id.desc()).all()
    html = render_template('notifications.html', items=items)
    for n in items: n.is_read = True
    db.session.commit()
    return html

@app.route('/profile', methods=['GET', 'POST'])
@role_required('patient', 'doctor', 'admin')
def profile():
    u = current_user()
    if request.method == 'POST':
        for field in ['full_name', 'phone', 'dob', 'gender', 'blood_group', 'emergency_contact',
                      'specialization', 'qualification', 'about']:
            if field in request.form: setattr(u, field, request.form[field])
        if 'experience' in request.form: u.experience = int(request.form['experience'] or 0)
        if 'fee' in request.form: u.fee = int(request.form['fee'] or 0)
        db.session.commit(); flash('Profile updated', 'success')
    return render_template('profile.html')

# ---------------- REPORTS ----------------
@app.route('/reports')
@role_required('patient', 'doctor', 'admin')
def reports():
    u = current_user()
    q = Report.query
    if u.role == 'patient': q = q.filter_by(patient_id=u.id)
    elif u.role == 'doctor': q = q.filter_by(doctor_id=u.id)
    return render_template('reports.html', reports=q.order_by(Report.id.desc()).all())

@app.route('/report/<int:id>')
@role_required('patient', 'doctor', 'admin')
def report_view(id):
    u = current_user(); r = db.get_or_404(Report, id)
    if (u.role == 'patient' and r.patient_id != u.id) or (u.role == 'doctor' and r.doctor_id != u.id):
        abort(403)  # users can only see their own reports
    return render_template('report_view.html', r=r)

@app.route('/generate-report', methods=['GET', 'POST'])
@role_required('doctor')
def generate_report():
    u = current_user()
    ids = {a.patient_id for a in Appointment.query.filter_by(doctor_id=u.id)}
    patients = User.query.filter(User.id.in_(ids)).all() if ids else []
    if request.method == 'POST':
        f = request.form
        if int(f['patient_id']) not in ids: abort(403)
        r = Report(patient_id=int(f['patient_id']), doctor_id=u.id, bp=f['bp'], hr=f['hr'],
                   cholesterol=f['cholesterol'], sugar=f['sugar'], ecg=f['ecg'], echo=f['echo'],
                   diagnosis=f['diagnosis'], notes=f['notes'])
        for n, d, fr, du in zip(f.getlist('med_name'), f.getlist('med_dose'), f.getlist('med_freq'), f.getlist('med_dur')):
            if n.strip(): r.medicines.append(Medicine(name=n, dosage=d, frequency=fr, duration=du))
        db.session.add(r)
        notify(r.patient_id, f'New health report available from Dr. {u.full_name}')
        db.session.commit(); flash('Report generated', 'success')
        return redirect(url_for('reports'))
    return render_template('generate_report.html', patients=patients)

# ---------------- ADMIN ----------------
@app.route('/admin/users')
@role_required('admin')
def admin_users():
    return render_template('admin_users.html', users=User.query.order_by(User.role).all())

@app.route('/admin/user/<int:id>/<action>', methods=['POST'])
@role_required('admin')
def admin_user_action(id, action):
    u = db.get_or_404(User, id)
    if u.role == 'admin': abort(403)
    if action == 'approve': u.approved = True
    elif action == 'toggle': u.active = not u.active
    elif action == 'delete':
        Appointment.query.filter((Appointment.patient_id == id) | (Appointment.doctor_id == id)).delete()
        Report.query.filter((Report.patient_id == id) | (Report.doctor_id == id)).delete()
        db.session.delete(u)
    db.session.commit(); flash('Done', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/appointments')
@role_required('admin')
def admin_appointments():
    return render_template('appointments.html', appts=Appointment.query.all())

# ---------------- DATABASE SETUP + DEMO DATA ----------------
def seed():
    if User.query.first(): return
    def mk(**kw):
        pw = kw.pop('pw'); u = User(password_hash=generate_password_hash(pw), **kw)
        db.session.add(u); return u
    mk(username='admin', pw='admin123', role='admin', full_name='Admin', email='admin@meditrust.com')
    p = mk(username='patient1', pw='patient123', role='patient', full_name='Harsh Rane', email='harsh@mail.com',
           phone='9999999999', dob='2000-05-01', gender='Male', blood_group='B+', emergency_contact='Mother - 8888888888')
    docs = []
    for i, (n, s, q, e, fee) in enumerate([('Smith', 'Cardiologist', 'MD Cardiology', 12, 800),
            ('Jane', 'Dermatologist', 'MD Dermatology', 8, 600), ('John', 'Neurologist', 'DM Neurology', 15, 900),
            ('Akriti', 'Dentist', 'BDS, MDS', 6, 500), ('Manish', 'Physician', 'MBBS, MD', 10, 400)], 1):
        docs.append(mk(username=f'doctor{i}', pw='doctor123', role='doctor', full_name=n, email=f'doc{i}@meditrust.com',
                       phone=f'90000000{i}', specialization=s, qualification=q, experience=e, fee=fee,
                       about=f'Dr. {n} is an experienced {s.lower()} dedicated to patient care.'))
    db.session.commit()
    db.session.add_all([Appointment(patient_id=p.id, doctor_id=docs[0].id, date='2026-09-09', time='10:30', type='In-person', reason='Chest pain checkup', status='Completed'),
                        Appointment(patient_id=p.id, doctor_id=docs[0].id, date='2026-12-10', time='10:30', type='Online', reason='Follow-up', status='Confirmed')])
    r = Report(patient_id=p.id, doctor_id=docs[0].id, bp='120/80', hr='72', cholesterol='180', sugar='95',
               ecg='Normal', echo='Normal', diagnosis='Healthy heart', notes='Exercise regularly.', report_date='2026-09-09')
    r.medicines.append(Medicine(name='Aspirin', dosage='75 mg', frequency='1 time/day', duration='30 days'))
    db.session.add(r); db.session.commit()

with app.app_context():
    db.create_all()
    seed()

if __name__ == '__main__':
    app.run(debug=True)
