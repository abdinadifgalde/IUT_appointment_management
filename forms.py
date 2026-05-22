from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    SelectField,
    TextAreaField,
    DateField,
    IntegerField,
    BooleanField,
    SelectMultipleField,
    HiddenField
)

from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    ValidationError,
    Optional,
    NumberRange
)

from models import User


# ════════════════════════════════════════════════════════════════
# Registration Form
# ════════════════════════════════════════════════════════════════

class RegistrationForm(FlaskForm):

    name = StringField(
        'Full Name',
        validators=[
            DataRequired(),
            Length(min=2, max=100)
        ]
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=6)
        ]
    )

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password')
        ]
    )

    role = SelectField(
        'Role',
        choices=[
            ('student', 'Student')
        ],
        validators=[DataRequired()]
    )

    submit = SubmitField('Create Account')

    def validate_email(self, email):

        if not email.data.lower().endswith('@iut-dhaka.edu'):
            raise ValidationError(
                'Only @iut-dhaka.edu emails are allowed.'
            )

        existing_user = User.query.filter_by(
            email=email.data
        ).first()

        if existing_user:
            raise ValidationError(
                'This email already exists.'
            )


# ════════════════════════════════════════════════════════════════
# Login Form
# ════════════════════════════════════════════════════════════════

class LoginForm(FlaskForm):

    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        'Password',
        validators=[DataRequired()]
    )

    remember = BooleanField('Remember Me')

    submit = SubmitField('Login')


# ════════════════════════════════════════════════════════════════
# Appointment Booking Form
# ════════════════════════════════════════════════════════════════

class AppointmentForm(FlaskForm):

    student_name = StringField(
        'Full Name',
        validators=[DataRequired()]
    )

    student_id_num = StringField(
        'Student ID',
        validators=[DataRequired()]
    )

    department = StringField(
        'Department',
        validators=[DataRequired()]
    )

    officer = SelectField(
        'Select Officer',
        coerce=int,
        validators=[DataRequired()]
    )

    date = DateField(
        'Appointment Date',
        validators=[DataRequired()]
    )

    time = SelectField(
        'Time Slot',
        choices=[],
        validators=[DataRequired()]
    )

    duration = SelectField(
        'Duration',
        choices=[
            ('15', '15 Minutes'),
            ('30', '30 Minutes'),
            ('45', '45 Minutes'),
            ('60', '1 Hour')
        ],
        default='30'
    )

    meeting_type = SelectField(
        'Meeting Type',
        choices=[
            ('physical', 'Physical Meeting'),
            ('online', 'Online Meeting')
        ],
        default='physical'
    )

    guest_emails = StringField(
        'Guest Emails (comma separated)',
        validators=[Optional()]
    )

    issue = TextAreaField(
        'Appointment Reason',
        validators=[
            DataRequired(),
            Length(min=5, max=1000)
        ]
    )

    submit = SubmitField('Book Appointment')


# ════════════════════════════════════════════════════════════════
# Reschedule Form
# ════════════════════════════════════════════════════════════════

class RescheduleForm(FlaskForm):

    date = DateField(
        'New Appointment Date',
        validators=[DataRequired()]
    )

    time = SelectField(
        'New Time Slot',
        choices=[],
        validators=[DataRequired()]
    )

    reason = TextAreaField(
        'Reason For Rescheduling',
        validators=[
            Optional(),
            Length(max=300)
        ]
    )

    submit = SubmitField('Reschedule Appointment')


# ════════════════════════════════════════════════════════════════
# Officer Form
# ════════════════════════════════════════════════════════════════

class OfficerForm(FlaskForm):

    name = StringField(
        'Officer Name',
        validators=[DataRequired()]
    )

    designation = StringField(
        'Designation',
        validators=[DataRequired()]
    )

    bio = TextAreaField(
        'About Officer',
        validators=[
            Optional(),
            Length(max=500)
        ]
    )

    room = StringField(
        'Office Room',
        validators=[Optional()]
    )

    handles = StringField(
        'Issues Handled',
        validators=[Optional()]
    )

    photo_url = StringField(
        'Photo Filename',
        validators=[Optional()]
    )

    work_start = StringField(
        'Work Start Time',
        validators=[DataRequired()],
        default='08:00'
    )

    work_end = StringField(
        'Work End Time',
        validators=[DataRequired()],
        default='17:00'
    )

    slot_duration = SelectField(
        'Default Slot Duration',
        choices=[
            ('15', '15 Minutes'),
            ('30', '30 Minutes'),
            ('45', '45 Minutes'),
            ('60', '1 Hour')
        ],
        default='30'
    )

    daily_limit = IntegerField(
        'Daily Appointment Limit',
        validators=[
            NumberRange(min=0)
        ],
        default=0
    )

    recurring_off_days = SelectMultipleField(
        'Recurring Off Days',
        choices=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday')
        ],
        default=['4', '5']
    )

    submit = SubmitField('Save Officer')


