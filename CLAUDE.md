# LoreDrop - Development Guide

## Docker 컨테이너 관리

### 안전한 명령어 (데이터 유지)
```bash
docker-compose up -d          # 컨테이너 시작
docker-compose down           # 컨테이너 중지 및 제거 (볼륨 유지)
docker-compose restart        # 컨테이너 재시작
docker-compose up -d --build  # 이미지 재빌드 후 시작
```

### 위험한 명령어 (데이터 삭제됨)
```bash
docker-compose down -v        # 볼륨까지 삭제 - n8n 워크플로우 전부 날아감
docker volume rm n8n_data     # n8n 볼륨 직접 삭제
```

### 볼륨 구조
- `n8n_data` → `/home/node/.n8n` : n8n 워크플로우, 크레덴셜, 설정 저장
- `./output` → `/app/output` : 생성물 (bind mount, 로컬에 직접 저장)

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

Telegram Webhook은 HTTPS URL이 필수이므로, 로컬 개발 환경에서는 ngrok으로 터널링한다.

### 설치 경로
`C:\Users\admin\AppData\Local\ngrok\ngrok.exe`

### 실행
```bash
ngrok http 5678
```

### 고정 도메인 사용 (URL 변경 방지)
```bash
ngrok http 5678 --url=nonrepudiative-enriqueta-sparkily.ngrok-free.dev
```
고정 도메인: `nonrepudiative-enriqueta-sparkily.ngrok-free.dev`
관리: https://dashboard.ngrok.com/domains

### ngrok 실행 후 필수 작업
1. 터미널에 표시된 `https://xxxx.ngrok-free.app` URL 복사
2. `docker-compose.yml`의 `WEBHOOK_URL`을 해당 URL로 변경
3. `docker-compose up -d n8n` 으로 n8n 재시작 (볼륨 유지됨, 워크플로우 안전)

### 주의사항
- ngrok 종료 시 터널 URL이 무효화되어 Telegram Webhook이 작동하지 않음
- 무료 플랜: 재시작마다 URL 변경 (고정 도메인 1개 무료 제공)
- n8n 작업 중에는 ngrok을 항상 실행 상태로 유지할 것

## 서비스 접속
- App: http://localhost:8000
- n8n: http://localhost:5678
- n8n (외부): https://nonrepudiative-enriqueta-sparkily.ngrok-free.dev
- ngrok 대시보드: http://localhost:4040
