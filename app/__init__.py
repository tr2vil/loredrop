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

    return app


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
                    '```json 코드블록 없이 {{ 로 시작해서 }} 로 끝나는 순수 JSON만 출력:\n\n'
                    '{{\n'
                    '  "topics": [\n'
                    '    {{\n'
                    '      "number": 1,\n'
                    '      "title_en": "영어 제목",\n'
                    '      "title_kr": "한글 제목",\n'
                    '      "summary_kr": "한줄 요약 (한국어)",\n'
                    '      "why_surprising": "왜 외국인이 놀랄 주제인가 (한국어, 한 문장)",\n'
                    '      "title_options": ["영어 제목안 1", "영어 제목안 2"],\n'
                    '      "keywords": "keyword1, keyword2, keyword3",\n'
                    '      "story_points": "스토리 핵심 포인트 3~4줄 (한국어)",\n'
                    '      "difficulty": "상/중/하"\n'
                    '    }}\n'
                    '  ]\n'
                    '}}'
                ),
            },
            'script_short': {
                'step': 'script_generation',
                'description': '약 1분 길이의 YouTube Shorts 대본 생성',
                'system_prompt': (
                    'You are a scriptwriter for "LoreDrop", a faceless YouTube Shorts channel.\n'
                    'Write engaging, concise scripts for ~1 minute narration.\n'
                    'Style: dramatic, mysterious, hook-driven.\n'
                    'Language: Korean narration script.'
                ),
                'user_prompt': (
                    '다음 주제에 대해 약 1분 길이의 쇼츠 대본을 작성해줘:\n'
                    '주제: {topic}\n\n'
                    '작성 규칙:\n'
                    '- 첫 문장에서 시청자의 호기심을 자극할 것 (hook)\n'
                    '- 총 4-6개 문단으로 구성\n'
                    '- 각 문단은 1-3문장\n'
                    '- 나레이션 톤: 긴장감 있고 몰입감 있는 말투\n'
                    '- 마지막 문단에서 여운을 남기거나 반전 제시\n'
                    '- 전체 글자 수: 약 300-400자 (한국어 기준)\n\n'
                    '각 문단을 빈 줄로 구분하여 작성해줘.'
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
