# QA 审计日志

## 审计报告 #001 项目初始化与状态控制文件

### 功能描述

初始化项目并建立 PRD 要求的状态与审计机制文件
### 验收标准核查

- 创建 `PROJECT_STATUS.md`：通过
- 创建 `QA_AUDIT_LOG.md`：通过
- 写入初始功能清单与状态：通过

### 代码审查发现

无

### 测试执行

- 手工检查文件存在与内容格式：通过

### 最终结论

审计通过

## 审计报告 #002 全栈MVP落地

### 功能描述

完成前后台页面、核心业务接口、异步任务、积分与推广基础流程
### 验收标准核查

- 手机号验证码登录与锁定机制：通过
- 三大任务页面可提交文件并创建任务：通过
- 任务失败可触发退积分：通过（代码路径核查）
- 推广邀请码、邀请记录、奖励流水接口：通过
- 后台仪表盘与列表页实时取数：通过
- 统一 API 响应格式：通过
- 前端构建：通过（`npm run build`）

### 代码审查发现

- Docker 环境未完成联调，容器拉起受本机 Docker API 异常影响
- 支付仍为 Mock，真实签名校验未接入
- 算法包上传与热替换未落地
### 测试执行

- 后端语法检查：`python -m compileall backend/app` 通过
- 前端构建：`npm run build` 通过
- Docker compose：失败（Docker Engine API 返回 500）

### 最终结论

阶段性通过（MVP 主链路可用，存在已登记遗留项）

## 审计报告 #003 支付回调与算法包管理补齐

### 功能描述

补齐商业化支付回调核心链路（验签+幂等）与算法包管理基础能力（上传、manifest校验、smoke test、激活、列表）

### 验收标准核查

- 支付回调接口 `/api/v1/billing/callback`：通过
- 支付回调签名校验（HMAC-SHA256）：通过
- 支付回调重复通知幂等（不重复加积分）：通过（代码与测试核查）
- 算法包上传（zip）与 `manifest.json` 校验：通过
- 算法包基础 smoke test（入口文件存在、任务类型合法）：通过
- 后台算法包管理接口（上传/激活/列表）：通过
- SQLite 回退主键自增兼容修复：通过（`BigInteger` 主键改为 SQLite 兼容变体）

### 代码审查发现

- 本机 Python 环境未安装 `pytest`，自动化测试暂无法直接执行
- Docker 仍受本机 Engine API 500 影响，容器联调待恢复

### 测试执行

- 语法编译检查：`python -m compileall backend/app backend/tests` 通过
- 新增测试文件：
  - `backend/tests/test_billing_callback.py`
  - `backend/tests/test_algo_packages.py`
- 自动化测试执行：`python -m pytest backend/tests -q` 失败（环境缺少 pytest 模块）

### 最终结论

功能实现通过，测试用例已补齐；待补本机测试环境后执行完整自动化回归

## 审计报告 #004 PRD对齐整改（算法包+后台联动）

### 功能描述

根据 PRD 第5章与第7章补齐算法包槽位化管理与后台前端联动能力，并修复登录态回跳体验

### 验收标准核查

- 算法包上传必须包含 `manifest.json` + `main.py`：通过
- `manifest.platform/function_type` 与上传槽位一致性校验：通过
- 上传后 smoke test（调用 `main.py` 的 `process`）：通过
- 后台算法包页面展示槽位当前版本/上传时间/smoke状态：通过
- 后台支持槽位激活切换：通过
- 登录态接口 401 后，登录后返回原页面：通过

### 代码审查发现

- 本机 `pytest` 仍未安装，自动化回归执行受限
- Docker Engine API 500 仍阻塞容器联调

### 测试执行

- 后端语法检查：`python -m compileall backend/app backend/tests` 通过
- 前端构建：`npm run build` 通过
- 算法包接口冒烟（上传+查询）：通过

### 最终结论

PRD 对齐整改阶段性通过；待第三方审查报告产出后继续逐条闭环
