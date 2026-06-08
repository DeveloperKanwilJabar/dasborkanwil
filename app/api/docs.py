"""Utilitas dokumentasi API untuk Flasgger/Swagger.

Modul ini mengemas pola dokumentasi yang berulang agar endpoint tetap ringkas,
konsisten, dan mudah direview. Fokus utamanya:
- mendefinisikan template Swagger global aplikasi,
- membuat schema envelope response standar `json_response()`,
- menyediakan helper parameter/path/query/body yang reusable,
- menambahkan contoh request/response agar reviewer lebih cepat memahami kontrak API.
"""

from copy import deepcopy


DEFAULT_ERROR_SCHEMA = {
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean', 'example': False},
        'message': {'type': 'string', 'example': 'Terjadi kesalahan validasi.'},
        'data': {
            'type': 'object',
            'properties': {
                'error_type': {'type': 'string', 'example': 'validation_error'},
            },
        },
    },
}


def swagger_template():
    """Bangun metadata Swagger global aplikasi.

    Returns:
        dict: Template Swagger 2.0 yang dipakai Flasgger untuk UI docs,
        metadata aplikasi, serta definisi skema auth dasar.

    Example:
        >>> template = swagger_template()
        >>> template['info']['title']
        'Dasborkanwil API Docs'
    """
    return {
        'swagger': '2.0',
        'info': {
            'title': 'Dasborkanwil API Docs',
            'description': (
                'Dokumentasi API aplikasi Dasborkanwil. '
                'Setiap endpoint dilengkapi ringkasan fungsi, parameter, '
                'bentuk input/output, dan contoh payload untuk memudahkan review.'
            ),
            'version': '1.0.0',
        },
        'basePath': '/',
        'schemes': ['http', 'https'],
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Format: Bearer <JWT access token>.',
            }
        },
    }


def swagger_config():
    """Bangun konfigurasi endpoint Flasgger.

    Returns:
        dict: Konfigurasi UI Swagger pada path `/api/docs/` dan spesifikasi
        JSON pada path `/api/docs/openapi.json`.

    Example:
        >>> config = swagger_config()
        >>> config['specs_route']
        '/api/docs/'
    """
    return {
        'headers': [],
        'specs': [
            {
                'endpoint': 'openapi',
                'route': '/api/docs/openapi.json',
                'rule_filter': lambda rule: rule.rule.startswith('/api/'),
                'model_filter': lambda tag: True,
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'specs_route': '/api/docs/',
    }


def envelope_schema(data_schema=None, message_example='OK', success_example=True):
    """Buat schema response standar pembungkus `json_response()`.

    Args:
        data_schema (dict | None): Schema isi field `data`.
        message_example (str): Contoh pesan sukses/gagal.
        success_example (bool): Contoh flag sukses.

    Returns:
        dict: Schema object dengan properti `success`, `message`, dan `data`.

    Example:
        >>> schema = envelope_schema({'type': 'object'})
        >>> sorted(schema['properties'].keys())
        ['data', 'message', 'success']
    """
    return {
        'type': 'object',
        'properties': {
            'success': {'type': 'boolean', 'example': success_example},
            'message': {'type': 'string', 'example': message_example},
            'data': data_schema or {'type': 'object', 'nullable': True},
        },
    }


def body_parameter(name, schema, required=True, description='Payload JSON request body.'):
    """Buat dokumentasi parameter body JSON."""
    return {
        'name': name,
        'in': 'body',
        'required': required,
        'description': description,
        'schema': schema,
    }


def path_parameter(name, value_type='integer', description='Parameter path.', example=None, required=True):
    """Buat dokumentasi parameter path pada URL."""
    parameter = {
        'name': name,
        'in': 'path',
        'required': required,
        'type': value_type,
        'description': description,
    }
    if example is not None:
        parameter['example'] = example
    return parameter


def query_parameter(name, value_type='string', description='Parameter query.', required=False, example=None, default=None):
    """Buat dokumentasi parameter query string."""
    parameter = {
        'name': name,
        'in': 'query',
        'required': required,
        'type': value_type,
        'description': description,
    }
    if example is not None:
        parameter['example'] = example
    if default is not None:
        parameter['default'] = default
    return parameter


def security_bearer(enabled=True):
    """Deklarasi security bearer untuk endpoint yang butuh JWT."""
    return [{'Bearer': []}] if enabled else []


def standard_responses(success_schema, success_description, success_status=200, *, include_auth=False):
    """Buat blok respons standar endpoint.

    Args:
        success_schema (dict): Schema envelope sukses.
        success_description (str): Deskripsi respons sukses.
        success_status (int): HTTP status sukses.
        include_auth (bool): Jika True, tambahkan contoh 401 auth.

    Returns:
        dict: Mapping status code ke schema respons.
    """
    responses = {
        success_status: {
            'description': success_description,
            'schema': success_schema,
        },
        400: {
            'description': 'Validasi gagal.',
            'schema': deepcopy(DEFAULT_ERROR_SCHEMA),
        },
        403: {
            'description': 'Akses ditolak.',
            'schema': deepcopy(DEFAULT_ERROR_SCHEMA),
        },
        500: {
            'description': 'Kesalahan server internal.',
            'schema': envelope_schema(
                {'type': 'object', 'nullable': True},
                message_example='Terjadi kesalahan server.',
                success_example=False,
            ),
        },
    }
    if include_auth:
        responses[401] = {
            'description': 'Token tidak valid atau belum dikirim.',
            'schema': envelope_schema(
                {'type': 'object', 'nullable': True},
                message_example='Missing Authorization Header',
                success_example=False,
            ),
        }
    return responses


def build_spec(*, tag, summary, description, parameters=None, responses=None, security=None):
    """Bangun dokumen Swagger endpoint dalam bentuk dict.

    Args:
        tag (str): Kelompok endpoint di UI Swagger.
        summary (str): Ringkasan singkat endpoint.
        description (str): Penjelasan penggunaan, input-output, dan contoh kasus.
        parameters (list[dict] | None): Daftar parameter Swagger.
        responses (dict | None): Mapping HTTP status ke schema respons.
        security (list | None): Deklarasi security Swagger.

    Returns:
        dict: Payload yang bisa dipakai oleh `@swag_from(...)`.
    """
    spec = {
        'tags': [tag],
        'summary': summary,
        'description': description,
        'parameters': parameters or [],
        'responses': responses or {},
    }
    if security:
        spec['security'] = security
    return spec
