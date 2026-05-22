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

# ═════════════════════════════════════════════════════════════════════
# Authentication Forms
# ═════════════════════════════════════════════════════════════════════

class RegistrationForm(FlaskForm):
    name = StringField(
        'Full Name',
        validators=[DataRequired(), Length(min=2, max=100)]
    )

    email = StringField(
        'IUT Email',
        validators=[DataRequired(), Email()]
    )

    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6)]
    )

    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match.')
        ]
    )

    role = SelectField(
        'Role',
        choices=[('student', 'Student')],
    submit = SubmitField('Reset Password')
