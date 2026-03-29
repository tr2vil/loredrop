from flask import Blueprint, render_template, jsonify, request
from ..services.system.settings_service import get_settings, update_settings, VALID_SECTIONS

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def index():
    return render_template('settings/index.html')


@settings_bp.route('/api/<section>', methods=['GET'])
def get_section(section):
    if section not in VALID_SECTIONS:
        return jsonify({'error': 'Invalid section'}), 400
    return jsonify(get_settings(section))


@settings_bp.route('/api/<section>', methods=['PUT'])
def update_section(section):
    if section not in VALID_SECTIONS:
        return jsonify({'error': 'Invalid section'}), 400
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    update_settings(section, data)
    return jsonify({'ok': True})
