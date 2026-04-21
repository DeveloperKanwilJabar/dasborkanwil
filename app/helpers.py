import os
import pendulum
from flask import jsonify

def now_utc():
    return pendulum.now('UTC')

def json_response(success, message, data=None, status=200):
    return jsonify({
        "success": success,
        "message": message,
        "data": data
    }), status

# Helper lain tetap murni tanpa impor dari package 'app'