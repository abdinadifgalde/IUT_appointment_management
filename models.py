from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
import secrets

# ═════════════════════════════════════════════════════════════════════════════
# Database
# ═════════════════════════════════════════════════════════════════════════════

db = SQLAlchemy()

# ═════════════════════════════════════════════════════════════════════════════
# Roles
# ═════════════════════════════════════════════════════════════════════════════

VALID_ROLES = (
    'student',
    'officer',
    'admin',
    'super_admin'
)

PRIVILEGED_ROLES = (
    'officer',
    'admin',
    'super_admin'
)

# ═════════════════════════════════════════════════════════════════════════════
# Appointment Statuses
# ═════════════════════════════════════════════════════════════════════════════

APPOINTMENT_STATUSES = (
    'Pending',
    'Confirmed',
    'Rejected',
    'Completed',
    'Cancelled',
    'No Show',
    'Rescheduled'
)

# ═════════════════════════════════════════════════════════════════════════════
# User Model
# ═════════════════════════════════════════════════════════════════════════════

class User(db.Model, UserMixin):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    role = db.Column(
        db.String(20),
        nullable=False,
        default='student'
    )

    student_id_num = db.Column(
        db.String(50),
        nullable=True
    )

    department = db.Column(
        db.String(100),
        nullable=True
    )

    dark_mode = db.Column(
        db.Boolean,
        default=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    email_verified = db.Column(
        db.Boolean,
        default=False
    )

    email_verify_token = db.Column(
        db.String(64),
        nullable=True
    )

    failed_logins = db.Column(
        db.Integer,
        default=0
    )

    locked_until = db.Column(
        db.DateTime,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    last_seen = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    appointments = db.relationship(
        'Appointment',
        backref='student_user',
        lazy=True
    )

    notifications = db.relationship(
        'Notification',
        backref='user',
        lazy=True
    )

    def generate_verify_token(self):
        self.email_verify_token = secrets.token_urlsafe(32)
        return self.email_verify_token

    def is_locked(self):
        if (
            self.locked_until and
            datetime.now(timezone.utc).replace(tzinfo=None)
            < self.locked_until
        ):
            return True

        return False


# ═════════════════════════════════════════════════════════════════════════════
# Password Reset Token
# ═════════════════════════════════════════════════════════════════════════════

class PasswordResetToken(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        index=True
    )

    expires_at = db.Column(
        db.DateTime,
        nullable=False
    )

    used = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship(
        'User',
        backref='reset_tokens'
    )


# ═════════════════════════════════════════════════════════════════════════════
# Officer Model
# ═════════════════════════════════════════════════════════════════════════════

class Officer(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    designation = db.Column(
        db.String(100),
        nullable=False
    )

    bio = db.Column(
        db.Text,
        nullable=True
    )

    handles = db.Column(
        db.Text,
        nullable=True
    )

    email = db.Column(
        db.String(120),
        nullable=True
    )

    room = db.Column(
        db.String(50),
        nullable=True
    )

    photo_url = db.Column(
        db.String(255),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    work_start = db.Column(
        db.String(5),
        default='08:00'
    )

    work_end = db.Column(
        db.String(5),
        default='17:00'
    )

    daily_limit = db.Column(
        db.Integer,
        default=0
    )

    recurring_off_days = db.Column(
        db.String(20),
        default=''
    )

    avg_appointment_duration = db.Column(
        db.Integer,
        default=15
    )

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

        if not self.recurring_off_days:
            return []

        return [
            int(day)
            for day in self.recurring_off_days.split(',')
            if day
        ]

    def get_handles(self):

        if not self.handles:
            return []

        return [
            handle.strip()
            for handle in self.handles.split(',')
            if handle.strip()
        ]


# ═════════════════════════════════════════════════════════════════════════════
# Officer Working Hours
# ═════════════════════════════════════════════════════════════════════════════

class OfficerWorkingHours(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False
    )

    weekday = db.Column(
        db.Integer,
        nullable=False
    )

    start_time = db.Column(
        db.String(5),
        nullable=False
    )

    end_time = db.Column(
        db.String(5),
        nullable=False
    )


# ═════════════════════════════════════════════════════════════════════════════
# Officer Unavailability
# ═════════════════════════════════════════════════════════════════════════════

class OfficerUnavailability(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    reason = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    def is_active_on(self, date):
        return self.start_date <= date <= self.end_date


# ═════════════════════════════════════════════════════════════════════════════
# Appointment Model
# ═════════════════════════════════════════════════════════════════════════════

class Appointment(db.Model):

    id = db.Column(db.Integer, primary_key=True)

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

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False
    )

    officer = db.relationship(
        'Officer',
        backref='appointments'
    )

    day = db.Column(
        db.String(20),
        nullable=False
    )

    date = db.Column(
        db.Date,
        nullable=False
    )

    time = db.Column(
        db.String(20),
        nullable=False
    )

    end_time = db.Column(
        db.String(20),
        nullable=True
    )

    duration = db.Column(
        db.Integer,
        default=15
    )

    issue = db.Column(
        db.Text,
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default='Pending'
    )

    priority = db.Column(
        db.String(20),
        default='Normal'
    )

    meeting_type = db.Column(
        db.String(20),
        default='in-person'
    )

    location = db.Column(
        db.String(255),
        nullable=True
    )

    meeting_link = db.Column(
        db.String(255),
        nullable=True
    )

    recording_link = db.Column(
        db.String(255),
        nullable=True
    )

    session_notes = db.Column(
        db.Text,
        nullable=True
    )

    no_show = db.Column(
        db.Boolean,
        default=False
    )

    rejection_note = db.Column(
        db.Text,
        nullable=True
    )

    reminder_sent = db.Column(
        db.Boolean,
        default=False
    )

    queue_number = db.Column(
        db.Integer,
        nullable=True
    )

    estimated_wait_time = db.Column(
        db.Integer,
        nullable=True
    )

    qr_code_data = db.Column(
        db.String(255),
        nullable=True
    )

    calendar_color = db.Column(
        db.String(20),
        default='#0d6efd'
    )

    previous_schedule = db.Column(
        db.Text,
        nullable=True
    )

    reschedule_requested = db.Column(
        db.Boolean,
        default=False
    )

    reschedule_message = db.Column(
        db.Text,
        nullable=True
    )

    reschedule_proposed_date = db.Column(
        db.Date,
        nullable=True
    )

    reschedule_proposed_time = db.Column(
        db.String(20),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    completed_at = db.Column(
        db.DateTime,
        nullable=True
    )

    status_updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    def get_start_datetime(self):

        return datetime.strptime(
            f'{self.date} {self.time}',
            '%Y-%m-%d %H:%M'
        )

    def get_end_datetime(self):

        start = self.get_start_datetime()

        return start + timedelta(
            minutes=self.duration or 15
        )

    def is_upcoming(self):

        return (
            self.get_start_datetime()
            > datetime.now()
        )

    def is_completed(self):

        return self.status.lower() == 'completed'

    def mark_completed(self):

        self.status = 'Completed'

        self.completed_at = datetime.now(
            timezone.utc
        )

    def mark_no_show(self):

        self.no_show = True
        self.status = 'No Show'


# ═════════════════════════════════════════════════════════════════════════════
# Waitlist Entry
# ═════════════════════════════════════════════════════════════════════════════

class WaitlistEntry(db.Model):

    __tablename__ = 'waitlist_entry'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    officer_id = db.Column(
        db.Integer,
        db.ForeignKey('officer.id'),
        nullable=False,
        index=True
    )

    slot_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    slot_time = db.Column(
        db.String(30),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False,
        index=True
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
        default=lambda: datetime.now(timezone.utc)
    )

    user = db.relationship(
        'User',
        backref='waitlist_entries'
    )

    officer = db.relationship(
        'Officer',
        backref='waitlist_entries'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'officer_id',
            'slot_date',
            'slot_time',
            'user_id',
            name='uq_waitlist_student_slot'
        ),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Notification
# ═════════════════════════════════════════════════════════════════════════════

class Notification(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

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
        default=lambda: datetime.now(timezone.utc)
    )


# ═════════════════════════════════════════════════════════════════════════════
# Appointment History
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentHistory(db.Model):

    __tablename__ = 'appointment_history'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id'),
        nullable=False,
        index=True
    )

    action = db.Column(
        db.String(80),
        nullable=False
    )

    action_type = db.Column(
        db.String(50),
        default='general'
    )

    old_value = db.Column(
        db.Text,
        nullable=True
    )

    new_value = db.Column(
        db.Text,
        nullable=True
    )

    changed_by = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )

    note = db.Column(
        db.Text,
        nullable=True
    )

    timestamp = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    appointment = db.relationship(
        'Appointment',
        backref='history_events'
    )

    actor = db.relationship(
        'User',
        backref='history_actions'
    )


# ═════════════════════════════════════════════════════════════════════════════
# Appointment Guests
# ═════════════════════════════════════════════════════════════════════════════

class AppointmentGuest(db.Model):

    __tablename__ = 'appointment_guest'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    appointment_id = db.Column(
        db.Integer,
        db.ForeignKey('appointment.id'),
        nullable=False,
        index=True
    )

    guest_email = db.Column(
        db.String(120),
        nullable=False
    )

    added_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    appointment = db.relationship(
        'Appointment',
        backref='guests'
    )
