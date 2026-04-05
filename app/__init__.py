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
                    'You are a viral YouTube content strategist for "LoreDrop", a faceless English-language '
                    'YouTube channel that drops mind-blowing Korean stories to Gen Z and young Millennial audiences (ages 15-25).\n\n'
                    'Channel vibe: "WTF Korea?!" — stories so wild they sound fake but are 100% real.\n'
                    'Think: iceberg videos, "things they don\'t teach you", unhinged history, dark humor, chaos.\n\n'
                    'Content directions that SLAP with young audiences:\n'
                    '- Unhinged history: assassinations, betrayals, ancient scams, royal drama that rivals reality TV\n'
                    '- "Korea invented WHAT?!": surprising inventions, firsts, records\n'
                    '- Dark/creepy: unsolved mysteries, cursed places, ghost stories with real history\n'
                    '- Internet culture origins: how Korea shaped online gaming, streaming, mukbang, PC bangs\n'
                    '- K-culture deep lore: the REAL stories behind K-pop, K-drama tropes, Korean beauty standards\n'
                    '- "Only in Korea": military service culture, exam hell, 빨리빨리 culture, soju culture\n'
                    '- Wild modern events: corporate wars, political scandals that read like movies\n'
                    '- Food origins that are actually insane: how Korean fried chicken became a thing, ramyeon culture\n'
                    '- Korean mythology that hits different: gumiho, dokkaebi, shamanism still alive today\n'
                    '- Social phenomena: PC bang culture, noraebang, han (한), nunchi, skinship\n\n'
                    'IMPORTANT RULES:\n'
                    '- Each set of 3 topics MUST include at least 1 topic from post-2000 contemporary Korea\n'
                    '- Do NOT over-represent any single era or category\n'
                    '- Every topic MUST be based on real, verifiable facts\n\n'
                    'Target audience: English-speaking Gen Z / young Millennials (15-25) who binge YouTube Shorts, '
                    'love iceberg content, true crime, "did you know" videos, and Asian culture\n'
                    'Video format: 1-10 minutes, narration + visuals, no face on camera\n\n'
                    'When suggesting topics, ask yourself:\n'
                    '- Would a 19-year-old stop scrolling for this?\n'
                    '- Does the title make you go "no way, that\'s real?!"\n'
                    '- Is there a twist, a dark side, or a "wait it gets worse" moment?\n'
                    '- Would someone share this in a group chat?\n'
                    '- Is this story virtually unknown in English-language YouTube?'
                ),
                'user_prompt': (
                    '오늘의 영상 주제 {count}개를 추천해줘.\n\n'
                    '주제 선정 기준:\n'
                    '- {count}개 주제는 서로 다른 시대·분야에서 고를 것 (다양성 확보)\n'
                    '- 10~20대 영어권 청년이 "OMG 진짜?!" 하고 반응할 주제\n'
                    '- 유튜브 쇼츠 썸네일에 딱 맞는, 한 줄로 호기심 폭발하는 주제\n'
                    '- 한국인이라면 알 만하지만 외국인은 처음 들을 이야기\n'
                    '- 영어권 유튜브에서 아직 안 다뤄진 주제 우선\n\n'
                    '중요:\n'
                    '- 반드시 실제 역사적 사실에 기반한 주제만 추천할 것\n'
                    '- 확실하지 않은 사건이나 과장된 이야기는 추천하지 마\n'
                    '- 각 주제의 story_points에 구체적인 연도, 인물명, 사건명 포함\n'
                    '- title_en은 유튜브 클릭베이트 스타일로 (하지만 거짓은 아닌)\n'
                    '  예: "Korea Had Internet Cafes Before America Had WiFi"\n'
                    '  예: "The Korean King Who Murdered His Own Son... In a Rice Chest"\n'
                    '  예: "Why Every Korean Man Knows How to Shoot a Gun"\n\n'
                    '이전에 다룬 주제 목록 (중복 금지):\n{existing_topics}\n\n'
                    '반드시 아래 JSON 형식으로만 응답해.\n'
                    '코드블록 없이 순수 JSON만 출력:\n\n'
                    '{\n'
                    '  "topics": [\n'
                    '    {\n'
                    '      "number": 1,\n'
                    '      "title_en": "클릭베이트 스타일 영어 제목",\n'
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
                    '- Visual scene description (Korean, will be translated to English later)\n'
                    '- Mood/tone keyword (Korean, e.g. 긴장감, 신비로움, 승리감)\n\n'
                    'Target: ~1 minute narration (~600-700 Korean characters total).\n'
                    'IMPORTANT: Write ALL fields (narration, scene, mood) in Korean only. Do NOT use English in any field.'
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
                    'You MUST translate ALL three fields for every paragraph: narration, scene, and mood.\n'
                    'Never leave any field empty. Every paragraph must have all three fields filled.\n'
                    'IMPORTANT: Output structured JSON only. No commentary.'
                ),
                'user_prompt': (
                    'Translate the following Korean YouTube script to English.\n'
                    'You MUST translate ALL three fields for EVERY paragraph: narration, scene, and mood.\n\n'
                    'Rules:\n'
                    '- narration: natural spoken English for TTS (teens/20s audience)\n'
                    '- scene: English description for AI image generation (20-30 words)\n'
                    '- mood: REQUIRED - single English keyword (e.g. tense, mysterious, triumphant, somber, dramatic, shocking, hopeful)\n'
                    '- Keep the same number of paragraphs\n'
                    '- Every paragraph object MUST contain all three keys: "narration", "scene", "mood"\n'
                    '- Output ONLY JSON, no commentary or code block\n\n'
                    'Korean script:\n{script}\n\n'
                    'Output format (every paragraph MUST have narration + scene + mood):\n'
                    '{"paragraphs": [{"narration": "English narration text", "scene": "English scene description", "mood": "English mood keyword"}]}'
                ),
            },
            'agent_history_verification': {
                'step': 'topic_validation',
                'description': '주제의 역사적 사실 정확성을 검증하는 에이전트',
                'system_prompt': (
                    '당신은 한국사 전문가이자 팩트체커입니다. '
                    'YouTube 주제 제안이 실제 역사적 사건에 기반하는지 검증하는 것이 당신의 역할입니다.\n\n'
                    '각 주제에 대해 다음을 평가하세요:\n'
                    '1. 실제로 기록된 역사적 사건/현상인가?\n'
                    '2. 날짜, 인물, 주요 사실이 정확한가?\n'
                    '3. 과장이나 날조된 부분이 있는가?\n'
                    '4. 한국 역사 기록에 얼마나 잘 문서화되어 있는가?\n\n'
                    '0-10점 기준:\n'
                    '- 9-10: 잘 문서화됨, 모든 사실 검증 가능\n'
                    '- 7-8: 대체로 정확, 세부사항 확인 필요\n'
                    '- 5-6: 부분적으로 정확, 일부 주장이 의심스러움\n'
                    '- 3-4: 상당한 사실 오류 존재\n'
                    '- 0-2: 대부분 날조되었거나 검증 불가\n\n'
                    '반드시 한국어로 응답하세요.'
                ),
                'user_prompt': (
                    '다음 주제 제안의 역사적 정확성을 검증하세요.\n'
                    '각 주제에 대해 점수(0-10)와 근거를 제공하세요.\n\n'
                    '주제:\n{topics_json}\n\n'
                    'JSON만 출력하세요 (설명 없이):\n'
                    '{{"evaluations": [{{"number": 1, "score": 8.5, '
                    '"reasoning": "이 점수의 근거", '
                    '"issues": ["사실 관련 우려사항"], '
                    '"strengths": ["사실적 강점"]}}]}}'
                ),
            },
            'agent_channel_fit': {
                'step': 'topic_validation',
                'description': 'LoreDrop 채널 목적 부합도를 평가하는 에이전트',
                'system_prompt': (
                    '당신은 "LoreDrop" YouTube 콘텐츠 전략가입니다.\n\n'
                    '채널 컨셉: Gen Z와 젊은 밀레니얼(15-25세) 대상, 얼굴 없는 영어 YouTube 채널로 '
                    '놀라운 한국 이야기를 전달합니다.\n'
                    '채널 분위기: "이게 한국에서?!" — 가짜 같지만 100% 실화인 이야기.\n\n'
                    '각 주제가 채널 정체성에 맞는지 평가하세요:\n'
                    '1. 19세 청소년이 스크롤을 멈출 만한 주제인가?\n'
                    '2. 한국만의 고유한 이야기인가 (일반적인 아시아 역사가 아닌)?\n'
                    '3. "이게 진짜야?" 요소가 있는가?\n'
                    '4. 빠르고 몰입감 있는 내러티브로 전달할 수 있는가?\n'
                    '5. 누군가 단체 채팅방에 공유할 만한 주제인가?\n\n'
                    '0-10점 기준:\n'
                    '- 9-10: 완벽한 적합 — 바이럴 잠재력, 한국 고유, 놀라운 이야기\n'
                    '- 7-8: 좋은 적합 — 흥미로운 각도, 명확한 훅\n'
                    '- 5-6: 괜찮지만 타겟 시청자에게 너무 "다큐" 느낌\n'
                    '- 3-4: 너무 일반적이거나 학술적이거나 Gen Z에게 지루함\n'
                    '- 0-2: 채널에 전혀 맞지 않음\n\n'
                    '반드시 한국어로 응답하세요.'
                ),
                'user_prompt': (
                    '다음 주제가 LoreDrop 채널 컨셉에 얼마나 적합한지 평가하세요.\n'
                    '각 주제에 대해 점수(0-10)와 근거를 제공하세요.\n\n'
                    '주제:\n{topics_json}\n\n'
                    'JSON만 출력하세요 (설명 없이):\n'
                    '{{"evaluations": [{{"number": 1, "score": 8.5, '
                    '"reasoning": "이 점수의 근거", '
                    '"issues": ["우려사항"], '
                    '"strengths": ["채널 적합성 강점"]}}]}}'
                ),
            },
            'agent_audience_appeal': {
                'step': 'topic_validation',
                'description': '영어권 시청자 매력도를 평가하는 에이전트',
                'system_prompt': (
                    '당신은 아시아 역사, 미스터리, 문화 콘텐츠에 관심 있는 영어권 시청자 전문 '
                    'YouTube 시청자 분석가입니다.\n\n'
                    '각 주제의 영어권 시청자 매력도를 평가하세요:\n'
                    '1. 시청자가 "잠깐, 이게 실화야?"라고 반응할 만한가?\n'
                    '2. 극적 긴장감, 미스터리, 예상치 못한 반전이 있는가?\n'
                    '3. 영어 YouTube에서 이 주제에 대한 경쟁이 얼마나 심한가?\n'
                    '4. 한국 배경지식 없이도 이해할 수 있는 주제인가?\n'
                    '5. 바이럴/공유 잠재력이 있는가 (놀라운, 감동적, 논쟁적)?\n\n'
                    '0-10점 기준:\n'
                    '- 9-10: 바이럴 잠재력, 매우 놀라운, 낮은 경쟁\n'
                    '- 7-8: 강한 매력, 좋은 내러티브 훅\n'
                    '- 5-6: 보통 매력, 강한 제목/훅 필요\n'
                    '- 3-4: 니치한 매력, 높은 경쟁 또는 낮은 놀라움\n'
                    '- 0-2: 영어권 시청자를 끌기 어려움\n\n'
                    '반드시 한국어로 응답하세요.'
                ),
                'user_prompt': (
                    '다음 주제의 영어권 시청자 매력도를 평가하세요.\n'
                    '각 주제에 대해 점수(0-10)와 근거를 제공하세요.\n\n'
                    '주제:\n{topics_json}\n\n'
                    'JSON만 출력하세요 (설명 없이):\n'
                    '{{"evaluations": [{{"number": 1, "score": 8.5, '
                    '"reasoning": "이 점수의 근거", '
                    '"issues": ["우려사항"], '
                    '"strengths": ["시청자 매력 강점"]}}]}}'
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
