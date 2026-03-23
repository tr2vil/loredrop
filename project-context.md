# 유튜브 자동화 채널 프로젝트 컨텍스트

> 새 Claude 세션 시작 시 이 파일 전체를 붙여넣고 "이어서 작업하자"고 하면 됩니다.

---

## 프로젝트 개요

- **목표**: 역사·미스터리 얼굴없는 유튜브 채널 자동화
- **채널**: 한국어 채널 + 영어 채널 동시 운영
- **한국어 채널**: https://www.youtube.com/channel/UCsTLq4MyJLI-wzFheNC9JmQ
- **개발자 수준**: API·자동화 자유자재
- **핵심 컨셉**: 주제 추천 → 사용자 선택 → 리서치·스크립트 → 검토 → 영상 제작 → 최종 승인 → 업로드

---

## 자동화 파이프라인

### Stage 1: 주제 추천 (매일 오전, 자동)
- pytrends + feedparser + Claude로 트렌드 기반 주제 3~5개 생성
- 텔레그램 Bot으로 추천안 전송
- 사용자가 하나 선택 or 직접 입력

### Stage 2: 리서치 + 스크립트 (자동)
- Claude API로 선택된 주제 자료조사 + 한글 스크립트 작성
- 이메일(channel.loredrop@gmail.com)로 대본 전송
- 텔레그램으로 "대본 전송 완료" 알림

### Stage 3: 검토 후 영상 제작 (반자동)
- 사용자가 대본 검토/승인 (텔레그램 버튼 or 이메일 회신)
- 승인 시 자동 시작:
  - Claude API로 영어 현지화
  - ElevenLabs로 한/영 음성 생성
  - Pictory(→FFmpeg)로 영상 조립

### Stage 4: 최종 확인 + 퍼블리시 (반자동)
- 완성 영상 링크 텔레그램 알림
- 사용자 최종 확인 → 버튼 클릭
- YouTube API로 자동 업로드

### 체크포인트 (사용자 개입 2회)
1. **주제 선택** — Stage 1 후
2. **최종 영상 승인** — Stage 4에서 퍼블리시 전

### 추가 필요 서비스
- 텔레그램 Bot (BotFather에서 토큰 생성)
- Gmail App Password 또는 SendGrid
- n8n Webhook + Wait 노드 (사용자 응답 대기)

---

## 기술 스택

| 역할 | 도구 | 비고 |
|---|---|---|
| 스크립트 생성 | Claude API (claude-sonnet-4-6) | 한국어·영어 현지화 포함 |
| 음성 생성 | ElevenLabs API (eleven_multilingual_v2) | 한/영 별도 목소리 |
| 영상 조립 | Pictory API → 이후 FFmpeg | MVP는 Pictory |
| 업로드 자동화 | YouTube Data API v3 | OAuth2 인증 |
| 파이프라인 오케스트레이션 | n8n (self-hosted, Docker) | |
| 콘텐츠 DB | Airtable | 주제 관리·성과 추적 |
| 성과 대시보드 | Streamlit + YouTube Analytics API | |
| 주제 발굴 | pytrends + feedparser + Claude | 자동 트렌드 수집 |

---

## 30일 플랜 진행 현황

### W1: 기반 구축 (1~7일) ← 현재 여기
- [x] D1: 니치 세분화 결정 — 역사·미스터리 (한국어=세계 미스터리, 영어=한국 역사, 세계 미스터리)
- [ ] **D2: YouTube Data API v3 세팅** ← 다음 작업
- [ ] **D3: Claude API 스크립트 자동 생성 파이프라인** ← 다음 작업
- [ ] D4: ElevenLabs API 보이스 파이프라인
- [ ] D5: 영상 조립 파이프라인
- [ ] D6: 첫 영상 제작 & 썸네일
- [ ] D7: 첫 업로드 + YouTube API 업로드 자동화

### W2: 이중 언어 자동화 (8~14일)
- [ ] D8: 한→영 현지화 파이프라인
- [ ] D9: n8n 전체 워크플로우 구축
- [ ] D10: Airtable 콘텐츠 DB 연동
- [ ] D11: 영어 채널 개설 + 첫 영상
- [ ] D12: YouTube Analytics API 자동 수집
- [ ] D13: Shorts 자동 생성 (FFmpeg)
- [ ] D14: 2주 파이프라인 점검

### W3: 콘텐츠 엔진 + 수익화 (15~21일)
- [ ] D15: 배치 제작 스케줄러 (주 1회 → 7일치 자동 생성)
- [ ] D16: 제휴 마케팅 설정
- [ ] D17: 시리즈 기획
- [ ] D18: 댓글 분석 자동화 (다음 주제 발굴)
- [ ] D19: 디지털 제품 기획 (Gumroad)
- [ ] D20: Streamlit 대시보드
- [ ] D21: 3주 성과 점검

