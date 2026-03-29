import os
from flask import Flask
from .config import config_map
from .extensions import db, migrate, init_redis


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['development']))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    init_redis(app)

    # Register blueprints
    from .blueprints.dashboard import dashboard_bp
    from .blueprints.topics import topics_bp
    from .blueprints.prompts import prompts_bp
    from .blueprints.pipeline import pipeline_bp
    from .blueprints.settings import settings_bp
    from .blueprints.webhook import webhook_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(topics_bp, url_prefix='/topics')
    app.register_blueprint(prompts_bp, url_prefix='/prompts')
    app.register_blueprint(pipeline_bp, url_prefix='/pipeline')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(webhook_bp, url_prefix='/webhook')

    # Ensure output directories exist
    for subdir in ['scripts', 'audio', 'images', 'videos']:
        os.makedirs(os.path.join(app.config['OUTPUT_DIR'], subdir), exist_ok=True)

    # Register CLI commands
    register_commands(app)

    # Initialize scheduler and Telegram webhook (skip during CLI commands)
    if not app.config.get('TESTING') and os.environ.get('FLASK_RUN_FROM_CLI') != 'true':
        with app.app_context():
            _init_services(app)

    return app


def _init_services(app):
    """Initialize background services (scheduler, Telegram webhook)."""
    try:
        from .services.system.scheduler_service import init_scheduler
        init_scheduler(app)
    except Exception as e:
        print(f'[Init] Scheduler init failed: {e}')

    # Set Telegram webhook if ngrok domain is configured
    ngrok_domain = app.config.get('NGROK_DOMAIN')
    if ngrok_domain:
        try:
            from .services.distribution.telegram_service import set_webhook
            webhook_url = f'https://{ngrok_domain}/webhook/telegram'
            result = set_webhook(webhook_url)
            print(f'[Init] Telegram webhook set: {webhook_url} -> {result.get("ok")}')
        except Exception as e:
            print(f'[Init] Telegram webhook failed: {e}')

