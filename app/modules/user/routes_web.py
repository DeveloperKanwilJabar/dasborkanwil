from flask import (
    Blueprint, abort, current_app, flash,
    jsonify, redirect, request, render_template, url_for,
    )
from flask_login import current_user, login_user, login_required, logout_user
from app.core.extensions import db
from app.core.utils import json_response
from .forms import LoginForm, RegisterForm
from .services import UserService

user_bp = Blueprint(
    'user',
    __name__,
    template_folder='pages',
)

@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        # 1. Validasi Form
        current_app.logger.info("Register form validation passed.")

        # 2. Menambahkan user baru. Proteksi ganda sudah ada di Service, jadi cukup panggil saja.
        try:
            service = UserService()
            service.register(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data,
                is_seeding=False, # Pendaftaran selain seeding
            )
            return json_response(True, "Registrasi berhasil! Silahkan login.", {"redirect_url": url_for('user.dashboard')})

        except ValueError as e:
            # Menangkap pesan error logic dari Service (misal: NIP tidak ada, email duplikat, dll) dan mengembalikannya ke frontend
            # untuk ditampilkan via Toastify. Status 400 untuk error yang berasal dari validasi bisnis.
            return json_response(False, str(e), status=400)

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Register Error: {str(e)}")
            return json_response(False, "Terjadi kesalahan saat menyimpan data.", status=500)


    # 3. Handle Error Validasi Form (WTF-Forms)
    if form.errors:
        current_app.logger.warning(f"Register form validation failed: {form.errors}")
        # Mengubah dictionary errors menjadi pesan string tunggal untuk Toastify
        error_msgs = [f"{', '.join(msgs)}" for field, msgs in form.errors.items()]
        return json_response(False, error_msgs[0] if error_msgs else "Validasi gagal", status=422)

    return render_template('pages/auth/register.html', form=form)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # 1. Cek jika user sudah login
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))

    if form.validate_on_submit():
        # 2. Proses Otentikasi
        try:
            service = UserService()
            user = service.authenticate(
                username=form.username.data,
                password=form.password.data
            )

            if not user:
                return json_response(False, "NIP atau Password salah.", status=401)

            # 3. Login sukses
            login_user(user, remember=form.remember.data)
            current_app.logger.info(f"User logged in: {user.username}")

            return json_response(True, "Login berhasil! Mengarahkan...", {
                "redirect_url": url_for('user.dashboard')
            })

        except ValueError as e:
            return json_response(False, str(e), status=400)

        except Exception as e:
            current_app.logger.error(f"Login System Error: {str(e)}")
            return json_response(False, "Terjadi kesalahan sistem saat login.", status=500)

    # 4. Handle Error Validasi Form (WTF-Forms)
    if form.errors:
        current_app.logger.warning(f"Login form validation failed: {form.errors}")
        error_msgs = [f"{', '.join(msgs)}" for field, msgs in form.errors.items()]
        return json_response(False, error_msgs[0] if error_msgs else "Validasi gagal", status=422)

    return render_template('pages/auth/login.html', form=form)

@user_bp.route('/logout')
@login_required
def logout():
    current_app.logger.info("User logged out: %s", current_user.username)
    logout_user()
    flash('Anda telah keluar dari aplikasi.', 'info')
    return redirect(url_for('user.login'))

@user_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.is_authenticated:
        current_app.logger.warning("Unauthorized access attempt to dashboard.")
        return redirect(url_for('user.login'))

    return render_template('pages/user/dashboard.html', user=current_user)
