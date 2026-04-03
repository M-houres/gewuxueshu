# Aliyun ECS Quick Start

This file is for browser terminal copy-paste deployment.

## 1) First install (one command)

```bash
curl -fsSL https://raw.githubusercontent.com/M-houres/gewuxueshu/main/scripts/deploy_aliyun.sh | sudo bash
```

## 2) Update to latest main

```bash
cd /opt/gewuxueshu && git pull --ff-only origin main && sudo bash scripts/deploy_aliyun.sh
```

## 3) Rollback if latest deploy fails

```bash
sudo bash /opt/gewuxueshu/scripts/deploy_aliyun_rollback.sh
```

## 4) Health checks

```bash
curl -fsS http://127.0.0.1/api/v1/health
sudo docker compose --env-file /opt/gewuxueshu/.env.prod -f /opt/gewuxueshu/docker-compose.prod.yml ps
```

## 5) Common logs

```bash
sudo docker compose --env-file /opt/gewuxueshu/.env.prod -f /opt/gewuxueshu/docker-compose.prod.yml logs --tail=200
```
