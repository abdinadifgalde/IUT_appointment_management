from flask import (
    Blueprint,
    jsonify,
    request
)

from flask_login import (
    login_required,
    current_user
)

from datetime import (
    datetime,
    timedelta
)

from models import (
    db,
    User,
    Appointment,
    OfficerAvailability
)

api_bp = Blueprint(
    'api',
    __name__
)

# ─────────────────────────────────────────────────────────────
# GENERATE DYNAMIC SLOTS
# ─────────────────────────────────────────────────────────────

def generate_slots(
    start_time,
    end_time,
    duration,
    booked_slots
):

    slots = []

    current = datetime.combine(
        datetime.today(),
        start_time
    )

    end = datetime.combine(
        datetime.today(),
        end_time
    )

    while current + timedelta(minutes=duration) <= end:

        slot_end = current + timedelta(minutes=duration)

        overlap = False

        for booked_start, booked_end in booked_slots:

            booked_start_dt = datetime.combine(
                datetime.today(),
                booked_start
            )

            booked_end_dt = datetime.combine(
                datetime.today(),
                booked_end
            )

            if current < booked_end_dt and slot_end > booked_start_dt:
                overlap = True
                break

        if not overlap:

            slots.append({
                "start": current.strftime("%I:%M %p"),
                "end": slot_end.strftime("%I:%M %p"),
                "duration": duration
            })

        current += timedelta(minutes=duration)

    return slots

# ─────────────────────────────────────────────────────────────
# AVAILABLE SLOTS API
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/available-slots',
    methods=['GET']
)
@login_required
def available_slots():

    officer_id = request.args.get(
        'officer_id',
        type=int
    )

    selected_date = request.args.get(
        'date'
    )

    duration = request.args.get(
        'duration',
        default=15,
        type=int
    )

    if not officer_id or not selected_date:

        return jsonify({
            'success': False,
            'message': 'Missing data'
        }), 400

    try:

        selected_date = datetime.strptime(
            selected_date,
            '%Y-%m-%d'
        ).date()

    except ValueError:

        return jsonify({
            'success': False,
            'message': 'Invalid date'
        }), 400

    # Prevent past booking

    if selected_date < datetime.today().date():

        return jsonify({
            'success': False,
            'message': 'Past dates not allowed'
        }), 400

    weekday = selected_date.weekday()

    availability = OfficerAvailability.query.filter_by(
        officer_id=officer_id,
        weekday=weekday,
        is_available=True
    ).first()

    if not availability:

        return jsonify({
            'success': True,
            'slots': []
        })

    # Get booked appointments

    appointments = Appointment.query.filter_by(
        officer_id=officer_id,
        appointment_date=selected_date
    ).filter(
        Appointment.appointment_status != 'Rejected'
    ).all()

    booked_slots = []

    for appointment in appointments:

        booked_slots.append((
            appointment.start_time,
            appointment.end_time
        ))

    slots = generate_slots(
        availability.start_time,
        availability.end_time,
        duration,
        booked_slots
    )

    return jsonify({
        'success': True,
        'slots': slots
    })

# ─────────────────────────────────────────────────────────────
# CHECK SLOT CONFLICT
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/check-conflict',
    methods=['POST']
)
@login_required
def check_conflict():

    data = request.get_json()

    officer_id = data.get('officer_id')

    appointment_date = data.get('date')

    start_time = data.get('start_time')

    end_time = data.get('end_time')

    existing = Appointment.query.filter(
        Appointment.officer_id == officer_id,
        Appointment.appointment_date == appointment_date,
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
        Appointment.appointment_status != 'Rejected'
    ).first()

    return jsonify({
        'conflict': existing is not None
    })

# ─────────────────────────────────────────────────────────────
# OFFICER CALENDAR AVAILABILITY
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/calendar-availability/<int:officer_id>',
    methods=['GET']
)
@login_required
def calendar_availability(officer_id):

    availability = OfficerAvailability.query.filter_by(
        officer_id=officer_id
    ).all()

    days = []

    for item in availability:

        days.append({
            'weekday': item.weekday,
            'start_time': item.start_time.strftime('%H:%M'),
            'end_time': item.end_time.strftime('%H:%M')
        })

    return jsonify({
        'success': True,
        'availability': days
    })

# ─────────────────────────────────────────────────────────────
# STUDENT BOOKINGS API
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/my-bookings',
    methods=['GET']
)
@login_required
def my_bookings():

    appointments = Appointment.query.filter_by(
        student_id=current_user.id
    ).order_by(
        Appointment.appointment_date.desc()
    ).all()

    data = []

    for appointment in appointments:

        data.append({

            'id': appointment.id,

            'title': appointment.title,

            'officer': appointment.officer.name,

            'date': appointment.appointment_date.strftime('%Y-%m-%d'),

            'start_time': appointment.start_time.strftime('%I:%M %p'),

            'end_time': appointment.end_time.strftime('%I:%M %p'),

            'duration': appointment.duration,

            'status': appointment.appointment_status,

            'location': appointment.location
        })

    return jsonify({
        'success': True,
        'appointments': data
    })

# ─────────────────────────────────────────────────────────────
# OFFICER QUICK STATUS UPDATE
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/update-status/<int:appointment_id>',
    methods=['POST']
)
@login_required
def update_status(appointment_id):

    if current_user.role != 'officer':

        return jsonify({
            'success': False
        }), 403

    appointment = Appointment.query.get_or_404(
        appointment_id
    )

    status = request.json.get('status')

    valid_statuses = [
        'Pending',
        'Confirmed',
        'Rejected',
        'Completed',
        'No-show'
    ]

    if status not in valid_statuses:

        return jsonify({
            'success': False,
            'message': 'Invalid status'
        }), 400

    appointment.appointment_status = status

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Status updated successfully'
    })

# ─────────────────────────────────────────────────────────────
# RESCHEDULE APPOINTMENT
# ─────────────────────────────────────────────────────────────

@api_bp.route(
    '/reschedule/<int:appointment_id>',
    methods=['POST']
)
@login_required
def reschedule_appointment(appointment_id):

    if current_user.role != 'officer':

        return jsonify({
            'success': False
        }), 403

    appointment = Appointment.query.get_or_404(
        appointment_id
    )

    data = request.get_json()

    new_date = data.get('date')

    new_start = data.get('start_time')

    new_end = data.get('end_time')

    appointment.previous_schedule = (
        f"{appointment.appointment_date} "
        f"{appointment.start_time}"
    )

    appointment.appointment_date = datetime.strptime(
        new_date,
        '%Y-%m-%d'
    ).date()

    appointment.start_time = datetime.strptime(
        new_start,
        '%H:%M'
    ).time()

    appointment.end_time = datetime.strptime(
        new_end,
        '%H:%M'
    ).time()

    appointment.appointment_status = 'Confirmed'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Appointment rescheduled'
    })