# ════════════════════════════════════════════════════════════════
# Working Hours Form
# ════════════════════════════════════════════════════════════════

class WorkingHoursForm(FlaskForm):

    weekday = SelectField(
        'Weekday',
        coerce=int,
        choices=[
            (0, 'Monday'),
            (1, 'Tuesday'),
            (2, 'Wednesday'),
            (3, 'Thursday'),
            (4, 'Friday'),
            (5, 'Saturday'),
            (6, 'Sunday')
        ]
    )

    start_time = StringField(
        'Start Time',
        validators=[DataRequired()],
        default='08:00'
    )

    end_time = StringField(
        'End Time',
        validators=[DataRequired()],
        default='17:00'
    )

    submit = SubmitField('Save Working Hours')


# ════════════════════════════════════════════════════════════════
# Profile Form
# ════════════════════════════════════════════════════════════════

class ProfileForm(FlaskForm):

    name = StringField(
        'Full Name',
        validators=[DataRequired()]
    )

    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email()
        ]
    )

    student_id_num = StringField(
        'Student ID',
        validators=[Optional()]
    )

    department = StringField(
        'Department',
        validators=[Optional()]
    )

    current_password = PasswordField(
        'Current Password',
        validators=[Optional()]
    )

    new_password = PasswordField(
        'New Password',
        validators=[
            Optional(),
            Length(min=6)
        ]
    )

    confirm_new_password = PasswordField(
        'Confirm New Password',
        validators=[
            EqualTo(
                'new_password',
                message='Passwords must match.'
            )
        ]
    )

    submit = SubmitField('Update Profile')

    def validate_email(self, email):

        if not email.data.lower().endswith('@iut-dhaka.edu'):
            raise ValidationError(
                'Only IUT emails are allowed.'
            )


# ════════════════════════════════════════════════════════════════
# Forgot Password Form
# ════════════════════════════════════════════════════════════════

class ForgotPasswordForm(FlaskForm):

    email = StringField(
        'Email Address',
        validators=[
            DataRequired(),
            Email()
        ]
    )

    submit = SubmitField('Send Reset Link')


# ════════════════════════════════════════════════════════════════
# Reset Password Form
# ════════════════════════════════════════════════════════════════

class ResetPasswordForm(FlaskForm):

    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(min=6)
        ]
    )

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('new_password')
        ]
    )

    submit = SubmitField('Reset Password')


# ════════════════════════════════════════════════════════════════
# Officer Unavailability Form
# ════════════════════════════════════════════════════════════════

class UnavailabilityForm(FlaskForm):

    start_date = DateField(
        'Unavailable From',
        validators=[DataRequired()]
    )

    end_date = DateField(
        'Unavailable Until',
        validators=[DataRequired()]
    )

    reason = StringField(
        'Reason',
        validators=[
            DataRequired(),
            Length(max=255)
        ]
    )

    submit = SubmitField('Save Unavailability')


# ════════════════════════════════════════════════════════════════
# Reject Appointment Form
# ════════════════════════════════════════════════════════════════

class RejectNoteForm(FlaskForm):

    rejection_note = TextAreaField(
        'Reason For Rejection',
        validators=[
            DataRequired(),
            Length(max=500)
        ]
    )

    submit = SubmitField('Reject Appointment')


# ════════════════════════════════════════════════════════════════
# Bulk Appointment Action Form
# ════════════════════════════════════════════════════════════════

class BulkActionForm(FlaskForm):

    action = SelectField(
        'Action',
        choices=[
            ('Approved', 'Approve Selected'),
            ('Rejected', 'Reject Selected'),
            ('Completed', 'Mark As Completed'),
            ('Cancelled', 'Cancel Selected')
        ]
    )

    submit = SubmitField('Apply Action')
