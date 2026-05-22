"""
Officer blueprint — for users with role='officer'.
Officers can: view their appointments, approve/reject, scan QR for check-in,
set unavailability, mark as completed, and use the Cal.com-inspired detail page.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import (db, Appointment, Officer, Notification, User,
                    OfficerUnavailability, AuditLog,
                    AppointmentHistory, AppointmentGuest)
from datetime import datetime, date, timezone
import json

officer_bp = Blueprint('officer', __name__, url_prefix='/officer')

def officer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('officer', 'admin', 'super_admin'):
            flash('Access denied.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def get_officer_record():
    return Officer.query.filter_by(email=current_user.email).first()

def _log_history(apt_id, action, old_val=None, new_val=None, note=None):
    db.session.add(AppointmentHistory(
        appointment_id=apt_id,
        action=action,
        old_value=str(old_val) if old_val is not None else None,
        new_value=str(new_val) if new_val is not None else None,
        changed_by=current_user.id,
        note=note,
    ))

def _notify(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))

# ── Dashboard ──────────────────────────────────────────────────────────────────
@officer_bp.route('/')
@login_required
@officer_required
def dashboard():
    officer = get_officer_record()
    if not officer:
        flash('No officer profile linked to your account. Contact an administrator.', 'warning')
        return render_template('officer/dashboard.html', officer=None,
                               today_apts=[], pending=[], stats={})

    today = datetime.now(timezone.utc).date()
    today_apts = Appointment.query.filter_by(officer_id=officer.id, date=today)\
        .order_by(Appointment.time).all()
    pending = Appointment.query.filter_by(officer_id=officer.id, status='Pending')\
        .order_by(Appointment.date, Appointment.time).all()

    stats = {
        'total':     Appointment.query.filter_by(officer_id=officer.id).count(),
        'pending':   Appointment.query.filter_by(officer_id=officer.id, status='Pending').count(),
        'approved':  Appointment.query.filter_by(officer_id=officer.id, status='Approved').count(),
        'completed': Appointment.query.filter_by(officer_id=officer.id, status='Completed').count(),
        'rejected':  Appointment.query.filter_by(officer_id=officer.id, status='Rejected').count(),
        'today':     len(today_apts),
    }
    return render_template('officer/dashboard.html', officer=officer,
                           today_apts=today_apts, pending=pending,
                           stats=stats, today=today)

# ── Appointment detail page ────────────────────────────────────────────────────
@officer_bp.route('/appointment/<int:apt_id>')
@login_required
@officer_required
def appointment_detail(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        flash('Not authorized.', 'danger')
        return redirect(url_for('officer.dashboard'))
    history = AppointmentHistory.query.filter_by(appointment_id=apt_id)\
        .order_by(AppointmentHistory.timestamp.desc()).all()
    guests = AppointmentGuest.query.filter_by(appointment_id=apt_id).all()
    return render_template('officer/appointment_details.html',
                           apt=apt, officer=officer,
                           history=history, guests=guests)

# ── Approve (legacy GET + new AJAX POST) ──────────────────────────────────────
@officer_bp.route('/approve/<int:apt_id>', methods=['GET', 'POST'])
@login_required
@officer_required
def approve(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        flash('Not authorized.', 'danger')
        return redirect(url_for('officer.dashboard'))

    old_status = apt.status
    apt.status = 'Approved'
    msg = (f"Your appointment with {apt.officer.name} on "
           f"{apt.date.strftime('%d %b %Y')} at {apt.time} has been Approved.")
    _notify(apt.user_id, msg)
    _log_history(apt.id, 'status_change', old_status, 'Approved')
    db.session.add(AuditLog(admin_id=current_user.id, action='approve',
                            detail=f"#{apt.id} {apt.student_name} → Approved"))
    db.session.commit()

    try:
        from utils import send_email, appointment_status_email
        student = db.session.get(User, apt.user_id)
        send_email('Appointment Approved — IUT', [student.email],
                   appointment_status_email(apt, 'Approved'))
    except Exception:
        pass

    if request.is_json:
        return jsonify({'success': True, 'status': 'Approved'})
    flash('Appointment approved.', 'success')
    return redirect(request.referrer or url_for('officer.dashboard'))

# ── Reject (legacy POST + AJAX) ────────────────────────────────────────────────
@officer_bp.route('/reject/<int:apt_id>', methods=['POST'])
@login_required
@officer_required
def reject(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        flash('Not authorized.', 'danger')
        return redirect(url_for('officer.dashboard'))

    data = request.get_json(silent=True) or {}
    note = data.get('note') or request.form.get('note', '')
    note = note.strip()

    old_status = apt.status
    apt.status = 'Rejected'
    apt.rejection_note = note
    msg = (f"Your appointment with {apt.officer.name} on "
           f"{apt.date.strftime('%d %b %Y')} was Rejected."
           f"{(' Reason: ' + note) if note else ''}")
    _notify(apt.user_id, msg)
    _log_history(apt.id, 'status_change', old_status, 'Rejected', note=note)
    db.session.add(AuditLog(admin_id=current_user.id, action='reject',
                            detail=f"#{apt.id} {apt.student_name} → Rejected: {note}"))
    db.session.commit()

    try:
        from utils import send_email, rejection_email
        student = db.session.get(User, apt.user_id)
        send_email('Appointment Rejected — IUT', [student.email],
                   rejection_email(apt, student, note))
    except Exception:
        pass

    if request.is_json:
        return jsonify({'success': True, 'status': 'Rejected'})
    flash('Appointment rejected.', 'info')
    return redirect(request.referrer or url_for('officer.dashboard'))

# ── Reschedule ─────────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/reschedule', methods=['POST'])
@login_required
@officer_required
def api_reschedule(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json(silent=True) or {}
    new_date_str = data.get('date', '').strip()
    new_time     = data.get('time', '').strip()
    new_duration = data.get('duration', apt.duration)

    if not new_date_str or not new_time:
        return jsonify({'success': False, 'error': 'Date and time required'}), 400

    try:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date format'}), 400

    # Save previous schedule as JSON
    prev = json.dumps({
        'date': str(apt.date), 'time': apt.time,
        'duration': apt.duration, 'rescheduled_at': datetime.now(timezone.utc).isoformat()
    })
    apt.previous_schedule = prev
    old_summary = f"{apt.date} {apt.time}"
    apt.date     = new_date
    apt.day      = new_date.strftime('%A')
    apt.time     = new_time
    apt.duration = int(new_duration)
    apt.status   = 'Approved'

    _notify(apt.user_id,
            f"Your appointment with {apt.officer.name} has been rescheduled to "
            f"{new_date.strftime('%d %b %Y')} at {new_time}.")
    _log_history(apt.id, 'rescheduled', old_summary, f"{new_date} {new_time}")
    db.session.commit()
    return jsonify({'success': True, 'new_date': new_date_str, 'new_time': new_time})

# ── Request reschedule from student ───────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/request-reschedule', methods=['POST'])
@login_required
@officer_required
def api_request_reschedule(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json(silent=True) or {}
    message       = data.get('message', '').strip()
    proposed_date = data.get('proposed_date', '').strip()
    proposed_time = data.get('proposed_time', '').strip()

    apt.reschedule_requested = True
    apt.reschedule_message   = message
    if proposed_date:
        try:
            apt.reschedule_proposed_date = datetime.strptime(proposed_date, '%Y-%m-%d').date()
        except ValueError:
            pass
    apt.reschedule_proposed_time = proposed_time or None

    full_msg = f"Your officer has requested a reschedule for your appointment on {apt.date.strftime('%d %b %Y')}."
    if message:
        full_msg += f" Message: {message}"
    if proposed_date:
        full_msg += f" Proposed new time: {proposed_date} {proposed_time}".strip()
    _notify(apt.user_id, full_msg)
    _log_history(apt.id, 'reschedule_requested', note=message)
    db.session.commit()
    return jsonify({'success': True})

# ── Update location ────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/update-location', methods=['POST'])
@login_required
@officer_required
def api_update_location(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json(silent=True) or {}
    location = data.get('location', '').strip()
    old_loc  = apt.location
    apt.location = location
    _log_history(apt.id, 'location_updated', old_loc, location)
    db.session.commit()
    return jsonify({'success': True, 'location': location})

# ── Add guest ──────────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/add-guest', methods=['POST'])
@login_required
@officer_required
def api_add_guest(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'error': 'Valid email required'}), 400

    exists = AppointmentGuest.query.filter_by(
        appointment_id=apt_id, guest_email=email).first()
    if exists:
        return jsonify({'success': False, 'error': 'Guest already added'}), 409

    guest = AppointmentGuest(appointment_id=apt_id, guest_email=email)
    db.session.add(guest)
    _log_history(apt.id, 'guest_added', new_val=email)
    db.session.commit()
    return jsonify({'success': True, 'guest_id': guest.id, 'email': email})

# ── Remove guest ───────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/remove-guest/<int:guest_id>', methods=['DELETE'])
@login_required
@officer_required
def api_remove_guest(apt_id, guest_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    guest = db.session.get(AppointmentGuest, guest_id)
    if not guest or guest.appointment_id != apt_id:
        return jsonify({'success': False, 'error': 'Guest not found'}), 404

    _log_history(apt.id, 'guest_removed', old_val=guest.guest_email)
    db.session.delete(guest)
    db.session.commit()
    return jsonify({'success': True})

# ── Add recording link ─────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/add-recording', methods=['POST'])
@login_required
@officer_required
def api_add_recording(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json(silent=True) or {}
    link = data.get('link', '').strip()
    apt.recording_link = link
    _log_history(apt.id, 'recording_added', new_val=link)
    db.session.commit()
    return jsonify({'success': True, 'link': link})

# ── Save session notes ─────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/add-notes', methods=['POST'])
@login_required
@officer_required
def api_add_notes(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = request.get_json(silent=True) or {}
    notes = data.get('notes', '').strip()
    apt.session_notes = notes
    _log_history(apt.id, 'notes_updated')
    db.session.commit()
    return jsonify({'success': True})

# ── Mark completed ─────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/mark-complete', methods=['POST'])
@login_required
@officer_required
def api_mark_complete(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    old_status = apt.status
    apt.status       = 'Completed'
    apt.completed_at = datetime.now(timezone.utc)
    _notify(apt.user_id,
            f"Your appointment with {apt.officer.name} on "
            f"{apt.date.strftime('%d %b %Y')} has been marked Completed.")
    _log_history(apt.id, 'status_change', old_status, 'Completed')
    db.session.commit()
    return jsonify({'success': True, 'status': 'Completed'})

# ── Mark no-show ───────────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/mark-no-show', methods=['POST'])
@login_required
@officer_required
def api_mark_no_show(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    old_status = apt.status
    apt.status  = 'No-show'
    apt.no_show = True
    _notify(apt.user_id,
            f"Your appointment with {apt.officer.name} on "
            f"{apt.date.strftime('%d %b %Y')} was marked as No-show.")
    _log_history(apt.id, 'status_change', old_status, 'No-show')
    db.session.commit()
    return jsonify({'success': True, 'status': 'No-show'})

# ── Get history (AJAX) ─────────────────────────────────────────────────────────
@officer_bp.route('/api/appointment/<int:apt_id>/get-history')
@login_required
@officer_required
def api_get_history(apt_id):
    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()
    if not apt or (officer and apt.officer_id != officer.id):
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    events = AppointmentHistory.query.filter_by(appointment_id=apt_id)\
        .order_by(AppointmentHistory.timestamp.desc()).all()
    return jsonify({'success': True, 'history': [
        {
            'action':    e.action,
            'old_value': e.old_value,
            'new_value': e.new_value,
            'note':      e.note,
            'actor':     e.actor.name if e.actor else 'System',
            'timestamp': e.timestamp.strftime('%d %b %Y %H:%M'),
        } for e in events
    ]})

# ── QR scan / check-in ────────────────────────────────────────────────────────
@officer_bp.route('/scan', methods=['GET'])
@login_required
@officer_required
def scan_page():
    return render_template('officer/scan_qr.html')

@officer_bp.route('/checkin', methods=['POST'])
@login_required
@officer_required
def checkin():
    qr_data = request.form.get('qr_data', '').strip()
    if not qr_data.startswith('APT-'):
        return jsonify({'success': False, 'error': 'Invalid QR format'}), 400
    parts = qr_data.split('-')
    if len(parts) != 3:
        return jsonify({'success': False, 'error': 'Malformed QR data'}), 400
    try:
        apt_id = int(parts[1])
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid appointment ID'}), 400

    apt = db.session.get(Appointment, apt_id)
    officer = get_officer_record()

    if not apt:
        return jsonify({'success': False, 'error': 'Appointment not found'}), 404
    if officer and apt.officer_id != officer.id:
        return jsonify({'success': False, 'error': 'This appointment belongs to another officer'}), 403
    if apt.qr_code_data != qr_data:
        return jsonify({'success': False, 'error': 'QR token mismatch — possible forgery'}), 403
    if apt.status == 'Completed':
        return jsonify({'success': False, 'error': 'Appointment already completed'}), 400
    if apt.status not in ('Approved', 'Pending'):
        return jsonify({'success': False, 'error': f'Cannot check in — status is {apt.status}'}), 400

    old_status = apt.status
    apt.status       = 'Completed'
    apt.completed_at = datetime.now(timezone.utc)
    msg = f"Check-in verified! Your appointment with {apt.officer.name} has been marked Completed."
    _notify(apt.user_id, msg)
    _log_history(apt.id, 'qr_checkin', old_status, 'Completed',
                 note=f"Checked in by {current_user.name}")
    db.session.add(AuditLog(admin_id=current_user.id, action='qr_checkin',
                            detail=f"#{apt.id} {apt.student_name} checked in by {current_user.name}"))
    db.session.commit()
    return jsonify({'success': True,
                    'message': f'Check-in confirmed for {apt.student_name}',
                    'appointment': {
                        'id': apt.id, 'student': apt.student_name,
                        'date': str(apt.date), 'time': apt.time, 'issue': apt.issue
                    }})

# ── My schedule ────────────────────────────────────────────────────────────────
@officer_bp.route('/schedule')
@login_required
@officer_required
def schedule():
    officer = get_officer_record()
    if not officer:
        flash('No officer profile found.', 'warning')
        return redirect(url_for('officer.dashboard'))
    apts = Appointment.query.filter_by(officer_id=officer.id)\
        .filter(Appointment.date >= datetime.now(timezone.utc).date())\
        .order_by(Appointment.date, Appointment.time).all()
    return render_template('officer/schedule.html', officer=officer, appointments=apts)
