# 配置中心与官方要求对照（运营版）

更新时间：2026-03-31

## 大模型（LLM）
- 分类：`系统配置 -> 大模型配置`
- 启用时必填：`base_url`、`model`、`api_key`
- 约束：API Key 仅服务端保存，关闭 LLM 时系统自动走算法模式
- 参考：<https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety>

## 支付（微信/支付宝/网关）
- 分类：`系统配置 -> 支付配置`
- 开关：`test_mode`（开启仅 `mock`，关闭走正式通道）
- 微信支付 V3 必填：`app_id`、`merchant_id`、`merchant_serial_no`、`merchant_private_key_pem`、`api_v3_key`、`notify_url`
- 支付宝必填：`app_id`、`api_key`、`notify_url`
- 网关代理必填：`notify_url`
- 参考：<https://github.com/wechatpay-apiv3/wechatpay-java>

## 短信登录（腾讯云 / 阿里云 / 自建网关）
- 分类：`系统配置 -> 登录配置`
- 腾讯云必填：`sms_sdk_app_id`、`sms_sign_name`、`sms_template_id`、`sms_access_key_id`、`sms_access_key_secret`
- 阿里云必填：`sms_sign_name`、`sms_template_id`、`sms_access_key_id`、`sms_access_key_secret`
- 自建网关必填：`sms_gateway_url`
- 参考：<https://cloud.tencent.com/document/product/382/55981>
- 参考：<https://www.alibabacloud.com/help/en/sdk/product-overview/v3-request-structure-and-signature>

## 微信扫码登录
- 分类：`系统配置 -> 登录配置`
- 启用项：`wechat_login_enabled`、`wechat_app_id`、`wechat_app_secret`、`wechat_redirect_uri`
- 回调建议：`/api/v1/auth/wx/callback`，并与微信开放平台回调域一致
- 参考：<https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html>

## 上线前检查
- 关闭支付 `test_mode`
- 支付 `provider` 非 `mock`
- 登录至少有一种可用路径（短信 / 微信 / debug）
- 生产环境关闭 `debug_code_enabled`
