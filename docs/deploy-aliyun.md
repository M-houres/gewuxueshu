# 格物学术 阿里云部署说明

## 已准备文件

- `docker-compose.prod.yml`
- `.env.prod.example`
- `frontend/Dockerfile`
- `frontend/nginx.conf`

## 部署前准备

1. 阿里云 ECS 安装 Docker 与 Docker Compose。
2. 安全组至少放行 `80`，如果后面接 HTTPS 再放行 `443`。
3. 域名解析到 ECS 公网 IP。

## 服务器部署步骤

```bash
git clone https://github.com/M-houres/gewuxueshu.git
cd gewuxueshu
cp .env.prod.example .env.prod
```

然后修改 `.env.prod` 中至少这些值：

- `JWT_SECRET`
- `MYSQL_PASSWORD`
- `ADMIN_INIT_PASSWORD`

以下配置可以部署后在后台再填：

- 支付参数
- 短信参数
- 微信登录参数
- 大模型参数

## 启动

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 更新

```bash
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 当前生产拓扑

- `frontend`
  - Nginx 托管前端静态文件
  - `/api/` 反向代理到 `backend:8000`
- `backend`
  - FastAPI 主服务
- `worker`
  - Celery 异步任务
- `mysql`
  - 生产数据库
- `redis`
  - 缓存与 Celery broker

## 注意事项

- 生产环境必须 `APP_ENV=prod`
- 生产环境必须 `DB_FALLBACK_SQLITE=false`
- 首次启动会自动执行 Alembic 迁移
- 算法包、上传文件、输出结果已经通过 Docker volume 持久化
- 邀请链接默认按当前请求域名生成，不再强依赖 `FRONTEND_BASE_URL`
- 支付回调签名优先使用后台支付配置中的 `callback_secret`
- 如果需要 HTTPS，建议前面再挂阿里云 SLB/Nginx/Caddy
