# Full Advanced `app.py` Code

```python
import os

from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    session,
    request as flask_request
)

from flask_login import (
    LoginManager,
    current_user,
    logout_user
)

from flask_wtf.csrf import CSRFProtect

from flask_bcrypt import Bcrypt

from flask_mail import Mail

from flask_migrate import Migrate

from flask_limiter import Limiter

from flask_limiter.util import get_remote_address

from flask_socketio import (
    SocketIO,
    emit,
    join_room
)

from models import (
    db,
    User,
    Appointment,
    Notification,
    AppointmentHistory,
    AppointmentGuest
)

from datetime import (
    datetime,
    timedelta,
    timezone
)

app = Flask(__name__)

# ──────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

app.config['SECRET_KEY'] = (
    os.environ.get('SECRET_KEY')
    or 'iut_secret_key_change_in_prod_2026!'
)

basedir = os.path.abspath(os.path.dirname(__file__))

database_url = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(
        basedir,
        'database',
        'university.db'
    )
)

if database_url.startswith('postgres://'):
    database_url = database_url.replace(
        'postgres://',
        'postgresql+psycopg://',
        1
    )

if database_url.startswith('postgresql://') and '+' not in database_url:
    database_url = database_url.replace(
        'postgresql://',
        'postgresql+psycopg://',
        1
    )

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# ──────────────────────────────────────────────────────────────────────
# ADVANCED BOOKING SETTINGS
# ──────────────────────────────────────────────────────────────────────

app.config['DEFAULT_TIMEZONE'] = 'Asia/Dhaka'

app.config['DEFAULT_SLOT_DURATION'] = 15

app.config['MIN_BOOKING_DURATION'] = 5

app.config['MAX_BOOKING_DURATION'] = 120

app.config['BOOKING_START_HOUR'] = 8

app.config['BOOKING_END_HOUR'] = 17

app.config['ENABLE_OVERLAY_CALENDAR'] = True

# ──────────────────────────────────────────────────────────────────────
# MAIL CONFIGURATION
# ──────────────────────────────────────────────────────────────────────

app.config['MAIL_SERVER'] = 'smtp.gmail.com'

app.config['MAIL_PORT'] = 587

app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')

app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')

app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
    'MAIL_USERNAME',
    'noreply@iut-dhaka.edu'
)

# ──────────────────────────────────────────────────────────────────────
# EXTENSIONS
# ──────────────────────────────────────────────────────────────────────

csrf = CSRFProtect(app)

db.init_app(app)

migrate = Migrate(app, db)

bcrypt = Bcrypt(app)

mail = Mail(app)

socketio = SocketIO(app, cors_allowed_origins='*')

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)

login_manager = LoginManager(app)

login_manager.login_view = 'auth.login'

login_manager.login_message_category = 'info'

# ──────────────────────────────────────────────────────────────────────
# LOGIN LOADER
# ──────────────────────────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(User, int(user_id))

# ──────────────────────────────────────────────────────────────────────
# SESSION CLEANUP
# ──────────────────────────────────────────────────────────────────────

@app.teardown_appcontext
def shutdown_session(exception=None):

    if exception:
        db.session.rollback()

    db.session.remove()

# ──────────────────────────────────────────────────────────────────────
# DATABASE INIT
# ──────────────────────────────────────────────────────────────────────

with app.app_context():

    db_dir = os.path.join(basedir, 'database')

    os.makedirs(db_dir, exist_ok=True)

    db.create_all()

    # CREATE DEFAULT SUPER ADMIN

    if not User.query.filter_by(role='super_admin').first():

        from flask_bcrypt import Bcrypt as _B

        _b = _B()

        sa = User(
            name='Super Admin',
            email='superadmin@iut-dhaka.edu',
            password=_b.generate_password_hash(
                'SuperAdmin@2026!'
            ).decode('utf-8'),
            role='super_admin',
            email_verified=True,
            is_active=True,
        )

        db.session.add(sa)

        db.session.commit()

        print(
            '[IUT] Default super_admin created'
        )

# ──────────────────────────────────────────────────────────────────────
# SESSION TIMEOUT
# ──────────────────────────────────────────────────────────────────────

@app.before_request
def check_session_timeout():

    if current_user.is_authenticated:

        last = session.get('last_activity')

        now = datetime.now(timezone.utc).timestamp()

        if last and (now - last) > 30 * 60:

            logout_user()

            session.clear()

            from flask import flash

            flash(
                'Session expired due to inactivity.',
                'warning'
            )

            return redirect(url_for('auth.login'))

        session['last_activity'] = now

        session.permanent = True

# ──────────────────────────────────────────────────────────────────────
# ADVANCED SLOT GENERATOR
# ──────────────────────────────────────────────────────────────────────

def generate_time_slots(
    start_str="08:00",
    end_str="17:00",
    duration=15,
    booked_slots=None
):

    if booked_slots is None:
        booked_slots = []

    slots = []

    fmt = "%H:%M"

    current = datetime.strptime(start_str, fmt)

    end = datetime.strptime(end_str, fmt)

    while current + timedelta(minutes=duration) <= end:

        slot_end = current + timedelta(minutes=duration)

        overlap = False

        for booked_start, booked_end in booked_slots:

            if current < booked_end and slot_end > booked_start:
                overlap = True
                break

        if not overlap:

            slots.append({
                'start': current.strftime('%I:%M %p'),
                'end': slot_end.strftime('%I:%M %p'),
                'duration': duration
            })

        current += timedelta(minutes=duration)

    return slots

# ──────────────────────────────────────────────────────────────────────
# CONFLICT CHECKER
# ──────────────────────────────────────────────────────────────────────

def has_conflict(
    officer_id,
    appointment_date,
    start_time,
    end_time
):

    existing = Appointment.query.filter(
        Appointment.officer_id == officer_id,
        Appointment.appointment_date == appointment_date,
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
        Appointment.appointment_status != 'Rejected'
    ).first()

    return existing is not None

# ──────────────────────────────────────────────────────────────────────
# APPOINTMENT HISTORY LOGGER
# ──────────────────────────────────────────────────────────────────────

def log_appointment_action(
    appointment_id,
    action,
    old_value=None,
    new_value=None,
    changed_by=None
):

    history = AppointmentHistory(
        appointment_id=appointment_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by
    )

    db.session.add(history)

    db.session.commit()

# ──────────────────────────────────────────────────────────────────────
# QR GENERATOR
# ──────────────────────────────────────────────────────────────────────

def generate_qr_data(appointment_id, token):

    import io
    import base64

    data = f"APT-{appointment_id}-{token}"

    try:

        import qrcode

        qr = qrcode.QRCode(
            version=1,
            box_size=8,
            border=2
        )

        qr.add_data(data)

        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        buf = io.BytesIO()

        img.save(buf, format='PNG')

        b64 = base64.b64encode(
            buf.getvalue()
        ).decode()

    except Exception:

        b64 = ""

    return data, b64

# ──────────────────────────────────────────────────────────────────────
# SOCKET EVENTS
# ──────────────────────────────────────────────────────────────────────

@socketio.on('join')
def on_join(data):

    room = str(data.get('user_id', ''))

    if room:
        join_room(room)

@socketio.on('join_booking_room')
def join_booking_room(data):

    officer_id = data.get('officer_id')

    date = data.get('date')

    room = f"{officer_id}_{date}"

    join_room(room)

# ──────────────────────────────────────────────────────────────────────
# REALTIME STATUS UPDATE
# ──────────────────────────────────────────────────────────────────────

def push_status_update(
    user_id,
    appointment_id,
    status,
    message
):

    socketio.emit(
        'appointment_update',
        {
            'appointment_id': appointment_id,
            'status': status,
            'message': message,
            'timestamp': datetime.now(
                timezone.utc
            ).isoformat(),
        },
        room=str(user_id)
    )

# ──────────────────────────────────────────────────────────────────────
# SLOT UPDATE
# ──────────────────────────────────────────────────────────────────────

def push_slot_update(officer_id, date):

    socketio.emit(
        'slot_update',
        {
            'officer_id': officer_id,
            'date': str(date)
        },
        broadcast=True
    )

# ──────────────────────────────────────────────────────────────────────
# TEMPLATE VARIABLES
# ──────────────────────────────────────────────────────────────────────

@app.context_processor
def inject_booking_settings():

    return dict(
        DEFAULT_TIMEZONE=app.config['DEFAULT_TIMEZONE'],
        DEFAULT_SLOT_DURATION=app.config['DEFAULT_SLOT_DURATION'],
        BOOKING_START_HOUR=app.config['BOOKING_START_HOUR'],
        BOOKING_END_HOUR=app.config['BOOKING_END_HOUR']
    )

# ──────────────────────────────────────────────────────────────────────
# ERROR HANDLERS
# ──────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):

    return render_template(
        'errors/404.html'
    ), 404

@app.errorhandler(500)
def server_error(e):

    return render_template(
        'errors/500.html'
    ), 500

@app.errorhandler(403)
def forbidden(e):

    return render_template(
        'errors/403.html'
    ), 403

@app.errorhandler(429)
def rate_limited(e):

    return render_template(
        'errors/429.html'
    ), 429

@app.errorhandler(400)
def bad_request(e):

    return render_template(
        'errors/400.html'
    ), 400

# ──────────────────────────────────────────────────────────────────────
# BLUEPRINTS
# ──────────────────────────────────────────────────────────────────────

from routes.auth import auth_bp

from routes.student import student_bp

from routes.admin import admin_bp

from routes.officer import officer_bp

from routes.super_admin import super_admin_bp

from routes.api import api_bp

app.register_blueprint(auth_bp)

app.register_blueprint(student_bp)

app.register_blueprint(admin_bp)

app.register_blueprint(officer_bp)

app.register_blueprint(super_admin_bp)

app.register_blueprint(api_bp, url_prefix='/api')

# RATE LIMIT

limiter.limit("10 per minute")(auth_bp)

# ──────────────────────────────────────────────────────────────────────
# ROOT ROUTE
# ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():

    if current_user.is_authenticated:

        role = current_user.role

        if role == 'super_admin':
            return redirect(
                url_for('super_admin.dashboard')
            )

        if role == 'admin':
            return redirect(
                url_for('admin.dashboard')
            )

        if role == 'officer':
            return redirect(
                url_for('officer.dashboard')
            )

        return redirect(
            url_for('student.dashboard')
        )

    return render_template('home.html')

# ──────────────────────────────────────────────────────────────────────
# UNREAD NOTIFICATIONS API
# ──────────────────────────────────────────────────────────────────────

@app.route('/api/notifications/unread-count')
def unread_count():

    if not current_user.is_authenticated:
        return {'count': 0}

    try:

        count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()

        return {'count': count}

    except Exception:

        db.session.rollback()

        return {'count': 0}

# ──────────────────────────────────────────────────────────────────────
# BOOKING HEALTH CHECK
# ──────────────────────────────────────────────────────────────────────

@app.route('/api/booking/health')
def booking_health():

    return {
        'success': True,
        'message': 'Advanced booking system active',
        'timezone': app.config['DEFAULT_TIMEZONE']
    }

# ──────────────────────────────────────────────────────────────────────
# SECURITY HEADERS
# ──────────────────────────────────────────────────────────────────────

@app.after_request
def add_security_headers(response):

    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    response.headers['X-Content-Type-Options'] = 'nosniff'

    response.headers['Referrer-Policy'] = (
        'strict-origin-when-cross-origin'
    )

    return response

# ──────────────────────────────────────────────────────────────────────
# RUN SERVER
# ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    port = int(os.environ.get('PORT', 5000))

    debug = (
        os.environ.get('FLASK_ENV') == 'development'
    )

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )
```
