---
name: docker-down
description: Docker 컨테이너 중지 + ngrok 종료 (볼륨 유지, 데이터 안전)
disable-model-invocation: true
---

Docker 컨테이너를 안전하게 중지하고 ngrok도 종료한다.

1. `docker-compose down` 실행 (절대 `-v` 플래그 사용 금지 - 볼륨 삭제됨)
2. ngrok 프로세스 종료: `taskkill //F //IM ngrok.exe 2>/dev/null || true`
3. `docker-compose ps` 로 중지 확인
4. Telegram Webhook 비활성화 알림
5. 상태 보고
