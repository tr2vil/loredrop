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

## 서비스 접속
- App: http://localhost:8000
- n8n: http://localhost:5678
