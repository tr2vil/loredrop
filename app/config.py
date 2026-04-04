import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://loredrop:loredrop@localhost:5432/loredrop'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Telegram
    TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHATID', '')

    # ngrok
    NGROK_DOMAIN = os.environ.get('NGROK_DOMAIN', '')

    # Claude API
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    # ElevenLabs
    ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
    ELEVENLABS_KO_VOICE_ID = os.environ.get('ELEVENLABS_KO_VOICE_ID', '')
    ELEVENLABS_EN_VOICE_ID = os.environ.get('ELEVENLABS_EN_VOICE_ID', '')

    # Leonardo.ai
    LEONARDO_API_KEY = os.environ.get('LEONARDO_API_KEY', '')

    # YouTube
    YOUTUBE_CLIENT_ID = os.environ.get('YOUTUBE_CLIENT_ID', '')
    YOUTUBE_CLIENT_SECRET = os.environ.get('YOUTUBE_CLIENT_SECRET', '')

    # n8n
    N8N_URL = os.environ.get('N8N_URL', 'http://localhost:5678')

    # Output paths
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output'))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
