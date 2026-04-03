# 格物学术 上线运维手册

适用对象：
- 运营负责人
- 部署人员
- 测试联调人员

目标：
- 把“配置中心怎么填、哪些环境变量必须改、什么状态能上线”说清楚
- 尽量避免“页面能打开，但支付/短信/微信登录实际不能用”

## 1. 上线前总检查

满足以下条件后，再进入正式上线：

1. `APP_ENV=prod`
2. `.env` 中以下值都不是默认值
   - `JWT_SECRET`
   - `PAYMENT_SIGN_SECRET`
   - `ADMIN_INIT_PASSWORD`
3. MySQL、Redis、Celery 正常启动
4. 前端构建通过
5. 后端测试通过
6. 后台配置中心的 5 个分类都检查过
   - 大模型配置
   - 支付配置
   - 计费配置
   - 登录配置
   - 推广规则配置

## 2. 必改环境变量

以下变量必须在正式环境改掉：

```env
APP_ENV=prod
JWT_SECRET=请替换为高强度随机字符串
PAYMENT_SIGN_SECRET=请替换为高强度随机字符串
ADMIN_INIT_PASSWORD=请替换为强密码
FRONTEND_BASE_URL=https://你的前端域名
VITE_API_BASE_URL=https://你的后端域名/api/v1
```

建议同时确认：

```env
PAYMENT_TEST_MODE=false
VITE_PAYMENT_TEST_MODE=false
VITE_ENABLE_WECHAT_LOGIN=true
```

说明：
- 如果还没接真实支付，请不要把 `PAYMENT_TEST_MODE` 改成 `false`
- 如果还没接真实微信登录，请不要把 `VITE_ENABLE_WECHAT_LOGIN` 改成 `true`

## 3. 服务启动顺序

推荐顺序：

1. 启动 MySQL
2. 启动 Redis
3. 启动后端 API
4. 启动 Celery Worker
5. 启动前端

本项目依赖：
- API 负责登录、下单、任务管理、后台接口
- Celery 负责文章处理、奖励发放、失败重试
- Redis 负责验证码、限流、队列

如果 Celery 没启动：
- 任务可能一直停留在排队中
- 推广奖励异步发放可能不执行

## 4. 配置中心填写说明

原则：
- 配置中心是运营主控面板
- 同类配置优先读取数据库配置，其次才回退到环境变量
- 改完后建议立刻做一轮联调

### 4.1 大模型配置

需要填写：
- `enabled`
- `provider`
- `base_url`
- `model`
- `api_key`
- `timeout_seconds`

建议：
- 未准备好真实大模型时，先关闭 `enabled`
- 关闭后系统会优先走算法模式或降级逻辑

上线确认：
- 保存后在配置中心 readiness 中看到“大模型已就绪”或明确 warning

### 4.2 支付配置

需要重点确认：
- `provider`
- `test_mode`
- `app_id`
- `merchant_id`
- `merchant_serial_no`
- `merchant_private_key_pem`
- `api_v3_key`
- `notify_url`
- `callback_secret`

运营理解：
- `test_mode=true`
  - 前端显示测试支付提示
  - 可用于本地或内测联调
- `test_mode=false`
  - 表示准备走正式支付能力

上线确认：
- `notify_url` 必须是正式 HTTPS 地址
- `api_v3_key` 必须是 32 位
- 支付页面不再显示“内测支付模式”

### 4.3 计费配置

需要填写：
- `aigc_rate`
- `dedup_rate`
- `rewrite_rate`

运营理解：
- 这 3 个值就是每字符消耗的积分
- 保存后，新提交任务立即按新规则计费

建议做法：
- 每次调整后，用一份小文档提交 3 个任务，核对扣费是否符合预期

### 4.4 登录配置

可选模式：
- 短信登录
- 微信登录
- 开发调试验证码

生产建议：
- 至少保证短信登录或微信登录中有一种可用
- 不建议在生产环境开启调试验证码

