import os
from gevent import monkey
monkey.patch_all()

from flask import Flask, redirect, url_for, render_template, session, request as flask_request
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room
from models import db, User
from datetime import datetime, timedelta, timezone

app = Flask(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'iut_secret_key_change_in_prod_2026!'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'university.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Flask-Mail
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'noreply@iut-dhaka.edu')

# ── Extensions ────────────────────────────────────────────────────────────────
csrf = CSRFProtect(app)
db.init_app(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='gevent')

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ── DB Init ───────────────────────────────────────────────────────────────────
with app.app_context():
    db_dir = os.path.join(basedir, 'database')
    os.makedirs(db_dir, exist_ok=True)
    db.create_all()
    # Auto-create super_admin if none exists
    from models import User
    if not User.query.filter_by(role='super_admin').first():
        from flask_bcrypt import Bcrypt as _B
        _b = _B()
        sa = User(
            name='Super Admin',
            email='superadmin@iut-dhaka.edu',
            password=_b.generate_password_hash('SuperAdmin@2026!').decode('utf-8'),
            role='super_admin',
            email_verified=True,
            is_active=True,
        )
        db.session.add(sa)
        db.session.commit()
        print('[IUT] Default super_admin created: superadmin@iut-dhaka.edu / SuperAdmin@2026!')

# ── Session timeout ───────────────────────────────────────────────────────────
@app.before_request
def check_session_timeout():
    if current_user.is_authenticated:
        last = session.get('last_activity')
        now = datetime.now(timezone.utc).timestamp()
        if last and (now - last) > 30 * 60:
            logout_user()
            session.clear()
            from flask import flash
            flash('Session expired due to inactivity.', 'warning')
            return redirect(url_for('auth.login'))
        session['last_activity'] = now
        session.permanent = True
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

# ── Time slot generator ───────────────────────────────────────────────────────
def generate_time_slots(start_str="08:00", end_str="17:00"):
    slots, fmt = [], "%H:%M"
    current = datetime.strptime(start_str, fmt)
    end = datetime.strptime(end_str, fmt)
    while current < end:
        nxt = current + timedelta(hours=1)
        slots.append(f"{current.strftime('%I:%M %p')} - {nxt.strftime('%I:%M %p')}")
        current = nxt
    return slots

# ── QR code generator ─────────────────────────────────────────────────────────
def generate_qr_data(appointment_id, token):
    """Returns the QR payload string and a base64-encoded PNG."""
    import io, base64
    data = f"APT-{appointment_id}-{token}"
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        # Fallback: generate a simple placeholder PNG if qrcode is not installed
        # Install with: pip install qrcode[pil]
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (200, 200), color='white')
            draw = ImageDraw.Draw(img)
            draw.rectangle([10, 10, 190, 190], outline='black', width=3)
            draw.text((20, 90), data[:20], fill='black')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            b64 = base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            b64 = ""
    return data, b64

# ── Socket.IO events ──────────────────────────────────────────────────────────
@socketio.on('join')
def on_join(data):
    """Client joins a room named after their user_id for live notifications."""
    room = str(data.get('user_id', ''))
    if room:
        join_room(room)

def push_status_update(user_id, appointment_id, status, message):
    """Emit a real-time status update to the student's socket room."""
    socketio.emit('appointment_update', {
        'appointment_id': appointment_id,
        'status': status,
        'message': message,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }, room=str(user_id))

# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):   return render_template('errors/404.html'), 404
@app.errorhandler(500)
def server_error(e): return render_template('errors/500.html'), 500
@app.errorhandler(403)
def forbidden(e):   return render_template('errors/403.html'), 403
@app.errorhandler(429)
def rate_limited(e):
    return render_template('errors/429.html'), 429

# ── Blueprints ────────────────────────────────────────────────────────────────
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

# Apply rate limiting to login route
limiter.limit("10 per minute")(auth_bp)

# ── Root route ────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if current_user.is_authenticated:
        role = current_user.role
        if role == 'super_admin':
            return redirect(url_for('super_admin.dashboard'))
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        if role == 'officer':
            return redirect(url_for('officer.dashboard'))
        return redirect(url_for('student.dashboard'))
    return render_template('home.html')

# ── Live notifications API ────────────────────────────────────────────────────
@app.route('/api/notifications/unread-count')
def unread_count():
    from flask_login import current_user
    from models import Notification
    if not current_user.is_authenticated:
        return {'count': 0}
    count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return {'count': count}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
