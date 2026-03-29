# LoreDrop - Development Guide

## 아키텍처 개요

Flask 기반 YouTube 영상 제작 자동화 파이프라인.

```
[ngrok] → [Flask :8000] → PostgreSQL / Redis
                ├── Dashboard, Topics, Pipeline, Prompts, Settings
                ├── Telegram Bot API (양방향)
                └── n8n (iframe 참고용, :5678)
```

## 기술 스택
- **Backend**: Flask + Jinja2 + Gunicorn
- **Frontend**: jQuery + Bootstrap 5
- **Database**: PostgreSQL 16 (topics, scripts, pipeline)
- **Cache/Settings**: Redis 7 (prompts, settings, pipeline status)
- **Container**: Docker Compose (5 services)
- **AI**: Claude API (Anthropic)
- **TTS**: ElevenLabs API
- **Tunnel**: ngrok (Flask 앱에 연결)

## Docker 컨테이너 관리

### 서비스 구성 (5개)
| 서비스 | 포트 | 역할 |
|--------|------|------|
| app | 8000 | Flask 웹 앱 |
| postgres | 5432 | 데이터베이스 |
| redis | 6379 | 캐시/설정 |
| n8n | 5678 | 워크플로우 (참고용) |
| ngrok | - | HTTPS 터널 |

### 안전한 명령어 (데이터 유지)
```bash
docker-compose up -d          # 컨테이너 시작
docker-compose down           # 컨테이너 중지 및 제거 (볼륨 유지)
docker-compose restart        # 컨테이너 재시작
docker-compose up -d --build  # 이미지 재빌드 후 시작
```

### 위험한 명령어 (데이터 삭제됨)
```bash
docker-compose down -v        # 볼륨까지 삭제 - DB, n8n 워크플로우 전부 날아감
docker volume rm postgres_data  # PostgreSQL 데이터 삭제
docker volume rm n8n_data       # n8n 볼륨 직접 삭제
```

### 볼륨 구조
- `postgres_data` : PostgreSQL 데이터
- `redis_data` : Redis 영속성 데이터
- `n8n_data` → `/home/node/.n8n` : n8n 워크플로우, 크레덴셜
- `./app` → `/app/app` : Flask 소스 (개발 시 live reload)
- `./output` → `/app/output` : 생성물 (scripts/audio/images/videos)

## DB 마이그레이션

```bash
# 컨테이너 내부에서 실행
docker-compose exec app flask db init      # 최초 1회
docker-compose exec app flask db migrate -m "message"
docker-compose exec app flask db upgrade
```

## 프로젝트 구조

```
app/
├── __init__.py          # create_app() 팩토리
├── config.py            # 환경 설정
├── extensions.py        # db, redis, migrate
├── models/              # SQLAlchemy 모델
├── blueprints/          # Flask 블루프린트 (라우트)
├── services/            # 비즈니스 로직
│   ├── ai/              # Claude API
│   ├── content/         # 주제/스크립트 서비스
│   ├── media/           # TTS/이미지/영상
│   ├── distribution/    # YouTube/Telegram
│   └── system/          # 스케줄러/설정
├── pipeline/            # 파이프라인 오케스트레이션
├── templates/           # Jinja2 HTML
└── static/              # CSS, JS
```

## Claude Code 스킬 (슬래시 명령어)

| 명령어 | 기능 |
|---|---|
| `/docker-up` | 컨테이너 시작 |
| `/docker-down` | 컨테이너 안전 중지 (볼륨 유지) |
| `/docker-restart` | 컨테이너 재시작 |
| `/docker-status` | 컨테이너 + 볼륨 상태 확인 |
| `/docker-rebuild` | 이미지 재빌드 후 시작 |

모든 스킬은 `-v` 플래그 사용을 금지하여 볼륨 삭제를 방지한다.

## ngrok (HTTPS 터널)

ngrok은 Docker 컨테이너로 실행되며, Flask 앱(:8000)에 연결된다.
고정 도메인: `nonrepudiative-enriqueta-sparkily.ngrok-free.dev`

### 수동 실행 (Docker 외부)
```bash
C:\Users\admin\AppData\Local\ngrok\ngrok.exe http 8000 --url=nonrepudiative-enriqueta-sparkily.ngrok-free.dev
```

### 주의사항
- ngrok 종료 시 Telegram Webhook이 작동하지 않음
- `.env`의 `NGROK_AUTHTOKEN`을 설정해야 Docker ngrok 컨테이너가 작동함

## 서비스 접속
- App: http://localhost:8000
- n8n: http://localhost:5678
- 외부 접속: https://nonrepudiative-enriqueta-sparkily.ngrok-free.dev
