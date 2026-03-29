---
name: docker-down
description: Docker 컨테이너 중지 (볼륨 유지, 데이터 안전)
disable-model-invocation: true
---

Docker 컨테이너를 안전하게 중지한다 (ngrok 포함).

1. `docker-compose down` 실행 (절대 `-v` 플래그 사용 금지 - 볼륨 삭제됨)
2. ngrok 터널도 함께 종료됨 → Telegram Webhook 비활성화 알림
3. `docker-compose ps` 로 중지 확인
4. 상태 보고