短信模式重点字段：
- `sms_provider`
- `sms_gateway_url`
- `sms_api_key`
- `sms_template_id`
- `sms_sign_name`

微信模式重点字段：
- `wechat_login_enabled`
- `wechat_app_id`
- `wechat_app_secret`
- `wechat_redirect_uri`

上线确认：
- 点“发送验证码”时用户手机能真实收到
- 微信扫码后能真正登录，不走 mock

### 4.5 推广规则配置

需要填写：
- `register_inviter_credits`
- `register_invitee_bonus`
- `first_pay_ratio`
- `recurring_ratio`
- `ip_limit_24h`

运营理解：
- `register_inviter_credits`
  - 邀请人带来注册后，直接奖励多少积分
- `register_invitee_bonus`
  - 被邀请人注册后，赠送多少积分
- `first_pay_ratio`
  - 被邀请人首充时，邀请人拿首充积分的多少比例
- `recurring_ratio`
  - 被邀请人后续每次充值，邀请人持续拿多少比例
- `ip_limit_24h`
  - 同一 IP 24 小时最多允许多少次注册，超过后风控拦截

## 5. 游客模式边界

当前产品策略：
- 可以游客浏览
  - 功能页
  - 套餐页
  - 平台选择
  - 价格和说明
- 必须登录后才能做
  - 提交任务
  - 创建支付订单
  - 下载任务结果
  - 查看个人记录
  - 查看积分流水
  - 查看推广个人数据

如果你想验证游客模式是否正常：

1. 清空浏览器登录态
2. 打开 `/app/detect`
3. 确认能浏览页面但提交时才跳登录
4. 打开 `/app/buy`
5. 确认能看套餐，但创建订单时才要求登录

## 6. 上线联调清单

建议按这个顺序做：

1. 手机验证码登录
   - 发送验证码
   - 登录成功
2. 微信扫码登录
   - 二维码可展示
   - 扫码后可回到系统
3. 购买积分
   - 下单
   - 支付
   - 积分到账
4. 提交 AIGC 检测
   - 结果生成
   - 历史记录可查看
5. 提交降重 / 改写
   - 主文件处理完成
   - 结果文件可下载
6. 邀请注册
   - 邀请码有效
   - 奖励到账
7. 后台检查
   - 用户页有记录
   - 任务页可查看详情
   - 配置审计日志可追踪

## 7. 常见异常排查

### 7.1 用户收不到验证码

先检查：
- 登录配置里的 `sms_provider`
- `sms_gateway_url`
- `sms_api_key`
- 模板和签名
- Redis 是否可用

再检查：
- 是否还停留在测试环境
- 是否触发 IP 限流或手机号冷却

### 7.2 任务一直排队

重点检查：
- Celery Worker 是否运行
- Redis 是否连接正常
- Worker 日志是否报错

### 7.3 支付页面可以打开但不能到账

重点检查：
- `payment.test_mode`
- `notify_url`
- `callback_secret`
- 支付配置是否完整

### 7.4 微信扫码页有二维码但扫完没登录

重点检查：
- `wechat_login_enabled`
- `wechat_app_id`
- `wechat_app_secret`
- `wechat_redirect_uri`
- 前端 `VITE_ENABLE_WECHAT_LOGIN`

## 8. 回滚建议

如果线上联调出问题，优先回滚以下内容：

1. 配置中心最近一次变更
   - 先看配置审计日志
   - 找到最近修改人和修改字段
2. 支付配置
   - 先切回测试模式，避免误收款
3. 登录配置
   - 先保留最稳定的一种登录方式
4. 大模型配置
   - 出现异常时先关闭 LLM，走算法降级

## 9. 建议保留的上线证据

建议每次上线都保留：

1. 前端构建成功记录
2. 后端测试通过记录
3. 配置中心截图
4. 一次真实登录截图
5. 一次真实下单截图
6. 一次任务完成截图
7. 一次后台审计日志截图

这样后面排问题时，不需要再猜“当时到底配了什么”。
