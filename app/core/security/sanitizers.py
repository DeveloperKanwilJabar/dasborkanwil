"""Sanitizer input sederhana untuk permukaan web/API.

Modul ini berisi helper defensif yang dipakai ketika aplikasi perlu menerima
teks bebas dari user lalu merendernya kembali pada HTML.
"""

from markupsafe import escape


class InputSanitizer:
    """Kumpulan helper sanitasi nilai input.

    Example:
        >>> InputSanitizer.clean_text('<script>alert(1)</script>')
        Markup('&lt;script&gt;alert(1)&lt;/script&gt;')
    """

    @staticmethod
    def clean_text(text):
        """Bersihkan teks dasar dari whitespace berlebih dan karakter berbahaya.

        Sanitasi ini bukan pengganti validasi domain, tetapi lapisan pertama
        untuk mencegah injeksi HTML/XSS sederhana pada field teks bebas.

        Args:
            text (str | None): Nilai mentah dari input user.

        Returns:
            markupsafe.Markup | str | None: Nilai yang sudah di-trim dan di-
            escape. Jika input kosong/None, nilai asal dikembalikan.

        Example:
            >>> InputSanitizer.clean_text('  <b>Halo</b>  ')
            Markup('&lt;b&gt;Halo&lt;/b&gt;')
        """
        if not text:
            return text
        return escape(text.strip())
