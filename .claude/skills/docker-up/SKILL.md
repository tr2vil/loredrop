---
name: docker-up
description: Docker 컨테이너 시작 + ngrok 터널 연결
disable-model-invocation: true
---

Docker 컨테이너를 시작하고 ngrok 터널을 연결한다.

1. `docker-compose up -d` 실행 (app, postgres, redis, n8n 시작)
2. `docker-compose ps` 로 상태 확인
3. ngrok 수동 실행 (Docker ngrok 컨테이너는 AUTHTOKEN 문제로 사용하지 않음):
   ```bash
   /c/Users/admin/AppData/Local/ngrok/ngrok.exe http 8000 --url=nonrepudiative-enriqueta-sparkily.ngrok-free.dev &>/dev/null &
   ```
4. 3초 대기 후 ngrok 터널 상태 확인: `curl -s http://localhost:4040/api/tunnels` 로 연결 확인
5. 상태 보고 (각 서비스 + ngrok 터널 URL)
