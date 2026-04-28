from wtforms.validators import DataRequired, Length, Regexp, Email

class ValidationRules:
    NIP = {
        'validators': [
            DataRequired(message="NIP wajib diisi."),
            Length(min=18, max=18, message="NIP harus 18 karakter."),
            Regexp(r'^\d{18}', message="NIP tidak valid.")
        ],
        'regex': r'^\d{18}'
    }

    PASSWORD = {
        'validators': [
            DataRequired(message="Password wajib diisi."),
            Length(min=8, message="Password minimal 8 karakter."),
            Regexp(
                r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*{}])',
                message="Password harus mengandung huruf besar, huruf kecil, angka, dan karakter khusus !@#$%^&*{}."
            )
        ],
        'regex': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*{}])'
    }
    # (?=.*[a-z]) : Memastikan ada huruf kecil
    # (?=.*[A-Z]) : Memastikan ada huruf besar
    # (?=.*[0-9]) : Memastikan ada angka
    # (?=.*[!@#$%^&*{}]) : Memastikan ada karakter khusus

    EMAIL = {
        'validators': [
            DataRequired(message="Email wajib diisi."),
            Email(message="Format email tidak valid.")
        ],
        'regex': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    }