### W4: 스케일링 (22~30일)
- [ ] D22: LLM 기반 주제 자동 발굴 에이전트
- [ ] D23: 품질 자동 검증 레이어
- [ ] D24: 영어 채널 SEO 키워드 자동화
- [ ] D25: Shorts 전용 3번째 채널 기획
- [ ] D26: 스폰서십 미디어킷 자동 생성
- [ ] D27: 전체 파이프라인 SOP 문서화
- [ ] D28: 30일 ROI 분석
- [ ] D29: 파이프라인 오픈소스/판매 검토
- [ ] D30: 90일 로드맵 수립

---

## 프로젝트 디렉토리 구조

```
loredrop/
├── src/                        # Python 소스 코드
│   ├── config.py               #   환경변수·설정 로딩
│   ├── api/                    #   n8n이 호출할 API 엔드포인트
│   │   └── routes.py           #     FastAPI 라우트 정의
│   ├── pipeline/               #   파이프라인 비즈니스 로직 (api → pipeline 호출)
│   │   ├── trend.py            #     Stage 1: 트렌드 수집
│   │   ├── idea_bank.py        #     Stage 1: 주제 아이디어 관리
│   │   ├── script_gen.py       #     Stage 2: Claude API 스크립트 생성
│   │   ├── localizer.py        #     Stage 3: 한→영 현지화
│   │   ├── voice_gen.py        #     Stage 3: ElevenLabs TTS
│   │   ├── video_gen.py        #     Stage 3: 영상 조립 (Pictory/FFmpeg)
│   │   ├── uploader.py         #     Stage 4: YouTube 업로드
│   │   └── analytics.py        #     성과 수집·분석
│   ├── notify/                 #   알림 레이어
│   │   ├── telegram.py         #     텔레그램 봇 (추천·승인 알림)
│   │   └── email.py            #     이메일 발송 (대본 전송)
│   └── store/                  #   외부 저장소 연동
│       └── airtable.py         #     Airtable 콘텐츠 DB
│
├── web/                        # 관리 웹서비스 (대시보드·관리 UI)
│   ├── app.py                  #   웹앱 진입점
│   ├── routes/                 #   페이지 라우트
│   ├── templates/              #   HTML 템플릿
│   └── static/                 #   정적 파일 (CSS, JS)
│
├── output/                     # 생성물 저장 (git 제외)
│   ├── scripts/                #   생성된 대본
│   ├── audio/                  #   TTS 음성 파일
│   └── videos/                 #   완성 영상
│
├── tests/                      # 테스트 코드
├── Dockerfile                  # 앱 컨테이너 이미지
├── docker-compose.yml          # app + n8n 컨테이너 구성
├── .env                        # API 키 (git 제외)
├── .gitignore
├── requirements.txt
└── project-context.md
```

### 호출 흐름

```
n8n (오케스트레이터, 별도 컨테이너)
  ↓ HTTP 요청
src/api/routes.py (엔드포인트)
  ↓ 함수 호출
src/pipeline/* (비즈니스 로직)
  ├→ src/store/* (데이터 저장)
  └→ src/notify/* (알림 발송)
```

### 폴더별 역할

| 폴더 | 역할 | 비고 |
|---|---|---|
| `src/api/` | n8n → 앱 연결 지점. HTTP 엔드포인트 노출 | FastAPI 사용 |
| `src/pipeline/` | 핵심 비즈니스 로직. 주제 발굴부터 업로드까지 전 단계 | api가 호출 |
| `src/notify/` | 텔레그램·이메일 알림. 파이프라인 전반에서 공통 사용 | |
| `src/store/` | 외부 저장소(Airtable 등) 연동 | |
| `web/` | 관리 대시보드. src/와 별도 관심사로 분리 | 나중에 별도 컨테이너 가능 |
| `output/` | 파이프라인 산출물 저장. .gitignore 처리됨 | |
| `tests/` | 단위·통합 테스트 | |

---

## .env 파일 구조 (키 목록)

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

# Pictory (영상 조립)
PICTORY_API_KEY=

# Telegram Bot
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# n8n
N8N_AUTH_USER=admin
N8N_AUTH_PASSWORD=
```

---

## 이어서 작업할 때 클로드에게 요청 예시

### D2 작업 시작:
```
D2 작업 시작. YouTube Data API v3로 경쟁 채널 상위 영상을
자동 수집하는 완성 코드 만들어줘.
API 키는 .env에서 읽어오고, 결과는 Airtable에 저장하는 버전.
```

### D3 작업 시작:
```
D3 작업 시작. Claude API로 역사·미스터리 유튜브 스크립트를
생성하는 script_gen.py 완성 코드 만들어줘.
한국어/영어 선택 가능하고, 프롬프트 최적화 포함.
```

### 특정 파일 작업:
```
pipeline/voice_gen.py 작업. ElevenLabs API로
텍스트→MP3 변환하는 완성 코드. .env에서 키 읽기.
```

---

## 주요 결정 사항

- MVP 영상 조립 도구: Pictory API (나중에 FFmpeg으로 전환)
- n8n 호스팅: Docker 로컬 → 이후 Railway 배포
- 스크립트 길이: 8~10분 (한국어 1,800~2,200자)
- 발행 스케줄: 주 3~4편/채널 목표
- 수익화 우선순위: 제휴 마케팅 → AdSense → 디지털 제품 → 스폰서십