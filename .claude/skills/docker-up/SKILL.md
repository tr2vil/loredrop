---
name: docker-up
description: Docker 컨테이너 시작 (데이터 안전)
disable-model-invocation: true
---

Docker 컨테이너를 시작한다 (ngrok 포함).

1. `docker-compose up -d` 실행 (app, postgres, redis, n8n, ngrok 모두 시작)
2. `docker-compose ps` 로 상태 확인
3. 각 서비스(app, postgres, redis, n8n, ngrok) 상태를 보고
4. ngrok 터널 상태 확인: `docker-compose logs --tail=10 ngrok` 로 터널 URL 확인
