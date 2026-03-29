# LoreDrop

YouTube Shorts 영상 제작 자동화 파이프라인.
한국 역사/문화 이야기를 영어권 시청자에게 전달하는 페이스리스 채널 "LoreDrop"의 콘텐츠 제작 도구.

## 주요 기능

- **주제 추천**: Claude AI가 매일 3개 주제 추천 → Telegram으로 알림/선택
- **대본 생성**: 한국어 구조화된 대본 (나레이션 + 장면묘사 + 분위기) → 영어 번역
- **TTS 음성**: ElevenLabs API로 문단별 음성 생성 (예정)
- **이미지 생성**: Midjourney로 장면별 이미지 생성 (예정)
- **YouTube 업로드**: 편집 완료 영상을 채널에 업로드 (예정)

## Production 파이프라인

```
1. Confirm Topic     → 주제 확정
2. Generate Script   → 한국어 대본 생성 (scene/mood 포함) → 검수/수정
3. Translate Script  → 영어 번역 (scene/mood 영어 변환)
4. Generate TTS      → 영어 대본으로 음성 생성
5. Generate Images   → 장면 묘사로 이미지 생성
6. Upload            → 편집 완료 영상 YouTube 업로드
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Flask + Jinja2 + Gunicorn |
| Frontend | jQuery + Bootstrap 5 |
| Database | PostgreSQL 16 |
| Cache/Settings | Redis 7 |
| AI | Claude API (Anthropic) |
| TTS | ElevenLabs API |
| Container | Docker Compose (5 services) |
| Tunnel | ngrok (Telegram webhook용) |

## 시작하기

### 사전 요구사항

- Docker & Docker Compose
- `.env` 파일 설정 (API 키)

### 실행

```bash
# 컨테이너 시작
docker-compose up -d

# DB 마이그레이션 (최초 1회)
docker-compose exec app flask db upgrade

# 기본 프롬프트/설정 시드 (최초 1회)
docker-compose exec app flask seed
```

### 접속

- **Web UI**: http://localhost:8000
- **n8n**: http://localhost:5678
- **외부 접속**: https://nonrepudiative-enriqueta-sparkily.ngrok-free.dev

### 환경변수 (.env)

```env
# Claude API
ANTHROPIC_API_KEY=

# Telegram Bot
TELEGRAM_TOKEN=
TELEGRAM_CHATID=

# ElevenLabs TTS
ELEVENLABS_API_KEY=
ELEVENLABS_KO_VOICE_ID=
ELEVENLABS_EN_VOICE_ID=

# ngrok
NGROK_DOMAIN=
NGROK_AUTHTOKEN=

# (자동 설정 - docker-compose.yml에서 주입)
# DATABASE_URL=postgresql://loredrop:loredrop@postgres:5432/loredrop
# REDIS_URL=redis://redis:6379/0
```

## 웹 UI 메뉴

| 메뉴 | 기능 |
|------|------|
| Dashboard | 요약/통계 |
| Topics | 주제 추천/선택 관리 |
| Production | 영상 제작 파이프라인 실행/모니터링 |
| Prompts | AI 프롬프트 관리 (system + user) |
| Settings | TTS/이미지/일반 설정 |
| n8n | n8n 워크플로우 접근 |

## Telegram 연동

- 매일 설정된 시각에 3개 주제 추천 메시지 발송
- 인라인 버튼으로 주제 선택 / 재생성 / 직접 입력
- ngrok 터널을 통해 webhook 수신

