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


@settings_bp.route('/api/tts/test', methods=['POST'])
def test_tts():
    """Test TTS connection with a short sample text."""
    # Use form values from UI if provided, fall back to saved Redis settings
    posted = request.get_json() or {}
    settings = get_settings('tts')
    settings.update({k: v for k, v in posted.items() if v})
    provider = settings.get('provider', 'elevenlabs')
    sample_text = 'Hello, this is a test of the text to speech system.'

    try:
        if provider == 'edge_tts':
            from ..services.media.edge_tts_client import text_to_speech
            audio = text_to_speech(
                text=sample_text,
                voice=settings.get('edge_voice', 'en-US-GuyNeural'),
                rate=settings.get('edge_rate', '+0%'),
                pitch=settings.get('edge_pitch', '+0Hz'),
            )
        else:
            from ..services.media.elevenlabs_client import text_to_speech
            from flask import current_app
            voice_id = (settings.get('en_voice_id')
                        or current_app.config.get('ELEVENLABS_EN_VOICE_ID', ''))
            if not voice_id:
                return jsonify({'ok': False, 'error': 'No English voice ID configured.'}), 400
            audio = text_to_speech(
                text=sample_text,
                voice_id=voice_id,
                model_id=settings.get('model_id', 'eleven_multilingual_v2'),
            )

        import base64
        audio_b64 = base64.b64encode(audio).decode('ascii')
        return jsonify({
            'ok': True,
            'provider': provider,
            'audio_b64': audio_b64,
            'size': len(audio),
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@settings_bp.route('/api/leonardo/upload-style-ref', methods=['POST'])
def upload_style_ref():
    """Download an image from URL and upload it to Leonardo as a style reference."""
    data = request.get_json() or {}
    image_url = data.get('image_url', '').strip()
    if not image_url:
        return jsonify({'error': 'image_url is required'}), 400

    try:
        from ..services.media import leonardo_client

        # Download the image
        image_bytes, ext = leonardo_client.download_image_from_url(image_url)

        # Upload to Leonardo
        init_image_id = leonardo_client.upload_init_image(image_bytes, ext)

        # Save to settings
        update_settings('leonardo', {
            'style_ref_image_id': init_image_id,
            'style_ref_image_url': image_url,
        })

        return jsonify({
            'ok': True,
            'init_image_id': init_image_id,
            'image_url': image_url,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
