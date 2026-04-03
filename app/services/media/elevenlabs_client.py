from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from elevenlabs.core import ApiError
from flask import current_app

# API error code → user-friendly message
_ERROR_MESSAGES = {
    'voice_not_found': 'Voice ID not found. Check Settings > TTS or .env ELEVENLABS_EN_VOICE_ID.',
    'invalid_api_key': 'Invalid API key. Check .env ELEVENLABS_API_KEY.',
    'quota_exceeded': 'ElevenLabs character quota exceeded. Upgrade your plan or wait for reset.',
    'rate_limit_exceeded': 'Too many requests. Please wait a moment and retry.',
    'paid_plan_required': 'Free plan cannot use library voices via API. Upgrade to Starter ($5/mo) or use a default voice.',
    'payment_required': 'Free plan cannot use library voices via API. Upgrade to Starter ($5/mo) or use a default voice.',
}


def get_client():
    api_key = current_app.config['ELEVENLABS_API_KEY']
    if not api_key:
        raise ValueError('ELEVENLABS_API_KEY is not configured.')
    return ElevenLabs(api_key=api_key)


def text_to_speech(text, voice_id, model_id='eleven_multilingual_v2',
                   stability=0.5, similarity=0.75, style=0.0, speed=1.0,
                   output_format='mp3_44100_128'):
    """Convert text to speech using ElevenLabs API.

    Returns audio data as bytes.
    """
    client = get_client()
    try:
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=float(stability),
                similarity_boost=float(similarity),
                style=float(style),
                speed=float(speed),
            ),
            output_format=output_format,
        )
        return b''.join(audio)
    except ApiError as e:
        raise ValueError(_friendly_error(e)) from None


def _friendly_error(e):
    """Extract a clean message from an ElevenLabs ApiError."""
    body = e.body if hasattr(e, 'body') else None
    if isinstance(body, dict):
        detail = body.get('detail', {})
        if isinstance(detail, dict):
            code = detail.get('status') or detail.get('code', '')
            if code in _ERROR_MESSAGES:
                return _ERROR_MESSAGES[code]
            msg = detail.get('message', '')
            if msg:
                return f'ElevenLabs: {msg}'
    return f'ElevenLabs API error (HTTP {e.status_code})'
