---
name: docker-restart
description: Docker 컨테이너 재시작 (데이터 안전)
disable-model-invocation: true
---

Docker 컨테이너를 재시작한다 (ngrok 포함).

1. `docker-compose restart` 실행 (app, postgres, redis, n8n, ngrok 모두 재시작)
2. `docker-compose ps` 로 상태 확인
3. 각 서비스(app, postgres, redis, n8n, ngrok) 상태 보고
4. ngrok 터널 상태 확인: `docker-compose logs --tail=10 ngrok` 로 터널 재연결 확인
