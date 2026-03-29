from flask import Blueprint, request, jsonify

webhook_bp = Blueprint('webhook', __name__)


@webhook_bp.route('/telegram', methods=['POST'])
def telegram_webhook():
    """Receive Telegram Bot API updates."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'ok': False}), 400

    # TODO: Process callback_query and message events
    return jsonify({'ok': True})
