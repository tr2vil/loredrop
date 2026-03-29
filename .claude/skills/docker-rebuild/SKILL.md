---
name: docker-rebuild
description: Docker 이미지 재빌드 후 컨테이너 시작 (데이터 안전)
disable-model-invocation: true
---

Docker 이미지를 재빌드하고 컨테이너를 시작한다 (ngrok 포함).

1. `docker-compose down` 실행 (절대 `-v` 플래그 사용 금지)
2. `docker-compose up -d --build` 실행 (ngrok 포함 전체 서비스 시작)
3. `docker-compose ps` 로 상태 확인
4. 각 서비스(app, postgres, redis, n8n, ngrok) 상태 보고
5. ngrok 터널 상태 확인: `docker-compose logs --tail=10 ngrok` 로 터널 URL 확인
