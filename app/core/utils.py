"""Utilitas kecil lintas aplikasi.

Modul ini sengaja berisi helper yang benar-benar generik dan aman dipakai dari
route, service, maupun middleware. Dua helper utama di sini dipakai sangat
sering:
- `now_utc()` untuk timestamp konsisten lintas domain,
- `json_response()` untuk envelope response API yang seragam.
"""

import pendulum
from flask import jsonify


def now_utc():
    """Kembalikan timestamp saat ini dalam zona waktu UTC.

    Helper ini dipakai ketika aplikasi perlu mencatat waktu yang netral dari
    timezone client, misalnya untuk audit trail, last login, atau event domain.

    Returns:
        pendulum.DateTime: Objek datetime timezone-aware dengan timezone UTC.

    Example:
        >>> current_time = now_utc()
        >>> current_time.timezone_name
        'UTC'
    """
    return pendulum.now('UTC')


def json_response(success, message, data=None, status=200):
    """Bangun response JSON dengan envelope standar aplikasi.

    Struktur response yang konsisten memudahkan frontend, API consumer, dan
    dokumentasi Flasgger karena semua endpoint mengembalikan bentuk dasar yang
    sama: `success`, `message`, dan `data`.

    Args:
        success (bool): Penanda apakah operasi berhasil atau gagal.
        message (str): Ringkasan hasil operasi yang aman ditampilkan ke user.
        data (Any, optional): Payload utama response, bisa `dict`, `list`, atau
            `None`.
        status (int, optional): HTTP status code yang akan dikirim. Default 200.

    Returns:
        tuple[flask.wrappers.Response, int]: Tuple response Flask hasil
        `jsonify()` dan HTTP status code.

    Example:
        >>> response, status_code = json_response(
        ...     True,
        ...     'Form berhasil dibuat.',
        ...     data={'uuid': 'form-123'},
        ...     status=201,
        ... )
        >>> status_code
        201
    """
    return jsonify({
        "success": success,
        "message": message,
        "data": data,
    }), status
