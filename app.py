import os
import json as _json

from datetime import datetime, timedelta, timezone

from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    session,
    jsonify
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

from models import db, User


# ════════════════════════════════════════════════════════════════
# Flask App
# ════════════════════════════════════════════════════════════════

app = Flask(__name__)


# ════════════════════════════════════════════════════════════════
# Basic Config
# ════════════════════════════════════════════════════════════════

app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'change_this_secret_key'
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
    'pool_recycle': 300
}

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)


# ════════════════════════════════════════════════════════════════
# Mail Config
# ════════════════════════════════════════════════════════════════

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get(
    'MAIL_USERNAME',
    ''
)

app.config['MAIL_PASSWORD'] = os.environ.get(
    'MAIL_PASSWORD',
    ''
)

app.config['MAIL_DEFAULT_SENDER'] = os.environ.get(
    'MAIL_USERNAME',
    'noreply@iut-dhaka.edu'
)


# ════════════════════════════════════════════════════════════════
# Extensions
# ════════════════════════════════════════════════════════════════

csrf = CSRFProtect(app)

db.init_app(app)

migrate = Migrate(app, db)

bcrypt = Bcrypt(app)

mail = Mail(app)

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading'
)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[
        "200 per day",
        "60 per hour"
    ],
    storage_uri="memory://"
)

login_manager = LoginManager(app)

login_manager.login_view = 'auth.login'

login_manager.login_message_category = 'info'


# ════════════════════════════════════════════════════════════════
# User Loader
# ════════════════════════════════════════════════════════════════

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# ════════════════════════════════════════════════════════════════
# Safe Session Cleanup
# ════════════════════════════════════════════════════════════════

@app.teardown_appcontext
def shutdown_session(exception=None):

    if exception:
        db.session.rollback()

    db.session.remove()


# ════════════════════════════════════════════════════════════════
# JSON Filter
# ════════════════════════════════════════════════════════════════

@app.template_filter("from_json")
def from_json_filter(value):

    if not value:
        return {}

    try:
        return _json.loads(value)

    except Exception:
        return {}


# ════════════════════════════════════════════════════════════════
# Database Initialization
# ════════════════════════════════════════════════════════════════

with app.app_context():

    db_dir = os.path.join(
        basedir,
        'database'
    )

    os.makedirs(
        db_dir,
        exist_ok=True
    )

    db.create_all()

    # Create default super admin

    if not User.query.filter_by(role='super_admin').first():

        from flask_bcrypt import Bcrypt as _B

        _b = _B()

        super_admin = User(
            name='Super Admin',
            email='superadmin@iut-dhaka.edu',
            password=_b.generate_password_hash(
                'SuperAdmin@2026!'
            ).decode('utf-8'),
            role='super_admin',
            email_verified=True,
            is_active=True
        )

        db.session.add(super_admin)

        db.session.commit()

        print(
            '[IUT] Super Admin Created'
        )


# ════════════════════════════════════════════════════════════════
# Session Timeout
# ════════════════════════════════════════════════════════════════

@app.before_request
def check_session_timeout():

    if current_user.is_authenticated:

        last_activity = session.get('last_activity')

        current_time = datetime.now(
            timezone.utc
        ).timestamp()

        if last_activity:

            inactive_time = current_time - last_activity

            if inactive_time > 30 * 60:

                logout_user()

                session.clear()

                from flask import flash

                flash(
                    'Session expired due to inactivity.',
                    'warning'
                )

                return redirect(
                    url_for('auth.login')
                )

        session['last_activity'] = current_time

        session.permanent = True


# ════════════════════════════════════════════════════════════════
# Dynamic Time Slot Generator
# ════════════════════════════════════════════════════════════════

def generate_time_slots(
    start_str="08:00",
    end_str="17:00",
    duration=30
):

    slots = []

    fmt = "%H:%M"

    current = datetime.strptime(
        start_str,
        fmt
    )

    end = datetime.strptime(
        end_str,
        fmt
    )

    while current < end:

        next_time = current + timedelta(
            minutes=duration
        )

        if next_time > end:
            break

        slots.append(
            f"{current.strftime('%I:%M %p')} - "
            f"{next_time.strftime('%I:%M %p')}"
        )

        current = next_time

    return slots


# ════════════════════════════════════════════════════════════════
# QR Code Generator
# ════════════════════════════════════════════════════════════════

def generate_qr_data(
    appointment_id,
    token
):

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

        buffer = io.BytesIO()

        img.save(buffer, format='PNG')

        qr_base64 = base64.b64encode(
            buffer.getvalue()
        ).decode()

        return data, qr_base64

    except Exception:

        return data, ""


# ════════════════════════════════════════════════════════════════
# Socket.IO Realtime Events
# ════════════════════════════════════════════════════════════════

@socketio.on('join')
def on_join(data):

    room = str(
        data.get('user_id', '')
    )

    if room:
        join_room(room)


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
            ).isoformat()
        },
        room=str(user_id)
    )


# ════════════════════════════════════════════════════════════════
# Error Handlers
# ════════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(error):

    return render_template(
        'errors/404.html'
    ), 404


@app.errorhandler(500)
def server_error(error):

    return render_template(
        'errors/500.html'
    ), 500


@app.errorhandler(403)
def forbidden(error):

    return render_template(
        'errors/403.html'
    ), 403


@app.errorhandler(429)
def rate_limit(error):

    return render_template(
        'errors/429.html'
    ), 429


# ════════════════════════════════════════════════════════════════
# Register Blueprints
# ════════════════════════════════════════════════════════════════

from routes.auth import auth_bp
from routes.student import student_bp
from routes.admin import admin_bp
from routes.officer import officer_bp
from routes.super_admin import super_admin_bp

app.register_blueprint(auth_bp)

app.register_blueprint(student_bp)

app.register_blueprint(admin_bp)

app.register_blueprint(officer_bp)

app.register_blueprint(super_admin_bp)

limiter.limit(
    "10 per minute"
)(auth_bp)


# ════════════════════════════════════════════════════════════════
# Home Route
# ════════════════════════════════════════════════════════════════

@app.route('/')
def index():

    if current_user.is_authenticated:

        role = current_user.role

        if role == 'super_admin':

            return redirect(
                url_for(
                    'super_admin.dashboard'
                )
            )

        if role == 'admin':

            return redirect(
                url_for(
                    'admin.dashboard'
                )
            )

        if role == 'officer':

            return redirect(
                url_for(
                    'officer.dashboard'
                )
            )

        return redirect(
            url_for(
                'student.dashboard'
            )
        )

    return render_template(
        'home.html'
    )


# ════════════════════════════════════════════════════════════════
# Notification API
# ════════════════════════════════════════════════════════════════

@app.route('/api/notifications/unread-count')
def unread_count():

    from models import Notification

    if not current_user.is_authenticated:

        return jsonify({
            'count': 0
        })

    try:

        unread = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()

        return jsonify({
            'count': unread
        })

    except Exception:

        db.session.rollback()

        return jsonify({
            'count': 0
        })


# ════════════════════════════════════════════════════════════════
# Main Entry
# ════════════════════════════════════════════════════════════════

if __name__ == '__main__':

    port = int(
        os.environ.get('PORT', 5000)
    )

    debug = (
        os.environ.get('FLASK_ENV')
        == 'development'
    )

    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=True
    )
