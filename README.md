# LoreDrop

역사/미스터리 유튜브 채널 자동화 파이프라인

## Overview

주제 발굴부터 영상 업로드까지 전 과정을 자동화하는 시스템입니다.
한국어/영어 채널을 동시에 운영하며, n8n이 워크플로우를 오케스트레이션하고 이 앱이 핵심 비즈니스 로직을 API로 제공합니다.

## Pipeline Stages

| Stage | 설명 | 사용자 개입 |
|---|---|---|
| **Stage 1** | 트렌드 수집 → 주제 추천 → 텔레그램 알림 | 주제 선택 |
| **Stage 2** | Claude API로 스크립트 생성 → 이메일 발송 | - |
| **Stage 3** | 한→영 현지화 → TTS 음성 → 영상 조립 | - |
| **Stage 4** | 완성 영상 알림 → YouTube 업로드 | 최종 승인 |

## Tech Stack

- **스크립트 생성**: Claude API
- **음성 생성**: ElevenLabs API
- **영상 조립**: Pictory API → FFmpeg
- **업로드**: YouTube Data API v3
- **오케스트레이션**: n8n (별도 컨테이너)
- **콘텐츠 DB**: Airtable
- **알림**: Telegram Bot, Email

## Project Structure

```
src/
├── api/            # n8n이 호출할 API 엔드포인트 (FastAPI)
├── pipeline/       # 비즈니스 로직 (트렌드 → 스크립트 → TTS → 영상 → 업로드)
├── notify/         # 알림 (텔레그램, 이메일)
└── store/          # 외부 저장소 연동 (Airtable)

web/                # 관리 대시보드
output/             # 생성물 (scripts, audio, videos)
```

**호출 흐름:**
```
n8n → src/api/ → src/pipeline/ → src/store/
                               → src/notify/
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- `.env` 파일에 API 키 설정

### Run

```bash
docker-compose up -d
```

- App: `http://localhost:8000`
- n8n: `http://localhost:5678`

### Environment Variables

```env
# Anthropic
ANTHROPIC_API_KEY=

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_KO_VOICE_ID=
ELEVENLABS_EN_VOICE_ID=

# YouTube (OAuth2)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_KO_CHANNEL_ID=
YOUTUBE_EN_CHANNEL_ID=

# Airtable
AIRTABLE_API_KEY=
AIRTABLE_BASE_ID=
AIRTABLE_TABLE_NAME=

# Pictory
PICTORY_API_KEY=

# Telegram Bot
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# n8n
N8N_AUTH_USER=admin
N8N_AUTH_PASSWORD=
```

## License

Private
