from ...extensions import redis_client

VALID_SECTIONS = ['tts', 'midjourney', 'general', 'api_keys']

# Default values for each settings section
DEFAULTS = {
    'tts': {
        'ko_voice_id': '',
        'en_voice_id': '',
        'model_id': 'eleven_multilingual_v2',
        'stability': '0.5',
        'similarity': '0.75',
        'style': '0.0',
        'speed': '1.0',
    },
    'midjourney': {
        'style_preset': 'cinematic dark moody historical',
        'aspect_ratio': '9:16',
        'quality': 'medium',
        'version': 'v6.1',
        'negative_prompt': '',
        'character_refs': '',
    },
    'general': {
        'default_language': 'ko',
        'default_video_type': 'short',
        'daily_topic_count': '3',
        'schedule_time': '09:00',
        'telegram_enabled': 'true',
    },
    'api_keys': {},
}


def get_settings(section):
    """Get all settings for a section, with defaults applied."""
    if section not in VALID_SECTIONS:
        raise ValueError(f'Invalid section: {section}')
    stored = redis_client.hgetall(f'settings:{section}')
    defaults = DEFAULTS.get(section, {})
    return {**defaults, **stored}


def update_settings(section, data):
    """Update settings for a section."""
    if section not in VALID_SECTIONS:
        raise ValueError(f'Invalid section: {section}')
    if data:
        redis_client.hset(f'settings:{section}', mapping=data)


def get_setting(section, key, default=None):
    """Get a single setting value."""
    val = redis_client.hget(f'settings:{section}', key)
    if val is None:
        return DEFAULTS.get(section, {}).get(key, default)
    return val


def init_defaults():
    """Initialize default settings if not already set."""
    for section, defaults in DEFAULTS.items():
        if not defaults:
            continue
        existing = redis_client.hgetall(f'settings:{section}')
        missing = {k: v for k, v in defaults.items() if k not in existing}
        if missing:
            redis_client.hset(f'settings:{section}', mapping=missing)
