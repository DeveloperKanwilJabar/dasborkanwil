from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Optional

from app.core.security.validators import ValidationRules as Rules


class BaseForm(FlaskForm):
    username = StringField('NIP', validators=Rules.NIP['validators'])
    password = PasswordField('Password', validators=Rules.PASSWORD['validators'])


class RegisterForm(BaseForm):
    email = StringField('Email', validators=Rules.EMAIL['validators'])
    confirm_password = PasswordField(
        'Konfirmasi Password',
        validators=[
            DataRequired(message='Konfirmasi password wajib diisi.'),
            EqualTo('password', message='Konfirmasi password harus sama.'),
        ],
    )


class LoginForm(BaseForm):
    remember = BooleanField('Ingat saya')


class BaseUserForm(FlaskForm):
    username = StringField('NIP', validators=Rules.NIP['validators'])
    email = StringField('Email', validators=Rules.EMAIL['validators'])
    roles = TextAreaField('Roles')
    permissions = TextAreaField('Permissions')
    active_year = IntegerField('Tahun Aktif', validators=[Optional()])
    scope_type = SelectField('Tipe Scope', validators=[Optional()], choices=[])
    scope_code = SelectField('Kode Scope', validators=[Optional()], choices=[])
    active = BooleanField('Aktif', default=True)


class UserCreateForm(BaseUserForm):
    password = PasswordField('Password', validators=Rules.PASSWORD['validators'])
    confirm_password = PasswordField(
        'Konfirmasi Password',
        validators=[
            DataRequired(message='Konfirmasi password wajib diisi.'),
            EqualTo('password', message='Konfirmasi password harus sama.'),
        ],
    )


class UserUpdateForm(BaseUserForm):
    password = PasswordField('Password Baru', validators=[Optional()] + Rules.PASSWORD['validators'][1:])
    confirm_password = PasswordField('Konfirmasi Password Baru', validators=[Optional()])

    def validate(self, extra_validators=None):
        is_valid = super().validate(extra_validators=extra_validators)
        if not is_valid:
            return False

        password = (self.password.data or '').strip()
        confirm_password = (self.confirm_password.data or '').strip()

        if password or confirm_password:
            if not password:
                self.password.errors.append('Password baru wajib diisi jika ingin mengganti password.')
                return False

            if not confirm_password:
                self.confirm_password.errors.append('Konfirmasi password baru wajib diisi.')
                return False

            if password != confirm_password:
                self.confirm_password.errors.append('Konfirmasi password harus sama.')
                return False

        return True
