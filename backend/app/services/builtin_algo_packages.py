import io
import json
import zipfile
from dataclasses import dataclass
from textwrap import dedent

from sqlalchemy.orm import Session

from app.exceptions import BizError
from app.services.algo_package_service import _validate_slot, install_algorithm_package


@dataclass(frozen=True)
class BuiltinPackageSpec:
    platform: str
    function_type: str
    name: str
    version: str
    main_py: str


_VERSION = "1.1.0"


def _aigc_detect_code(*, profile: str, score_offset: float) -> str:
    return (
        dedent(
            f"""
            import hashlib
            import re

            PROFILE = "{profile}"
            SCORE_OFFSET = {score_offset}


            def _clamp(value):
                return max(0.0, min(1.0, float(value)))


            def process(input_data):
                text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)
                clean = " ".join(str(text).split())
                if not clean:
                    return {{"ai_score": 0.1, "label": "low", "profile": PROFILE, "text_stats": {{"chars": 0, "sentences": 0}}}}

                sentences = [seg.strip() for seg in re.split(r"[。\\n]+", clean) if seg.strip()]
                avg_len = sum(len(seg) for seg in sentences) / max(len(sentences), 1)
                unique_ratio = len(set(clean)) / max(len(clean), 1)
                repeat_signal = 1.0 - unique_ratio

                base = 0.42 + (avg_len - 22.0) / 125.0 + repeat_signal * 0.35 + SCORE_OFFSET
                seed = int(hashlib.md5(clean.encode("utf-8")).hexdigest()[:8], 16)
                jitter = ((seed % 17) - 8) / 1000.0
                score = round(_clamp(base + jitter), 4)

                if score >= 0.65:
                    label = "high"
                elif score >= 0.35:
                    label = "medium"
                else:
                    label = "low"

                return {{
                    "ai_score": score,
                    "label": label,
                    "profile": PROFILE,
                    "text_stats": {{
                        "chars": len(clean),
                        "sentences": len(sentences),
                        "avg_sentence_length": round(avg_len, 2),
                    }},
                    "algorithm": f"{{PROFILE}}_aigc_sim_v1_1_0",
                }}
            """
        ).strip()
        + "\n"
    )


def _dedup_code(*, profile: str, replacements: list[tuple[str, str]]) -> str:
    replacements_literal = json.dumps(replacements, ensure_ascii=False)
    return (
        dedent(
            f"""
            import hashlib
            import re

            PROFILE = "{profile}"
            REPLACEMENTS = {replacements_literal}


            def process(input_data):
                text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)
                normalized = re.sub(r"\\s+", " ", str(text)).strip()
                if not normalized:
                    return {{"text": "", "similarity": 0.0, "algorithm": f"{{PROFILE}}_dedup_sim_v1_1_0"}}

                output = normalized
                change_count = 0
                for src, dst in REPLACEMENTS:
                    prev = output
                    output = output.replace(src, dst)
                    if output != prev:
                        change_count += 1

                if output == normalized and len(output) > 30:
                    output = output.replace("，", "；", 1)
                    if output == normalized:
                        output = output.replace("。", "；", 1)

                seed = int(hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8], 16)
                rough_similarity = 8.0 + (seed % 31) + change_count * 2.2
                similarity = round(max(0.1, min(78.0, rough_similarity)), 2)

                return {{
                    "text": output,
                    "similarity": similarity,
                    "changes": change_count,
                    "algorithm": f"{{PROFILE}}_dedup_sim_v1_1_0",
                }}
            """
        ).strip()
        + "\n"
    )


def _rewrite_code(*, profile: str, replacements: list[tuple[str, str]]) -> str:
    replacements_literal = json.dumps(replacements, ensure_ascii=False)
    return (
        dedent(
            f"""
            import hashlib
            import re

            PROFILE = "{profile}"
            REPLACEMENTS = {replacements_literal}


            def _clamp_score(score):
                return max(0.0, min(100.0, float(score)))


            def process(input_data):
                text = input_data.get("text", "") if isinstance(input_data, dict) else str(input_data)
                source = re.sub(r"\\s+", " ", str(text)).strip()
                if not source:
                    return {{"text": "", "original_aigc_score": 0.0, "rewritten_aigc_score": 0.0, "algorithm": f"{{PROFILE}}_rewrite_sim_v1_1_0"}}

                output = source
                for src, dst in REPLACEMENTS:
                    output = output.replace(src, dst)
                output = re.sub(r"[。]{{2,}}", "。", output)

                seed = int(hashlib.md5(source.encode("utf-8")).hexdigest()[:8], 16)
                original_score = _clamp_score(52 + (seed % 34))
                reduction = 18 + (seed % 16)
                rewritten_score = _clamp_score(original_score - reduction)

                return {{
                    "text": output,
                    "original_aigc_score": round(original_score, 2),
                    "rewritten_aigc_score": round(rewritten_score, 2),
                    "algorithm": f"{{PROFILE}}_rewrite_sim_v1_1_0",
                }}
            """
        ).strip()
        + "\n"
    )


BUILTIN_PACKAGE_SPECS = (
    BuiltinPackageSpec(
        platform="cnki",
        function_type="aigc_detect",
        name="cnki_aigc_detect",
        version=_VERSION,
        main_py=_aigc_detect_code(profile="cnki_like", score_offset=0.00),
    ),
    BuiltinPackageSpec(
        platform="cnki",
        function_type="dedup",
        name="cnki_dedup",
        version=_VERSION,
        main_py=_dedup_code(
            profile="cnki_like",
            replacements=[
                ("首先", "第一"),
                ("其次", "第二"),
                ("因此", "由此可见"),
                ("但是", "然而"),
                ("总之", "综上所述"),
                ("可以看出", "据此可见"),
            ],
        ),
    ),
    BuiltinPackageSpec(
        platform="cnki",
        function_type="rewrite",
        name="cnki_rewrite",
        version=_VERSION,
        main_py=_rewrite_code(
            profile="cnki_like",
            replacements=[
                ("研究表明", "已有研究指出"),
                ("我们发现", "研究发现"),
                ("可以看出", "据此可见"),
                ("非常重要", "具有关键意义"),
            ],
        ),
    ),
    BuiltinPackageSpec(
        platform="vip",
        function_type="aigc_detect",
        name="vip_aigc_detect",
        version=_VERSION,
        main_py=_aigc_detect_code(profile="vip_like", score_offset=-0.02),
    ),
    BuiltinPackageSpec(
        platform="vip",
        function_type="dedup",
        name="vip_dedup",
        version=_VERSION,
        main_py=_dedup_code(
            profile="vip_like",
            replacements=[
                ("首先", "其一"),
                ("其次", "其二"),
                ("此外", "另一方面"),
                ("因此", "所以"),
                ("总之", "总体来看"),
                ("可以看出", "能够看出"),
            ],
        ),
    ),
    BuiltinPackageSpec(
        platform="vip",
        function_type="rewrite",
        name="vip_rewrite",
        version=_VERSION,
        main_py=_rewrite_code(
            profile="vip_like",
            replacements=[
                ("研究表明", "文献显示"),
                ("我们发现", "结果显示"),
                ("可以看出", "可以观察到"),
                ("非常重要", "较为关键"),
            ],
        ),
    ),
    BuiltinPackageSpec(
        platform="paperpass",
        function_type="aigc_detect",
        name="paperpass_aigc_detect",
        version=_VERSION,
        main_py=_aigc_detect_code(profile="paperpass_like", score_offset=0.03),
    ),
    BuiltinPackageSpec(
        platform="paperpass",
        function_type="dedup",
        name="paperpass_dedup",
        version=_VERSION,
        main_py=_dedup_code(
            profile="paperpass_like",
            replacements=[
                ("首先", "首要的是"),
                ("其次", "进一步看"),
                ("此外", "同时还需注意"),
                ("因此", "由此能够发现"),
                ("总之", "综合来看"),
                ("可以看出", "据此可以发现"),
            ],
        ),
    ),
    BuiltinPackageSpec(
        platform="paperpass",
        function_type="rewrite",
        name="paperpass_rewrite",
        version=_VERSION,
        main_py=_rewrite_code(
            profile="paperpass_like",
            replacements=[
                ("研究表明", "从现有研究来看"),
                ("我们发现", "分析结果显示"),
                ("可以看出", "据此可以发现"),
                ("非常重要", "具有核心作用"),
            ],
        ),
    ),
)


def _build_package_zip(spec: BuiltinPackageSpec) -> bytes:
    manifest = {
        "name": spec.name,
        "version": spec.version,
        "platform": spec.platform,
        "function_type": spec.function_type,
        "entry": "main.py",
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("main.py", spec.main_py)
    return buf.getvalue()


def _build_template_readme(spec: BuiltinPackageSpec) -> str:
    function_guides = {
        "aigc_detect": "- 推荐返回 dict，并至少包含 ai_score(0~1) 与 label(low/medium/high)\n- 建议额外返回 text_stats、algorithm、profile 等可观测字段\n",
        "dedup": "- 推荐返回 dict，并包含 text 字段作为处理后的正文\n- 建议额外返回 similarity、changes、algorithm 等字段\n",
        "rewrite": "- 推荐返回 dict，并包含 text 字段作为改写后的正文\n- 建议额外返回 original_aigc_score、rewritten_aigc_score、algorithm 等字段\n",
    }
    guide_text = function_guides.get(
        spec.function_type,
        "- 返回值必须非 None，并能被 JSON 序列化或转成字符串\n",
    ).strip()
    return dedent(
        f"""
        # 算法包模板说明

        这是 `{spec.platform}/{spec.function_type}` 槽位的可运行模板包。

        使用方式：
        1. 按需修改 `main.py` 中的 `process` 函数实现。
        2. 如需改名或重新上传，请同步修改 `manifest.json` 里的 `name` 与 `version`。
        3. 上传目标槽位必须与 `manifest.json` 内的 `platform` / `function_type` 完全一致。
        4. 入口文件默认是 `main.py`，如需改成别的路径，务必同步修改 `entry` 且保证文件实际存在。

        当前槽位建议：
        {guide_text}

        上传前检查：
        - zip 内必须有 `manifest.json`
        - Python 文件需 UTF-8 编码
        - `process` 需要能处理字符串输入；若你只接受 dict，请至少兼容 `{{"text": "..."}}`
        - 单次执行超时默认 8 秒
        - 上传文件大小默认不超过 200 MB
        """
    ).strip() + "\n"


def build_builtin_template_package(
    *,
    platform: str,
    function_type: str,
) -> tuple[str, bytes]:
    normalized_platform, normalized_function_type = _validate_slot(platform, function_type)
    spec = next(
        (
            item
            for item in BUILTIN_PACKAGE_SPECS
            if item.platform == normalized_platform and item.function_type == normalized_function_type
        ),
        None,
    )
    if spec is None:
        raise BizError(code=4526, message="算法包模板不存在")

    manifest = {
        "name": spec.name,
        "version": spec.version,
        "platform": spec.platform,
        "function_type": spec.function_type,
        "entry": "main.py",
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("main.py", spec.main_py)
        zf.writestr("README.md", _build_template_readme(spec))

    filename = f"algo_package_template_{spec.platform}_{spec.function_type}_{spec.version}.zip"
    return filename, buf.getvalue()


def _blank_package_manifest(*, platform: str, function_type: str) -> dict:
    return {
        "name": f"{platform}_{function_type}_custom",
        "version": "1.0.0",
        "platform": platform,
        "function_type": function_type,
        "entry": "main.py",
    }


def _blank_package_main_py(*, platform: str, function_type: str) -> str:
    algorithm_name = f"{platform}_{function_type}_custom"
    if function_type == "aigc_detect":
        return (
            dedent(
                f"""
                def _extract_text(payload):
                    if isinstance(payload, dict):
                        return payload.get("text", "")
                    return payload


                def process(payload):
                    text = str(_extract_text(payload) or "").strip()
                    # TODO: replace the placeholder logic with your own implementation.
                    score = 0.0 if not text else 0.5
                    label = "low" if score < 0.35 else "medium"
                    return {{
                        "ai_score": round(score, 4),
                        "label": label,
                        "algorithm": "{algorithm_name}",
                        "text_stats": {{
                            "chars": len(text),
                        }},
                    }}
                """
            ).strip()
            + "\n"
        )
    if function_type == "dedup":
        return (
            dedent(
                f"""
                def _extract_text(payload):
                    if isinstance(payload, dict):
                        return payload.get("text", "")
                    return payload


                def process(payload):
                    text = str(_extract_text(payload) or "").strip()
                    # TODO: replace the placeholder logic with your own implementation.
                    return {{
                        "text": text,
                        "similarity": 0.0,
                        "changes": 0,
                        "algorithm": "{algorithm_name}",
                    }}
                """
            ).strip()
            + "\n"
        )
    return (
        dedent(
            f"""
            def _extract_text(payload):
                if isinstance(payload, dict):
                    return payload.get("text", "")
                return payload


            def process(payload):
                text = str(_extract_text(payload) or "").strip()
                # TODO: replace the placeholder logic with your own implementation.
                return {{
                    "text": text,
                    "original_aigc_score": 0.0,
                    "rewritten_aigc_score": 0.0,
                    "algorithm": "{algorithm_name}",
                }}
            """
        ).strip()
        + "\n"
    )


def _authoring_bundle_readme() -> str:
    return (
        dedent(
            """
            # 算法写作总规范包

            这个规范包只解决一件事：你自己写的算法包，怎样组织、编码、返回，才能上传到当前系统后稳定跑起来。

            不包含业务算法结论，也不包含平台规避策略。它只描述当前项目的真实运行契约。

            ## 你应该怎么用

            1. 进入 `blank_packages/`，找到你要写的槽位目录。
            2. 先改 `manifest.json` 的 `name`、`version`。
            3. 再改 `main.py` 里的 `process` 实现。
            4. 打包时，必须把 `manifest.json` 和入口文件打在 zip 根目录下。
            5. 上传时，后台选择的槽位必须和 `manifest.json` 完全一致。

            ## 当前系统的硬约束

            - 上传文件必须是 zip
            - `manifest.json` 必须是 UTF-8
            - 入口 Python 文件必须是 UTF-8
            - `manifest.entry` 必须指向 zip 内真实存在的文件
            - 路径不能是绝对路径，也不能包含 `..`
            - 入口文件必须定义可调用的 `process`
            - `process` 返回值不能是 `None`
            - 运行时优先传入字符串；若报 `TypeError`，会再尝试传入 `{"text": "..."}`
            - 当前默认执行超时 8 秒
            - 当前默认包大小上限 200 MB

            ## 目录说明

            - `docs/00_runtime_contract.md`
              当前项目实际怎么校验、怎么加载、怎么执行
            - `docs/01_aigc_detect_spec.md`
              `aigc_detect` 写法规范
            - `docs/02_dedup_spec.md`
              `dedup` 写法规范
            - `docs/03_rewrite_spec.md`
              `rewrite` 写法规范
            - `blank_packages/`
              9 个槽位的空白可运行骨架
            """
        ).strip()
        + "\n"
    )


def _runtime_contract_doc() -> str:
    return (
        dedent(
            """
            # 运行时契约

            ## 1. manifest 要求

            - `name` 正则：`^[A-Za-z0-9_-]{2,64}$`
            - `version` 正则：`^[0-9]+(?:\\.[0-9]+){2}(?:[-+._A-Za-z0-9]*)?$`
            - `platform` 只能是 `cnki` / `vip` / `paperpass`
            - `function_type` 只能是 `aigc_detect` / `dedup` / `rewrite`
            - `entry` 默认 `main.py`
            - `entry` 只能是相对路径，不能包含 `..`

            ## 2. 运行方式

            - 系统会在子进程里执行算法包
            - 会从 zip 中读取 `manifest.entry` 对应的 Python 文件
            - 入口模块必须定义 `process`

            ## 3. 调用方式

            smoke test 与正式执行，都会优先按下面方式调用：

            ```python
            result = process(text)
            ```

            如果抛出 `TypeError`，系统会再尝试：

            ```python
            result = process({"text": text})
            ```

            因此最稳的写法，是你的 `process` 同时兼容字符串和对象输入。

            ## 4. smoke test 样例

            当前 smoke test 文本：

            ```text
            这是用于算法包 smoke test 的样例文本。
            ```

            只要你的 `process` 在这一步报错、超时或返回 `None`，上传就会失败。

            ## 5. 打包注意事项

            正确：

            ```text
            your_package.zip
              manifest.json
              main.py
            ```

            错误：

            ```text
            your_package.zip
              my_folder/
                manifest.json
                main.py
            ```

            上传时要求 `manifest.json` 在 zip 根层可直接读取。
            """
        ).strip()
        + "\n"
    )


def _function_spec_doc(function_type: str) -> str:
    if function_type == "aigc_detect":
        title = "AIGC 检测算法写作规范"
        core_principles = [
            "输入兼容字符串与 `{\"text\": ...}` 两种形式。",
            "返回值使用 dict，不要返回自定义对象。",
            "至少返回 `ai_score` 和 `label`，避免前后版本字段含义漂移。",
        ]
        output_example = dedent(
            """
            {
              "ai_score": 0.42,
              "label": "medium",
              "algorithm": "paperpass_aigc_detect_custom",
              "text_stats": {
                "chars": 1280
              }
            }
            """
        ).strip()
        writing_notes = [
            "`ai_score` 建议固定在 0 到 1 之间。",
            "`label` 建议只用 `low` / `medium` / `high`。",
            "不要依赖全局状态或外部网络调用。",
        ]
    elif function_type == "dedup":
        title = "降重复率算法写作规范"
        core_principles = [
            "返回正文时优先放在 `text` 字段里。",
            "若需要附带分数、变更次数，统一作为结构化字段返回。",
            "对空文本、超短文本要直接可处理，不要抛异常。",
        ]
        output_example = dedent(
            """
            {
              "text": "处理后的正文",
              "similarity": 12.6,
              "changes": 8,
              "algorithm": "cnki_dedup_custom"
            }
            """
        ).strip()
        writing_notes = [
            "如果返回 dict，请务必带 `text`。",
            "如果只返回字符串，系统也能跑，但后续排查信息会少。",
            "注意保证输出永远是字符串或可 JSON 序列化结构。",
        ]
    else:
        title = "改写算法写作规范"
        core_principles = [
            "返回正文时优先放在 `text` 字段里。",
            "建议把改写前后指标也结构化返回，方便对比。",
            "保持 `process` 幂等、可重复执行，不依赖运行环境副作用。",
        ]
        output_example = dedent(
            """
            {
              "text": "改写后的正文",
              "original_aigc_score": 58.0,
              "rewritten_aigc_score": 31.5,
              "algorithm": "vip_rewrite_custom"
            }
            """
        ).strip()
        writing_notes = [
            "如果返回 dict，请务必带 `text`。",
            "原始分、改写后分建议都返回数值。",
            "不要在 `process` 内读写业务数据库或系统目录。",
        ]

    principles_text = "\n".join(f"- {item}" for item in core_principles)
    notes_text = "\n".join(f"- {item}" for item in writing_notes)
    return (
        dedent(
            f"""
            # {title}

            ## 核心原则

            {principles_text}

            ## 返回值建议

            ```json
            {output_example}
            ```

            ## 写作注意事项

            {notes_text}

            ## 常见失败原因

            - `process` 参数只支持一种形态，结果 smoke test 兼容失败
            - 返回了 `None`
            - 返回了不可 JSON 化的对象
            - 入口文件不是 UTF-8
            - 打包时把 `manifest.json` 压到了子目录里
            """
        ).strip()
        + "\n"
    )


def _blank_package_readme(*, platform: str, function_type: str) -> str:
    return (
        dedent(
            f"""
            # 空白骨架说明

            这是 `{platform}/{function_type}` 槽位的最小可运行骨架。

            你需要做的只有两件事：

            1. 修改 `manifest.json`
               - 改 `name`
               - 改 `version`
            2. 修改 `main.py`
               - 保留 `process`
               - 把占位逻辑替换成你的真实算法

            打包时注意：

            - zip 根目录必须直接包含 `manifest.json`
            - zip 根目录必须直接包含 `main.py`，或你在 `entry` 中指定的入口文件
            - 上传槽位必须和 manifest 中的 `platform` / `function_type` 完全一致
            """
        ).strip()
        + "\n"
    )


def build_authoring_spec_bundle() -> tuple[str, bytes]:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", _authoring_bundle_readme())
        zf.writestr("docs/00_runtime_contract.md", _runtime_contract_doc())
        zf.writestr("docs/01_aigc_detect_spec.md", _function_spec_doc("aigc_detect"))
        zf.writestr("docs/02_dedup_spec.md", _function_spec_doc("dedup"))
        zf.writestr("docs/03_rewrite_spec.md", _function_spec_doc("rewrite"))

        for platform in ("cnki", "vip", "paperpass"):
            for function_type in ("aigc_detect", "dedup", "rewrite"):
                base = f"blank_packages/{platform}/{function_type}"
                manifest = _blank_package_manifest(platform=platform, function_type=function_type)
                zf.writestr(f"{base}/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
                zf.writestr(f"{base}/main.py", _blank_package_main_py(platform=platform, function_type=function_type))
                zf.writestr(f"{base}/README.md", _blank_package_readme(platform=platform, function_type=function_type))

    filename = "ALGO_PACKAGE_AUTHORING_SPEC_BUNDLE.zip"
    return filename, buf.getvalue()


def bootstrap_builtin_algo_packages(
    db: Session,
    *,
    uploaded_by: int,
    activate_after_upload: bool = True,
) -> dict:
    items = []
    for spec in BUILTIN_PACKAGE_SPECS:
        result = install_algorithm_package(
            db,
            file_bytes=_build_package_zip(spec),
            platform=spec.platform,
            function_type=spec.function_type,
            uploaded_by=uploaded_by,
            activate_after_upload=activate_after_upload,
        )
        items.append(
            {
                "platform": spec.platform,
                "function_type": spec.function_type,
                "name": spec.name,
                "version": spec.version,
                "active_version": (result.get("active_slot") or {}).get("version"),
            }
        )
    return {"count": len(items), "items": items}
