# 格物学术

格物学术全栈实现，覆盖前台、后台、任务处理和推广奖励
## 技术栈

- 前端：Vue 3 + Vite + Tailwind CSS
- 后端：FastAPI + SQLAlchemy
- 数据库：MySQL 8（开发环境支持自动回退 SQLite）
- 缓存队列：Redis 7 + Celery
- 部署：Docker Compose

## 已实现模块

- 手机号验证码登录（60s 冷却，错误次数锁定）
- JWT 鉴权（前台用户与后台管理员分离）
- AIGC 检测、降重复率、改写文章任务
- 文件上传校验（格式、大小、基础魔数）
- 积分扣费与失败自动退还
- 推广邀请码、邀请关系、注册奖励、充值返利
- 后台仪表盘、用户/任务/订单/推广管理接口
- Vue 前台与后台页面

## 快速启动

1. 复制环境变量
   - `cp .env.example .env`
   - 默认 `VITE_ENABLE_WECHAT_LOGIN=false`，如未接入真实微信回调请保持关闭
   - 默认 `PAYMENT_TEST_MODE=true`，表示当前为内测支付模式
2. 启动依赖（可选）
   - `docker compose up -d mysql redis`
3. 启动后端
   - `cd backend`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`
4. 启动 Celery
   - `cd backend`
   - `celery -A app.worker_tasks.celery_app worker -l info`
5. 启动前端
   - `cd frontend`
   - `npm install --ignore-scripts`
   - `npm run dev`

## 访问地址

- 前台：`http://localhost:5173`
- 后端：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

## 运维手册

- 上线、联调、配置中心填写说明见：[`docs/GO_LIVE_RUNBOOK.md`](./docs/GO_LIVE_RUNBOOK.md)

## 上线安全校验

- 当 `APP_ENV=prod` 时，后端启动会强制校验以下配置不得为默认值：
  - `JWT_SECRET`
  - `PAYMENT_SIGN_SECRET`
  - `ADMIN_INIT_PASSWORD`

## 关键接口（新增）

### 1) 支付回调（验签 + 幂等）

- `POST /api/v1/billing/callback`
- 鉴权：无需登录（支付网关回调）
- 用途：验证签名后入账积分；重复回调自动幂等忽略

请求示例：

```json
{
  "order_no": "OD202603310001",
  "user_id": 10001,
  "package_name": "入门包",
  "amount_cny": 9.9,
  "paid_at": 1774892000,
  "status": "paid",
  "provider": "wechat",
  "nonce": "nonce-001",
  "sign": "<hmac_sha256_signature>"
}
```

`curl` 示例：

```bash
curl -X POST "http://localhost:8000/api/v1/billing/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no":"OD202603310001",
    "user_id":10001,
    "package_name":"入门包",
    "amount_cny":9.9,
    "paid_at":1774892000,
    "status":"paid",
    "provider":"wechat",
    "nonce":"nonce-001",
    "sign":"<hmac_sha256_signature>"
  }'
```

预期响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "order_no": "OD202603310001",
    "status": "paid",
    "credits": 10000,
    "idempotent": false
  }
}
```

### 2) 管理端算法包上传

- `POST /api/v1/admin/algo-packages/upload`
- 鉴权：管理员 Bearer Token
- 要求：`zip` 内必须包含 `manifest.json` 和 `main.py`；上传后自动执行 smoke test

`curl` 示例：

```bash
curl -X POST "http://localhost:8000/api/v1/admin/algo-packages/upload" \
  -H "Authorization: Bearer <admin_token>" \
  -F "platform=cnki" \
  -F "function_type=dedup" \
  -F "activate=true" \
  -F "file=@./cnki_dedup_v1.0.0.zip"
```

预期响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "name": "cnki_dedup_engine",
    "version": "1.0.0",
    "platform": "cnki",
    "function_type": "dedup",
    "smoke_status": "passed"
  }
}
```

### 3) 管理端算法包激活

- `POST /api/v1/admin/algo-packages/activate`
- 鉴权：管理员 Bearer Token
- 用途：切换指定槽位（`platform + function_type`）到目标版本

请求示例：

```json
{
  "platform": "cnki",
  "function_type": "dedup",
  "version": "1.0.0"
}
```

`curl` 示例：

```bash
curl -X POST "http://localhost:8000/api/v1/admin/algo-packages/activate" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"platform":"cnki","function_type":"dedup","version":"1.0.0"}'
```

### 4) 管理端算法包查询

- `GET /api/v1/admin/algo-packages`
- 鉴权：管理员 Bearer Token
- 返回：`slots`（各槽位当前激活版本）+ `items`（上传历史）

## 工程化脚本（新增）

- 一键部署（阿里云 ECS）：
  - `bash scripts/deploy_aliyun.sh`
- 质量闸门（Linux）：
  - `bash scripts/quality_gate.sh`
- 质量闸门（Windows）：
  - `scripts\\quality_gate.ps1`
- 全链路升级手册：
  - `docs/PROJECT_EXCELLENCE_PLAYBOOK.md`
