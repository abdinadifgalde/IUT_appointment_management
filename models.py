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
# ─────────────────────────────────────────────────────────────
# OFFICER MODEL
# ─────────────────────────────────────────────────────────────

class Officer(db.Model):

    __tablename__ = 'officer'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    designation = db.Column(db.String(100), default='Officer')

    department = db.Column(db.String(100))

    room = db.Column(db.String(100))

    photo_url = db.Column(db.String(255))

    bio = db.Column(db.Text)

    handles = db.Column(db.Text)  # comma-separated tags

    work_start = db.Column(db.String(10), default='08:00')

    work_end = db.Column(db.String(10), default='17:00')

    daily_limit = db.Column(db.Integer, default=0)  # 0 = unlimited

    recurring_off_days = db.Column(db.String(50), default='')  # e.g. "5,6" for Sat,Sun

    avg_appointment_duration = db.Column(db.Integer, default=15)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    unavailabilities = db.relationship(
        'OfficerUnavailability',
        backref='officer',
        lazy=True,
        cascade='all, delete-orphan'
    )

    working_hours = db.relationship(
        'OfficerWorkingHours',
        backref='officer',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def get_off_days(self):
        """Return set of weekday integers (0=Mon … 6=Sun) that are off."""
        if not self.recurring_off_days:
            return set()
        try:
            return {int(d) for d in self.recurring_off_days.split(',') if d.strip()}
        except ValueError:
            return set()

    def get_handles(self):
        if not self.handles:
            return []
        return [h.strip() for h in self.handles.split(',') if h.strip()]

    def __repr__(self):
        return f'<Officer {self.name}>'


# ─────────────────────────────────────────────────────────────
# OFFICER UNAVAILABILITY
# ─────────────────────────────────────────────────────────────

class OfficerUnavailability(db.Model):

    __tablename__ = 'officer_unavailability'

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False
    )

    start_date = db.Column(db.Date, nullable=False)

    end_date = db.Column(db.Date, nullable=False)

    reason = db.Column(db.String(255))

    def __repr__(self):
        return f'<OfficerUnavailability officer={self.officer_id}>'


# ─────────────────────────────────────────────────────────────
# OFFICER WORKING HOURS (per-weekday overrides)
# ─────────────────────────────────────────────────────────────

class OfficerWorkingHours(db.Model):

    __tablename__ = 'officer_working_hours'

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False
    )

    weekday = db.Column(db.Integer, nullable=False)  # 0=Mon … 6=Sun

    start_time = db.Column(db.String(10), nullable=False)

    end_time = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<OfficerWorkingHours officer={self.officer_id} weekday={self.weekday}>'


# ─────────────────────────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────────────────────────

class AuditLog(db.Model):

    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)

    admin_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    action = db.Column(db.String(100), nullable=False)

    detail = db.Column(db.Text)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action}>'


# ─────────────────────────────────────────────────────────────
# APPOINTMENT TIMELINE
# ─────────────────────────────────────────────────────────────

class AppointmentTimeline(db.Model):

    __tablename__ = 'appointment_timeline'

    id = db.Column(db.Integer, primary_key=True)

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id'),
        nullable=False
    )

    status = db.Column(db.String(50), nullable=False)

    note = db.Column(db.Text)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AppointmentTimeline apt={self.appointment_id} status={self.status}>'
