# LoreDrop - Claude Code 개발 가이드

이 문서는 Claude Code가 이 프로젝트에서 작업할 때 참고하는 개발 규칙과 컨텍스트입니다.

## 아키텍처

```
[ngrok 고정도메인] → [Flask :8000] → PostgreSQL / Redis
                          ├── Dashboard, Topics, Production, Prompts, Settings
                          ├── Telegram Bot API (양방향)
                          └── n8n (iframe, :5678)
```

- **Flask + Jinja2 + jQuery**: 웹 UI 및 API (단일 앱)
- **PostgreSQL**: 주제, 스크립트, 파이프라인 실행 데이터
- **Redis**: 프롬프트 템플릿, 설정값, 파이프라인 실시간 상태
- **APScheduler**: Flask 내장 스케줄러 (매일 주제 생성)
- **Telegram Bot API**: Flask가 직접 webhook 수신/발신
- **ngrok**: Flask 앱에 HTTPS 터널 연결

## 프로젝트 구조

```
app/
├── __init__.py              # create_app() + CLI commands (seed)
├── config.py                # 환경 설정
├── extensions.py            # db, redis, migrate 초기화
├── models/                  # SQLAlchemy 모델
│   ├── topic.py             #   RecommendedTopic, SelectedTopic
│   ├── script.py            #   Script, ScriptParagraph (narration/scene/mood)
│   ├── pipeline_run.py      #   PipelineRun, PipelineStep
│   └── asset.py             #   Asset
├── blueprints/              # Flask 블루프린트
│   ├── dashboard.py         #   GET / (대시보드)
│   ├── topics.py            #   /topics/* (주제 관리 + 생성 API)
│   ├── pipeline.py          #   /pipeline/* (Production 실행 + Script API)
│   ├── prompts.py           #   /prompts/* (프롬프트 CRUD)
│   ├── settings.py          #   /settings/* (Redis 설정 관리)
│   └── webhook.py           #   /webhook/* (Telegram 콜백)
├── services/                # 비즈니스 로직
│   ├── ai/claude_client.py  #   Claude API 래퍼
│   ├── content/
│   │   ├── topic_service.py #   주제 생성/중복검사/선택
│   │   └── script_service.py#   대본 생성 + 문단 분리 + 번역
│   ├── distribution/
│   │   └── telegram_service.py  # Telegram 양방향 통신
│   └── system/
│       ├── settings_service.py  # Redis 설정 CRUD
│       └── scheduler_service.py # APScheduler
├── pipeline/
│   └── engine.py            # 파이프라인 엔진 (스텝 실행, auto-mode)
├── templates/               # Jinja2 HTML
└── static/                  # CSS, JS
```

## Docker 서비스 (5개)

| 서비스 | 포트 | 역할 |
|--------|------|------|
| app | 8000 | Flask 웹 앱 (Gunicorn) |
| postgres | 5432 | 데이터베이스 |
| redis | 6379 | 캐시/설정/실시간 상태 |
| n8n | 5678 | 참고용 (iframe 접근) |
| ngrok | - | HTTPS 터널 (Flask 앱에 연결) |

### 안전한 명령어
```bash
docker-compose up -d
docker-compose down           # 볼륨 유지
docker-compose restart
docker-compose up -d --build
```

### 절대 사용 금지
```bash
docker-compose down -v        # DB, Redis, n8n 데이터 전부 삭제됨
```

### 볼륨
- `postgres_data`: PostgreSQL 데이터
- `redis_data`: Redis 영속성 데이터
- `n8n_data`: n8n 워크플로우
- `./app` → `/app/app`: Flask 소스 (live reload)
- `./output` → `/app/output`: 생성물

## DB 마이그레이션

```bash
docker-compose exec app flask db migrate -m "설명"
docker-compose exec app flask db upgrade
```

## CLI 명령어

```bash
docker-compose exec app flask seed    # 기본 프롬프트 + 설정 시드
```

## 파이프라인 스텝

```
topic_confirmed → script_generated → script_translated → tts_completed → images_generated → uploaded
```

- `topic_confirmed`: 주제 확정
- `script_generated`: Claude API로 한국어 대본 생성 (JSON: narration/scene/mood)
- `script_translated`: 한국어 → 영어 번역 (scene/mood 영어 변환)
- `tts_completed`: ElevenLabs TTS (stub)
- `images_generated`: 이미지 생성 (stub)
- `uploaded`: YouTube 업로드 (stub)

## 프롬프트 구조

Redis에 저장. 각 프롬프트는 `system_prompt` + `user_prompt` 쌍.

| 이름 | 용도 | Pipeline Step |
|------|------|---------------|
| topic_generation | 주제 3개 추천 (JSON 응답) | topic_generation |
| script_short | 쇼츠 한국어 대본 (JSON: narration/scene/mood) | script_generation |
| script_long | 본편 한국어 대본 | script_generation |
| script_translate | 한→영 번역 (JSON: narration/scene/mood) | script_generation |
| scene_direction | 문단별 장면 묘사 | scene_direction |

## 대본 구조

한국어 대본 생성 시 Claude가 JSON으로 응답:
```json
{
  "paragraphs": [
    {
      "narration": "한국어 나레이션",
      "scene": "한국어 장면 묘사",
      "mood": "분위기 키워드 (한글)"
    }
  ]
}
```

영어 번역 시도 동일 구조 (영어):
```json
{
  "paragraphs": [
    {
      "narration": "English narration",
      "scene": "English scene for Midjourney",
      "mood": "English mood keyword"
    }
  ]
}
```

## ngrok

고정 도메인: `nonrepudiative-enriqueta-sparkily.ngrok-free.dev`
- Docker 컨테이너로 실행 (Flask :8000에 연결)
- 수동 실행: `C:\Users\admin\AppData\Local\ngrok\ngrok.exe http 8000 --url=nonrepudiative-enriqueta-sparkily.ngrok-free.dev`
- ngrok 종료 시 Telegram Webhook 비활성화

## Claude Code 스킬

| 명령어 | 기능 |
|---|---|
| `/docker-up` | 컨테이너 시작 |
| `/docker-down` | 컨테이너 안전 중지 (볼륨 유지) |
| `/docker-restart` | 컨테이너 재시작 |
| `/docker-status` | 컨테이너 + 볼륨 상태 확인 |
| `/docker-rebuild` | 이미지 재빌드 후 시작 |

## 개발 규칙

- 모바일 대응 필수 (Bootstrap 5 반응형)
- 한국어 대본의 scene/mood는 한글, 영어 대본은 영어
- 프롬프트 수정 시 Redis에서 삭제 후 `flask seed`로 재시드
- `flask seed`는 멱등성 보장 (기존 프롬프트는 skip)