def register_commands(app):
    """Register custom Flask CLI commands."""

    @app.cli.command('seed')
    def seed_command():
        """Seed default prompts and settings into Redis."""
        from .services.system.settings_service import init_defaults
        from .extensions import redis_client
        from datetime import datetime

        # Seed default settings
        init_defaults()
        print('Default settings seeded.')

        # Seed default prompts (system + user prompt pairs)
        prompts = {
            'topic_generation': {
                'step': 'topic_generation',
                'description': 'AI에게 유튜브 영상 주제 3개를 추천받는 프롬프트',
                'system_prompt': (
                    'You are a YouTube content strategist for "LoreDrop", a faceless English-language '
                    'YouTube channel that introduces fascinating Korean history and culture stories '
                    'to international audiences.\n\n'
                    'Channel concept: Stories that every Korean knows but most foreigners have never heard of.\n\n'
                    'Examples of content directions (not limited to these):\n'
                    '- Ancient kingdoms: Goguryeo, Baekje, Silla, Gaya\n'
                    '- Goryeo Dynasty: Mongol invasions, Buddhist culture\n'
                    '- Joseon Dynasty: royal court intrigue, scientific inventions\n'
                    '- Japanese occupation (1910-1945): resistance movements\n'
                    '- Korean War (1950-1953): untold stories\n'
                    '- Modern Korea (1960s-1990s): democratization, industrialization\n'
                    '- Contemporary Korea (2000s-present): tech, social phenomena\n'
                    '- K-culture origins: business systems behind K-pop, K-drama, K-food\n'
                    '- Korean social issues: education, military service, birth rate\n'
                    '- Korean internet & gaming culture\n'
                    '- Korean food history and origin stories\n'
                    '- Korean mythology with historical roots\n'
                    '- Korean inventions that preceded the West\n\n'
                    'Important: Do NOT over-represent any single era. '
                    'Each set of 3 topics MUST include at least 1 topic from post-2000 contemporary Korea.\n\n'
                    'Target audience: English-speaking viewers interested in Asian history, mystery, and culture\n'
                    'Video format: 8-10 minutes, narration + stock footage, no face on camera\n\n'
                    'When suggesting topics, think about:\n'
                    '- What would make a non-Korean viewer say "Wait, that actually happened?"\n'
                    '- Stories with dramatic tension, mystery, or unexpected twists\n'
                    '- Topics with very little existing English-language YouTube coverage'
                ),
                'user_prompt': (
                    '오늘의 영상 주제 {count}개를 추천해줘.\n\n'
                    '주제 선정 기준:\n'
                    '- {count}개 주제는 서로 다른 시대·분야에서 고를 것 (다양성 확보)\n'
                    '- 영어권 유튜브에서 아직 많이 다뤄지지 않은 대한민국에서 벌어졌던 흥미로운 주제를 우선 추천\n'
                    '- 한국인이라면 알 만하지만 외국인은 처음 들을 이야기 위주\n\n'
                    '중요: 반드시 실제 역사적 사실에 기반한 주제만 추천할 것.\n'
                    '확실하지 않은 사건이나 과장된 이야기는 추천하지 마.\n'
                    '각 주제의 story_points에 구체적인 연도, 인물명, 사건명을 반드시 포함할 것.\n\n'
                    '이전에 다룬 주제 목록 (중복 금지):\n{existing_topics}\n\n'
                    '반드시 아래 JSON 형식으로만 응답해.\n'
                    '코드블록 없이 순수 JSON만 출력:\n\n'
                    '{\n'
                    '  "topics": [\n'
                    '    {\n'
                    '      "number": 1,\n'
                    '      "title_en": "영어 제목",\n'
                    '      "title_kr": "한글 제목",\n'
                    '      "summary_kr": "한줄 요약 (한국어)",\n'
                    '      "why_surprising": "왜 외국인이 놀랄 주제인가 (한국어, 한 문장)",\n'
                    '      "title_options": ["영어 제목안 1", "영어 제목안 2"],\n'
                    '      "keywords": "keyword1, keyword2, keyword3",\n'
                    '      "story_points": "스토리 핵심 포인트 3~4줄 (한국어)",\n'
                    '      "difficulty": "상/중/하"\n'
                    '    }\n'
                    '  ]\n'
                    '}'
                ),
            },
            'script_short': {
                'step': 'script_generation',
                'description': '약 1분 길이의 YouTube Shorts 구조화된 한국어 대본 생성',
                'system_prompt': (
                    'You are a scriptwriter for "LoreDrop", a faceless YouTube Shorts channel '
                    'that tells fascinating Korean history and culture stories to international audiences.\n\n'
                    'You write structured scripts in Korean. Each paragraph includes:\n'
                    '- Narration text (Korean)\n'
                    '- Visual scene description (English, for AI image generation)\n'
                    '- Mood/tone tag (for TTS voice control)\n\n'
                    'Target: ~1 minute narration (~600-700 Korean characters total).\n'
                    'IMPORTANT: Write narration ONLY in Korean. Do NOT include any English translation of the narration.'
                ),
                'user_prompt': (
                    '다음 주제에 대해 약 1분 길이의 쇼츠 대본을 작성해줘:\n'
                    '주제: {topic}\n\n'
                    '작성 규칙:\n'
                    '- 6-8개 문단으로 구성\n'
                    '- 첫 문단은 강력한 hook (시청자가 스크롤을 멈출 것)\n'
                    '- 마지막 문단은 여운/반전\n'
                    '- 구체적인 연도, 인물명, 수치 포함\n'
                    '- 나레이션 총 글자 수: 약 600-700자 (한국어)\n\n'
                    '반드시 아래 JSON 형식으로만 응답해. 코드블록 없이 순수 JSON만 출력:\n\n'
                    '{\n'
                    '  "paragraphs": [\n'
                    '    {\n'
                    '      "narration": "한국어 나레이션 텍스트",\n'
                    '      "scene": "한국어 장면 묘사 (예: 어두운 회의실, 1980년대 한국, 극적인 조명)",\n'
                    '      "mood": "분위기 키워드 (예: 긴장감, 신비로움, 승리감, 비장함, 극적, 경이로움, 충격, 희망적)"\n'
                    '    }\n'
                    '  ]\n'
                    '}'
                ),
            },
            'script_long': {
                'step': 'script_generation',
                'description': '8-10분 길이의 YouTube 본편 대본 생성',
                'system_prompt': (
                    'You are a scriptwriter for "LoreDrop", a faceless YouTube channel '
                    'covering Korean history and culture for international audiences.\n'
                    'Write documentary-style scripts for 8-10 minute narration.\n'
                    'Style: informative, dramatic, with clear narrative arc.\n'
                    'Language: Korean narration script.'
                ),
                'user_prompt': (
                    '다음 주제에 대해 8-10분 분량의 영상 대본을 작성해줘:\n'
                    '주제: {topic}\n\n'
                    '작성 규칙:\n'
                    '- 도입부: 강력한 hook으로 시작 (시청자 이탈 방지)\n'
                    '- 본문: 시간순 또는 논리적 흐름으로 전개\n'
                    '- 결론: 여운 또는 교훈을 남기는 마무리\n'
                    '- 총 15-20개 문단으로 구성\n'
                    '- 나레이션 톤: 다큐멘터리 스타일\n'
                    '- 전체 글자 수: 약 2,000-2,500자 (한국어 기준)\n\n'
                    '각 문단을 빈 줄로 구분하여 작성해줘.'
                ),
            },
            'script_translate': {
                'step': 'script_generation',
                'description': '한국어 대본을 영어로 번역 (나레이션 + 장면 + 분위기 포함)',
                'system_prompt': (
                    'You are a professional translator for "LoreDrop", a YouTube channel '
                    'that tells Korean stories to English-speaking audiences (teens/20s).\n\n'
                    'Translate Korean scripts into natural, engaging English.\n'
                    'Translate ALL fields: narration, scene description, and mood keyword.\n'
                    'IMPORTANT: Output structured JSON only. No commentary.'
                ),
                'user_prompt': (
                    'Translate the following Korean YouTube script to English.\n'
                    'Translate ALL fields: narration, scene, and mood.\n\n'
                    'Rules:\n'
                    '- Narration: natural spoken English for TTS (teens/20s audience)\n'
                    '- Scene: English description for AI image generation (20-30 words)\n'
                    '- Mood: single English keyword (e.g. tense, mysterious, triumphant, somber)\n'
                    '- Keep the same number of paragraphs\n'
                    '- Output ONLY JSON, no commentary or code block\n\n'
                    'Korean script:\n{script}\n\n'
                    'Output format:\n'
                    '{"paragraphs": [{"narration": "...", "scene": "...", "mood": "..."}]}'
                ),
            },
            'scene_direction': {
                'step': 'scene_direction',
                'description': '대본 문단별 장면 묘사 생성 (이미지/영상 생성용)',
                'system_prompt': (
                    'You are a visual director for a YouTube channel. '
                    'Generate concise, vivid scene descriptions in English '
                    'for AI image generation tools (Midjourney, DALL-E).'
                ),
                'user_prompt': (
                    '다음 대본 문단에 어울리는 영상 장면을 묘사해줘.\n\n'
                    '문단: {paragraph}\n\n'
                    '규칙:\n'
                    '- 장면 묘사를 영어로 작성 (이미지 생성 AI용)\n'
                    '- 분위기, 조명, 색감, 구도를 포함\n'
                    '- 50단어 이내로 간결하게'
                ),
            },
        }

        for name, data in prompts.items():
            if not redis_client.sismember('prompt:list', name):
                redis_client.hset(f'prompt:{name}', mapping={
                    'system_prompt': data['system_prompt'],
                    'user_prompt': data['user_prompt'],
                    'description': data['description'],
                    'step': data['step'],
                    'updated_at': datetime.utcnow().isoformat(),
                })
                redis_client.sadd('prompt:list', name)
                print(f'  Prompt seeded: {name}')
            else:
                print(f'  Prompt exists: {name} (skipped)')

        print('Seed complete.')
