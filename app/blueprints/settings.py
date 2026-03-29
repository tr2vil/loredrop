from flask import Blueprint, render_template, jsonify, request
from ..extensions import redis_client

settings_bp = Blueprint('settings', __name__)

VALID_SECTIONS = ['tts', 'midjourney', 'general', 'api_keys']


@settings_bp.route('/')
def index():
    return render_template('settings/index.html')


@settings_bp.route('/api/<section>', methods=['GET'])
def get_settings(section):
    if section not in VALID_SECTIONS:
        return jsonify({'error': 'Invalid section'}), 400
    data = redis_client.hgetall(f'settings:{section}')
    return jsonify(data)


@settings_bp.route('/api/<section>', methods=['PUT'])
def update_settings(section):
    if section not in VALID_SECTIONS:
        return jsonify({'error': 'Invalid section'}), 400
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    redis_client.hset(f'settings:{section}', mapping=data)
    return jsonify({'ok': True})
