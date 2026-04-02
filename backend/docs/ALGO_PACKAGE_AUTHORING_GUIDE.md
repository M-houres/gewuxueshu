# 算法包撰写说明

这份说明按当前项目代码的真实校验逻辑整理，不是泛泛模板。你只要按下面的约束写，上传后就不会因为包结构、编码、入口、返回值这些基础问题卡住。

## 1. 支持的槽位

当前固定支持 3 个平台 x 3 个功能类型：

- 平台：`cnki`、`vip`、`paperpass`
- 功能：`aigc_detect`、`dedup`、`rewrite`

上传时你选择的槽位，必须和 `manifest.json` 里的 `platform`、`function_type` 完全一致。

## 2. 压缩包格式

算法包必须是一个 `.zip` 文件。

最小可用结构：

```text
manifest.json
main.py
```

也支持自定义入口路径，例如：

```text
manifest.json
engine/
  custom.py
dict/
  replace_words.json
```

只要 `manifest.entry` 指向的文件真实存在即可。

注意：

- 压缩包内路径不能是绝对路径
- 压缩包内路径不能包含 `..`
- 建议不要把无关大文件打进 zip

## 3. `manifest.json` 必填规则

示例：

```json
{
  "name": "paperpass_rewrite_v1",
  "version": "1.0.0",
  "platform": "paperpass",
  "function_type": "rewrite",
  "entry": "main.py"
}
```

字段要求：

- `name`
  - 必填
  - 只能包含字母、数字、下划线、短横线
  - 长度 2 到 64
  - 当前正则：`^[A-Za-z0-9_-]{2,64}$`
- `version`
  - 必填
  - 必须是语义化版本风格
  - 例如：`1.0.0`、`1.0.1-beta`
  - 当前正则：`^[0-9]+(?:\.[0-9]+){2}(?:[-+._A-Za-z0-9]*)?$`
- `platform`
  - 必填
  - 只能是：`cnki`、`vip`、`paperpass`
  - 必须与上传槽位一致
- `function_type`
  - 必填
  - 只能是：`aigc_detect`、`dedup`、`rewrite`
  - 必须与上传槽位一致
- `entry`
  - 可选，默认 `main.py`
  - 必须是 zip 内真实存在的相对路径
  - 不能写成绝对路径
  - 不能包含 `..`

其他要求：

- `manifest.json` 必须是 UTF-8 编码
- `manifest.json` 顶层必须是 JSON 对象，不能是数组

## 4. 入口文件与 `process` 函数

入口文件必须定义一个可调用的 `process` 函数。

推荐写法：

```python
def process(text):
    source = str(text or "").strip()
    return {
        "text": source,
    }
```

更稳妥的兼容写法：

```python
def process(payload):
    if isinstance(payload, dict):
        text = payload.get("text", "")
    else:
        text = payload
    source = str(text or "").strip()
    return {
        "text": source,
    }
```

为什么建议这么写：

- 运行时系统会优先把原始文本字符串传给 `process`
- 如果调用报 `TypeError`，系统会再尝试传一个 `{"text": 原文}` 的对象
- 所以最稳的是同时兼容字符串和对象输入

## 5. 当前运行行为

这部分很重要，直接决定你怎么写包。

### 5.1 smoke test 会做什么

上传时系统会执行一次快速校验：

- 入口文件会被真正加载
- `process` 会被真正调用
- 样本文本当前是：`这是用于算法包 smoke test 的样例文本。`

如果你的包在这一步报错，上传就会失败。

### 5.2 执行方式

当前算法包在子进程里运行，不再是主进程内直接 `exec`。

这意味着：

- 算法包异常不容易直接把主服务打崩
- 但这仍然不是完整沙箱
- 算法包子进程依旧有当前机器上的 Python 执行能力

### 5.3 超时与大小

当前默认配置：

- 算法包大小上限：`200 MB`
- 单次执行超时：`8 秒`

如果你写的逻辑明显超过这个量级，上传后即使能通过，也会在正式运行时超时。

## 6. 返回值怎么写最稳

`process` 不能返回 `None`。

系统最终会把返回值转成 JSON 可传输形式，所以推荐返回：

- 字符串
- 数字 / 布尔值
- 字典
- 列表

不推荐直接返回复杂自定义对象。

### 6.1 `aigc_detect`

推荐返回 `dict`，至少带这些字段：

```python
{
    "ai_score": 0.42,
    "label": "medium",
    "algorithm": "paperpass_aigc_v1"
}
```

建议补充：

- `profile`
- `text_stats`
- `reason`

其中：

- `ai_score` 建议用 `0 ~ 1`
- `label` 建议只用 `low` / `medium` / `high`

### 6.2 `dedup`

推荐返回 `dict`，至少带 `text`：

```python
{
    "text": "处理后的正文",
    "similarity": 18.6,
    "changes": 7,
    "algorithm": "cnki_dedup_v1"
}
```

也可以直接返回字符串，但建议保留结构化字段，后续更好排查。

### 6.3 `rewrite`

推荐返回 `dict`，至少带 `text`：

```python
{
    "text": "改写后的正文",
    "original_aigc_score": 61.5,
    "rewritten_aigc_score": 34.2,
    "algorithm": "vip_rewrite_v1"
}
```

## 7. 一个最小可用示例

### `manifest.json`

```json
{
  "name": "paperpass_rewrite_v1",
  "version": "1.0.0",
  "platform": "paperpass",
  "function_type": "rewrite",
  "entry": "main.py"
}
```

### `main.py`

```python
import re


def process(payload):
    if isinstance(payload, dict):
        text = payload.get("text", "")
    else:
        text = payload

    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if not source:
        return {
            "text": "",
            "algorithm": "paperpass_rewrite_v1"
        }

    output = source.replace("首先", "首先需要说明的是")
    output = output.replace("因此", "由此可以看出")

    return {
        "text": output,
        "original_aigc_score": 58.0,
        "rewritten_aigc_score": 36.0,
        "algorithm": "paperpass_rewrite_v1"
    }
```

## 8. 上传失败的常见原因

下面这些问题会直接导致上传或 smoke test 失败：

- 缺少 `manifest.json`
- `manifest.json` 不是合法 JSON
- `manifest.json` 不是 UTF-8
- `name` / `version` 不符合格式
- `platform` / `function_type` 跟上传槽位不一致
- `entry` 指向的文件不存在
- `entry` 路径里包含 `..`
- 入口 Python 文件不是 UTF-8
- 入口文件里没有 `process`
- `process` 运行时报错
- `process` 返回 `None`

## 9. 建议的开发流程

建议你按这个顺序来写：

1. 先在后台下载对应槽位的模板包
2. 只改 `main.py` 的逻辑，不要先动包结构
3. 上传前把 `version` 提升一下
4. 先在少量样本文本上验证输入输出格式
5. 上传通过后再决定是否激活到槽位
6. 保留每个版本的样本输入、输出和预期说明

## 10. 安全提醒

当前执行隔离只是进程级，不是完整沙箱。你的算法包代码会在当前机器的 Python 子进程里运行。

所以不要在包里做这些事：

- 读取系统敏感目录
- 启动额外系统命令
- 依赖本机环境里的隐式文件路径
- 硬编码密钥、账号、网关地址

推荐做法：

- 只处理输入文本与包内自带词典/配置
- 对空字符串、超长文本、异常字符做好保护
- 让 `process` 尽量纯函数化，输入什么，输出什么，便于排查
