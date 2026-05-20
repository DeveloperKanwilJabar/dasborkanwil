from markupsafe import escape

class InputSanitizer:
    @staticmethod
    def clean_text(text):
        """Membersihkan input dari potensi XSS."""
        if not text:
            return text
        # Mengonversi karakter seperti <, >, &, ", ' menjadi HTML entities
        return escape(text.strip())
