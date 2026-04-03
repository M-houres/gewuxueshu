# 格物学术 多端架构预留说明

## 当前目标

项目当前已上线 Web 端，后续会接入微信小程序端。现阶段后端接口保持端无关，前端仅负责当前 Web UI。

## 已落地预留

### 1. 接口层

- 后端继续只提供统一业务 API，不在接口返回结构中写死 Web 专属字段。
- 前端通过 `X-Client-Source` 请求头声明来源，当前 Web 默认发送 `web`，后续小程序发送 `miniprogram` 即可复用同一套接口。

### 2. 认证体系

- 登录态继续基于 Token/JWT，不依赖 Cookie/Session。
- 微信用户模型已预留：
  - `wechat_openid_web`
  - `wechat_openid_mp`
  - `wechat_unionid`
- 当前网页扫码登录走 `scene=web`，后续小程序授权登录可直接走 `scene=miniprogram`，无需重构用户主表或登录主链路。

### 3. 支付体系

- 订单、支付回调、积分到账逻辑与端无关。
- 小程序接微信支付时，只需要新增前端调起支付方式，后端订单状态更新、回调验签、积分发放、推广返佣逻辑可直接复用。

### 4. 数据体系

以下核心表已新增 `source` 字段，用于区分数据来源：

- `users`
- `credit_transactions`
- `orders`
- `tasks`
- `referral_relations`
- `referral_rewards`

当前约定值：

- `web`
- `miniprogram`
- `admin`
- `system`

### 5. 文件上传

- 当前后端仍支持 `.docx` / `.pdf` / `.txt`。
- 上传校验与处理逻辑保留在接口层，后续小程序如果需要走文件 URL、中转上传或受限格式适配，可以在不改业务核心逻辑的前提下扩展。

### 6. 业务与 UI 分离

- Web 端通过 `frontend/src/lib/http.js` 统一处理 API 调用与端标识。
- 业务核心仍放在后端，避免把计费、登录、支付、任务状态等逻辑写死在 Web 组件里。

## 接小程序时的建议顺序

1. 小程序端复用现有 JWT 鉴权。
2. 所有请求统一加 `X-Client-Source: miniprogram`。
3. 新增小程序微信授权入口，调用现有微信用户归并逻辑。
4. 前端新增微信支付调起，复用现有支付回调和积分到账逻辑。
5. 管理后台按 `source` 做端维度统计即可。
