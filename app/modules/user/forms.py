from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo
from app.core.security.validators import ValidationRules as Rules

class BaseForm(FlaskForm):
    username = StringField('NIP', validators=Rules.NIP['validators'])
    password = PasswordField('Password', validators=Rules.PASSWORD['validators'])

class RegisterForm(BaseForm):
    email = StringField('Email', validators=Rules.EMAIL['validators'])
    confirm_password = PasswordField('Konfirmasi Password', validators=[
        DataRequired(message="Konfirmasi password wajib diisi."),
        EqualTo('password', message='Password harus sama')
        ])

class LoginForm(BaseForm):
    remember = BooleanField('Ingat saya')

class UserForm(BaseForm):
    email = StringField('Email', validators=Rules.EMAIL['validators'])
    full_name = StringField('Nama Lengkap', validators=[DataRequired(), Length(min=3, max=254)])
