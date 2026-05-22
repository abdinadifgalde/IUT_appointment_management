from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# ─────────────────────────────────────────────────────────────
# USER MODEL
# ─────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False)

    department = db.Column(db.String(100))

    profile_image = db.Column(
        db.String(255),
        default='default_profile.png'
    )

    email_verified = db.Column(
        db.Boolean,
        default=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Relationships

    student_appointments = db.relationship(
        'Appointment',
        foreign_keys='Appointment.student_id',
        backref='student',
        lazy=True
    )

    officer_appointments = db.relationship(
        'Appointment',
        foreign_keys='Appointment.officer_id',
        backref='officer',
        lazy=True
    )

    notifications = db.relationship(
        'Notification',
        backref='user',
        lazy=True
    )

    def __repr__(self):

        return f'<User {self.email}>'

# ─────────────────────────────────────────────────────────────
# APPOINTMENT MODEL
# ─────────────────────────────────────────────────────────────

class Appointment(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    title = db.Column(
        db.String(255),
        nullable=False
    )

    description = db.Column(db.Text)

    appointment_date = db.Column(
        db.Date,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    duration = db.Column(
        db.Integer,
        default=15
    )

    location = db.Column(
        db.String(255),
        default='IUT Campus'
    )

    meeting_type = db.Column(
        db.String(50),
        default='In-person'
    )

    timezone = db.Column(
        db.String(100),
        default='Asia/Dhaka'
    )

    notes = db.Column(db.Text)

    recording_link = db.Column(
        db.String(500)
    )

    appointment_status = db.Column(
        db.String(30),
        default='Pending'
    )

    no_show = db.Column(
        db.Boolean,
        default=False
    )

    previous_schedule = db.Column(db.Text)

    overlay_calendar = db.Column(
        db.Boolean,
        default=False
    )

    requires_confirmation = db.Column(
        db.Boolean,
        default=True
    )

    booked_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships

    history = db.relationship(
        'AppointmentHistory',
        backref='appointment',
        lazy=True,
        cascade='all, delete-orphan'
    )

    guests = db.relationship(
        'AppointmentGuest',
        backref='appointment',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def __repr__(self):

        return f'<Appointment {self.id}>'

# ─────────────────────────────────────────────────────────────
# APPOINTMENT HISTORY
# ─────────────────────────────────────────────────────────────

class AppointmentHistory(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id'),
        nullable=False
    )

    action = db.Column(
        db.String(100),
        nullable=False
    )

    old_value = db.Column(db.Text)

    new_value = db.Column(db.Text)

    changed_by = db.Column(
        db.String(100)
    )

    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    def __repr__(self):

        return f'<AppointmentHistory {self.id}>'

# ─────────────────────────────────────────────────────────────
# APPOINTMENT GUESTS
# ─────────────────────────────────────────────────────────────

class AppointmentGuest(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id'),
        nullable=False
    )

    guest_name = db.Column(
        db.String(100)
    )

    guest_email = db.Column(
        db.String(120)
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ─────────────────────────────────────────────────────────────
# NOTIFICATION MODEL
# ─────────────────────────────────────────────────────────────

class Notification(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    message = db.Column(
        db.String(500),
        nullable=False
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ─────────────────────────────────────────────────────────────
# OFFICER AVAILABILITY MODEL
# ─────────────────────────────────────────────────────────────

class OfficerAvailability(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    weekday = db.Column(
        db.Integer,
        nullable=False
    )

    start_time = db.Column(
        db.Time,
        nullable=False
    )

    end_time = db.Column(
        db.Time,
        nullable=False
    )

    is_available = db.Column(
        db.Boolean,
        default=True
    )

# ─────────────────────────────────────────────────────────────
# WAITLIST MODEL
# ─────────────────────────────────────────────────────────────

class WaitlistEntry(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        nullable=False
    )

    slot_date = db.Column(
        db.Date,
        nullable=False
    )

    slot_time = db.Column(
        db.String(30),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    student_name = db.Column(
        db.String(100),
        nullable=False
    )

    student_id_num = db.Column(
        db.String(50),
        nullable=False
    )

    department = db.Column(
        db.String(100),
        nullable=False
    )

    issue = db.Column(
        db.Text,
        nullable=False
    )

    joined_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

# ─────────────────────────────────────────────────────────────
# SAVED CALENDAR OVERLAYS
# ─────────────────────────────────────────────────────────────

class CalendarOverlay(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    overlay_name = db.Column(
        db.String(100)
    )

    start_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    end_datetime = db.Column(
        db.DateTime,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )
