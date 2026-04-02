from __future__ import annotations

from typing import Any, Mapping

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.exceptions import BizError
from app.models import SystemConfig, TaskType

settings = get_settings()

LLM_PROVIDER_PRESETS = {
    "openai": {
        "label": "OpenAI",
        "api_style": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "label": "Anthropic Claude",
        "api_style": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-latest",
    },
    "gemini": {
        "label": "Google Gemini",
        "api_style": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.0-flash",
    },
    "deepseek": {
        "label": "DeepSeek",
        "api_style": "openai",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
    "qwen": {
        "label": "Qwen / DashScope",
        "api_style": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "doubao": {
        "label": "Doubao / Ark",
        "api_style": "openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "",
    },
    "moonshot": {
        "label": "Moonshot / Kimi",
        "api_style": "openai",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "zhipu": {
        "label": "Zhipu GLM",
        "api_style": "openai",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "custom_openai": {
        "label": "Custom OpenAI Compatible",
        "api_style": "openai",
        "base_url": "",
        "model": "",
    },
}

SUPPORTED_LLM_PROVIDERS = set(LLM_PROVIDER_PRESETS)


def normalize_llm_provider(provider: str | None) -> str:
    raw = str(provider or "").strip().lower()
    if raw in {"openai_compatible", "custom", "compatible"}:
        return "custom_openai"
    if raw in SUPPORTED_LLM_PROVIDERS:
        return raw
    return "openai"


def resolve_llm_config(value: dict | None = None) -> dict:
    raw = value if isinstance(value, dict) else {}
    provider = normalize_llm_provider(raw.get("provider"))
    preset = LLM_PROVIDER_PRESETS[provider]
    return {
        "enabled": bool(raw.get("enabled", settings.llm_enabled_default)),
        "provider": provider,
        "api_style": preset["api_style"],
        "base_url": str(raw.get("base_url") or preset["base_url"] or settings.llm_api_base_url).rstrip("/"),
        "api_key": str(raw.get("api_key") or settings.llm_api_key),
        "model": str(raw.get("model") or preset["model"] or settings.llm_model),
        "timeout_seconds": int(raw.get("timeout_seconds", settings.llm_timeout_seconds)),
        "max_output_tokens": int(raw.get("max_output_tokens", 2048) or 2048),
        "temperature": float(raw.get("temperature", 0.3) or 0.3),
    }


def load_llm_config(db: Session) -> dict:
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.category == "system", SystemConfig.config_key == "llm")
        .first()
    )
    value = row.config_value if row and isinstance(row.config_value, dict) else {}
    return resolve_llm_config(value)


def _build_prompt(task_type: TaskType, text: str) -> str:
    if task_type == TaskType.DEDUP:
        return (
            "你是学术降重助手。请在不改变原意的前提下改写文本表达，"
            "只返回改写后的正文，不要输出解释。\n\n"
            f"原文：\n{text}"
        )
    if task_type == TaskType.REWRITE:
        return (
            "你是学术润色助手。请将文本改写为更自然、规范的中文学术表达，"
            "不得改变论点和数据，只返回改写后的正文。\n\n"
            f"原文：\n{text}"
        )
    return text


def generate_with_llm(db: Session, *, task_type: TaskType, text: str) -> str:
    cfg = load_llm_config(db)
    if not cfg["enabled"]:
        raise BizError(code=4601, message="LLM 未启用")
    if not cfg["api_key"]:
        raise BizError(code=4602, message="LLM API Key 未配置")

    try:
        with httpx.Client(timeout=cfg["timeout_seconds"]) as client:
            if cfg["api_style"] == "anthropic":
                content = _call_anthropic(client, cfg=cfg, task_type=task_type, text=text)
            elif cfg["api_style"] == "gemini":
                content = _call_gemini(client, cfg=cfg, task_type=task_type, text=text)
            else:
                content = _call_openai_compatible(client, cfg=cfg, task_type=task_type, text=text)
    except httpx.TimeoutException as exc:
        raise BizError(code=4603, message="LLM 调用超时") from exc
    except httpx.HTTPError as exc:
        raise BizError(code=4604, message=f"LLM HTTP 调用失败: {exc}") from exc
    except BizError:
        raise
    except Exception as exc:
        raise BizError(code=4605, message=f"LLM 调用异常: {exc}") from exc

    if not isinstance(content, str) or not content.strip():
        raise BizError(code=4606, message="LLM 返回内容为空")
    return content.strip()


def _call_openai_compatible(client: httpx.Client, *, cfg: Mapping[str, Any], task_type: TaskType, text: str) -> str:
    url = f"{cfg['base_url']}/chat/completions"
    payload: dict[str, Any] = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": "你是可靠的中文学术文本处理助手。"},
            {"role": "user", "content": _build_prompt(task_type, text)},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_output_tokens"],
    }
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    resp = client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    body = resp.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    return content if isinstance(content, str) else ""


def _call_anthropic(client: httpx.Client, *, cfg: Mapping[str, Any], task_type: TaskType, text: str) -> str:
    url = f"{cfg['base_url']}/messages"
    payload = {
        "model": cfg["model"],
        "max_tokens": cfg["max_output_tokens"],
        "temperature": cfg["temperature"],
        "system": "你是可靠的中文学术文本处理助手。",
        "messages": [{"role": "user", "content": _build_prompt(task_type, text)}],
    }
    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    resp = client.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    body = resp.json()
    content_blocks = body.get("content", [])
    texts = []
    for item in content_blocks:
        if isinstance(item, dict) and item.get("type") == "text":
            texts.append(str(item.get("text", "")))
    return "\n".join(texts).strip()


def _call_gemini(client: httpx.Client, *, cfg: Mapping[str, Any], task_type: TaskType, text: str) -> str:
    url = f"{cfg['base_url']}/models/{cfg['model']}:generateContent"
    payload = {
        "systemInstruction": {
            "parts": [{"text": "你是可靠的中文学术文本处理助手。"}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": _build_prompt(task_type, text)}],
            }
        ],
        "generationConfig": {
            "temperature": cfg["temperature"],
            "maxOutputTokens": cfg["max_output_tokens"],
        },
    }
    resp = client.post(url, params={"key": cfg["api_key"]}, json=payload)
    resp.raise_for_status()
    body = resp.json()
    candidates = body.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "\n".join(str(item.get("text", "")) for item in parts if isinstance(item, dict)).strip()
