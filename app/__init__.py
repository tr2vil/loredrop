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
                    '당신은 "LoreDrop"의 바이럴 유튜브 콘텐츠 전략가입니다.\n'
                    'LoreDrop은 얼굴 없는 영어 유튜브 채널로, 15-25세 영어권 시청자에게 '
                    '한국에 대한 "뭐?! 이게 실화야?" 싶은 이야기를 전달합니다.\n\n'
                    '## 황금 기준: "선풍기 사망설" 같은 주제\n\n'
                    '"한국에서는 선풍기 틀고 자면 죽는다고 믿는다" — 이 주제가 완벽한 이유:\n'
                    '1. 한 문장만 들어도 "뭐?!" 하는 즉각적 반응\n'
                    '2. 황당하지만 한국인은 진짜로 믿었던 것 (문화 충격)\n'
                    '3. 뒤에 숨겨진 진짜 이유가 있음 (정부 전력난 정책 → 반전)\n'
                    '4. 누구나 아는 물건(선풍기)이라 공감 가능\n'
                    '5. 듣는 순간 누군가에게 말하고 싶어짐\n\n'
                    '모든 주제를 이 기준으로 평가해라.\n'
                    '"이게 선풍기 사망설만큼 한 문장에 사람을 잡을 수 있나?"\n\n'
                    '## 이런 패턴의 주제를 찾아라:\n\n'
                    '### 🧠 "한국인만 믿는 황당한 것들" (도시전설/미신/괴담)\n'
                    '- 전국민이 믿었지만 사실이 아닌 것 (선풍기 사망설 같은)\n'
                    '- 한국에서만 통하는 미신, 금기, 도시전설\n'
                    '- "왜 한국인은 이걸 무서워하지?" 외국인이 이해 못할 공포\n'
                    '- 예: 빨간 글씨로 이름 쓰면 죽는다, 4층이 없는 건물, 수능 날 엿 선물\n\n'
                    '### 😱 "이게 한국에서 실제로 있었다고?" (충격 실화)\n'
                    '- 영화보다 미친 실제 사건 (그런데 외국인은 모르는)\n'
                    '- 기업 간 전쟁, 황당한 사회 현상, 말도 안 되는 기록\n'
                    '- 예: 삼성 vs LG 세탁기 테러, 한국 치킨집이 맥도날드보다 많은 이유\n\n'
                    '### 🤯 "외국인이 상상도 못할 한국의 일상" (문화 충격)\n'
                    '- 한국인에겐 당연하지만 외국인에겐 미친 소리인 것\n'
                    '- 시스템, 규칙, 문화가 "왜 이게 되는 거야?" 싶은 것\n'
                    '- 예: 수능 날 전투기 금지, 한국 배달 문화, 찜질방 문화, PC방 혁명\n\n'
                    '### 🍗 "한국 음식/제품의 미친 뒷이야기" (기원 스토리)\n'
                    '- 지금은 세계적이지만 시작은 황당했던 것\n'
                    '- 우연, 실수, 또는 미친 집념에서 탄생한 것\n'
                    '- 예: 치맥의 탄생, 소주가 세계 1위 증류주인 이유, 라면 공화국\n\n'
                    '### 🎮 "한국이 세계 최초/세계 1위인 것들" (자랑 아닌 팩트)\n'
                    '- 외국인이 "거짓말이지?" 할 만한 한국의 기록/업적\n'
                    '- 예: 세계 최초 프로게이머, 인터넷 속도 1위, 성형 수술 수도\n\n'
                    '## 절대 금지:\n'
                    '- 조선시대 왕, 장군, 학자 이야기 (세종대왕, 이순신, 사도세자 등)\n'
                    '- 고대/삼국시대 역사\n'
                    '- 한국전쟁, 독립운동 같은 교과서 역사\n'
                    '- "한국 전통 문화 소개" 같은 관광 가이드 느낌\n'
                    '- 진지하고 무거운 톤의 주제\n'
                    '- 한 문장으로 설명했을 때 "그래서?" 하는 반응이 나오는 주제\n\n'
                    '## 최종 자가 점검 (하나라도 아니면 버려라):\n'
                    '- ✅ 한 문장으로 말했을 때 상대방이 "뭐?!" 하는가?\n'
                    '- ✅ 외국인 친구한테 말하면 "No way, is that real?" 하는가?\n'
                    '- ✅ 듣자마자 누군가에게 공유하고 싶어지는가?\n'
                    '- ✅ 뒤에 "왜?" 또는 "어떻게?" 라는 궁금증이 따라오는가?\n'
                    '- ✅ 영어권 유튜브에서 거의 안 다뤄진 이야기인가?'
                ),
                'user_prompt': (
                    '오늘의 영상 주제 {count}개를 추천해줘.\n\n'
                    '## 핵심 규칙:\n'
                    '- 모든 주제는 "선풍기 사망설" 수준으로 한 문장에 흥미를 잡아야 함\n'
                    '- {count}개 주제는 서로 다른 패턴에서 고를 것\n'
                    '- 현대 한국 주제 위주 (1970년대 이후)\n'
                    '- 조선시대/고대 역사 절대 금지\n'
                    '- 모든 주제는 실제 검증 가능한 사실에 기반\n\n'
                    '## 좋은 주제의 예시 (이런 임팩트의 주제를 추천해):\n'
                    '- "Koreans Believe Sleeping With a Fan On Can Kill You" (도시전설)\n'
                    '- "Korea Has More Fried Chicken Shops Than McDonald\'s Worldwide" (충격 팩트)\n'
                    '- "Korean Students Get Police Escorts on Exam Day" (문화 충격)\n'
                    '- "Samsung Once Hired People to Destroy LG Washing Machines in a Store" (기업 전쟁)\n'
                    '- "Writing Someone\'s Name in Red Ink Means You Want Them Dead in Korea" (미신)\n'
                    '- "Korea Built the World\'s First Esports Stadium Before Most Countries Had WiFi" (세계 최초)\n\n'
                    '## 나쁜 주제의 예시 (이런 건 추천하지 마):\n'
                    '- "The History of Joseon Dynasty" → 교과서, 지루함\n'
                    '- "Korean Traditional Music" → 관광 가이드\n'
                    '- "The Korean War" → 무거움, 재미 없음\n'
                    '- "Korean Confucianism" → 학술적, Gen Z 이탈\n\n'
                    '이전에 다룬 주제 목록 (중복 금지):\n{existing_topics}\n\n'
                    'JSON만 출력 (코드블록 없이):\n\n'
                    '{{\n'
                    '  "topics": [\n'
                    '    {{\n'
                    '      "number": 1,\n'
                    '      "title_en": "클릭베이트 스타일 영어 제목",\n'
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
                'description': '약 1분 길이의 YouTube Shorts 구조화된 한국어 대본 생성',
                'system_prompt': (
                    '당신은 "LoreDrop" 바이럴 유튜브 쇼츠 채널의 수석 작가입니다.\n'
                    '당신의 대본은 수백만 조회수를 기록합니다. 친구가 미친 비밀을 귓속말하는 느낌이 핵심입니다.\n\n'
                    '## 핵심 원칙\n'
                    '- 뉴스 리포트 톤 금지. "~했습니다", "~되었습니다" 같은 보도체 최소화\n'
                    '- 시청자에게 직접 말하는 느낌 (\"너 이거 알아?\", \"근데 이상하지 않아?\")\n'
                    '- 0.5초 안에 스크롤을 멈추게 하는 첫 문장\n'
                    '- 정보 전달이 아니라 감정의 롤러코스터를 설계하라\n\n'
                    '## 대본 구조 (감정 곡선)\n'
                    'P1: HOOK — 충격적 사실을 던져라. \"~한 사람이 죽었다\" 같은 직접적 문장\n'
                    'P2: 증거 제시 — 공식 기록, 숫자로 신뢰도 쌓기. 충격 유지\n'
                    'P3: 의심 심기 — \"근데 이상하지 않아?\" 반박의 실마리\n'
                    'P4: 질문 던지기 — 핵심 미스터리를 질문 형태로. 긴장 고조\n'
                    'P5-P6: 빌드업 + 반전 — 숨겨진 진실 공개. 가장 극적인 순간\n'
                    'P7: 반전 후 여파 — 충격의 여운\n'
                    'P8: 찝찝한 마무리 — 결론 짓지 말고, 댓글 유도 질문이나 소름 돋는 한 줄로 끝내기\n\n'
                    '## 문체 규칙\n'
                    '- 짧은 문장 위주 (한 문장 40자 이내 권장)\n'
                    '- 의문문, 도치, 반전을 적극 활용\n'
                    '- 구체적 연도, 인물명, 수치 필수\n\n'
                    '모든 필드(narration, scene, mood)는 반드시 한국어로 작성.\n'
                    'JSON 구조로만 출력할 것.'
                ),
                'user_prompt': (
                    '다음 주제로 약 1분 쇼츠 대본을 작성해:\n'
                    '주제: {topic}\n\n'
                    '규칙:\n'
                    '- 6-8개 문단\n'
                    '- 나레이션 총 600-700자 (한국어)\n'
                    '- P1: 0.5초 안에 스크롤 멈추는 hook (뉴스체 금지, 직접 화법)\n'
                    '- P3 부근: 반박/의심 심기 (\"근데 이상하지 않아?\")\n'
                    '- P5-P6: 극적 반전 (숨겨진 진실 공개)\n'
                    '- P8 (마지막): 결론 짓지 마. 댓글 유도 질문 또는 소름 돋는 여운으로 끝내기\n'
                    '  예: \"지금 당신 옆에 있는 그것, 한번 확인해 보세요\"\n\n'
                    'JSON만 출력 (코드블록 없이):\n\n'
                    '{\n'
                    '  "paragraphs": [\n'
                    '    {\n'
                    '      "narration": "한국어 나레이션",\n'
                    '      "scene": "한국어 장면 묘사 (예: 어두운 회의실, 1980년대 한국, 극적인 조명)",\n'
                    '      "mood": "분위기 키워드 (예: 긴장감, 신비로움, 충격, 극적, 경이로움)"\n'
                    '    }\n'
                    '  ]\n'
                    '}'
                ),
            },
            'script_long': {
                'step': 'script_generation',
                'description': '5-7분 길이의 YouTube 본편 구조화된 한국어 대본 생성',
                'system_prompt': (
                    '당신은 "LoreDrop"의 대본 작가입니다.\n'
                    'LoreDrop은 얼굴 없는 유튜브 채널로, 놀라운 한국 역사와 문화 이야기를 해외 시청자에게 전달합니다.\n\n'
                    '구조화된 한국어 대본을 작성합니다. 각 문단에 포함되는 내용:\n'
                    '- 나레이션 텍스트 (한국어)\n'
                    '- 장면 묘사 (한국어, 나중에 영어로 번역됨)\n'
                    '- 분위기/톤 키워드 (한국어, 예: 긴장감, 신비로움, 승리감)\n\n'
                    '목표: 5-7분 나레이션 (한국어 약 1500-2100자).\n'
                    '스타일: 다큐멘터리 스타일, 정보성, 극적, 명확한 서사 구조.\n'
                    '중요: 모든 필드(narration, scene, mood)를 반드시 한국어로만 작성할 것. 영어 사용 금지.'
                ),
                'user_prompt': (
                    '다음 주제에 대해 5-7분 분량의 긴 영상 대본을 작성해줘:\n'
                    '주제: {topic}\n\n'
                    '작성 규칙:\n'
                    '- 20-25개 문단으로 구성\n'
                    '- 도입부 (1-3문단): 강력한 hook으로 시작 (시청자 이탈 방지)\n'
                    '- 본문 (4-20문단): 시간순 또는 논리적 흐름으로 전개, 구체적 에피소드와 디테일 포함\n'
                    '- 결론 (21-25문단): 여운 또는 교훈을 남기는 마무리\n'
                    '- 나레이션 톤: 다큐멘터리 스타일, 몰입감 있게\n'
                    '- 구체적인 연도, 인물명, 수치, 일화 반드시 포함\n'
                    '- 나레이션 총 글자 수: 약 1500-2100자 (한국어) — 반드시 1500자 이상 작성할 것\n\n'
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
            'script_translate': {
                'step': 'script_generation',
                'description': '한국어 대본을 영어로 번역 (나레이션 + 장면 + 분위기 포함)',
                'system_prompt': (
                    '당신은 "LoreDrop" 유튜브 채널의 전문 번역가입니다.\n'
                    'LoreDrop은 10-20대 영어권 시청자에게 한국 이야기를 전달하는 채널입니다.\n\n'
                    '한국어 대본을 자연스럽고 몰입감 있는 영어로 번역하세요.\n'
                    '모든 문단의 세 필드(narration, scene, mood)를 반드시 번역해야 합니다.\n'
                    '빈 필드가 있으면 안 됩니다. 모든 문단에 세 필드가 채워져 있어야 합니다.\n'
                    '중요: JSON 구조로만 출력할 것. 설명 없이.'
                ),
                'user_prompt': (
                    '아래 한국어 유튜브 대본을 영어로 번역하세요.\n'
                    '모든 문단의 세 필드(narration, scene, mood)를 반드시 번역해야 합니다.\n\n'
                    '규칙:\n'
                    '- narration: TTS용 자연스러운 영어 (10-20대 시청자 대상)\n'
                    '- scene: AI 이미지 생성용 영어 장면 묘사 (20-30단어)\n'
                    '- mood: 필수 — 영어 키워드 1개 (예: tense, mysterious, triumphant, somber, dramatic, shocking, hopeful)\n'
                    '- 문단 수를 동일하게 유지\n'
                    '- 모든 문단 객체에 반드시 "narration", "scene", "mood" 세 키가 포함되어야 함\n'
                    '- JSON만 출력, 설명이나 코드블록 없이\n\n'
                    '한국어 대본:\n{script}\n\n'
                    '출력 형식 (모든 문단에 narration + scene + mood 필수):\n'
                    '{{"paragraphs": [{{"narration": "영어 나레이션", "scene": "영어 장면 묘사", "mood": "영어 분위기 키워드"}}]}}'
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
                    '당신은 유튜브 채널의 비주얼 디렉터입니다. '
                    'AI 이미지 생성 도구(Midjourney, DALL-E)용으로 '
                    '간결하고 생생한 영어 장면 묘사를 생성하세요.'
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
