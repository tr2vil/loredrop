---
name: docker-status
description: Docker 컨테이너 및 볼륨 상태 확인
disable-model-invocation: true
---

Docker 상태를 확인한다 (ngrok 포함).

1. `docker-compose ps` 로 컨테이너 상태 확인
2. `docker volume ls | grep loredrop` 로 볼륨 존재 확인
3. ngrok 터널 상태 확인: `docker-compose logs --tail=10 ngrok` 로 터널 URL 및 연결 상태 확인
4. 각 서비스(app, postgres, redis, n8n, ngrok) 상태와 볼륨 현황 보고
