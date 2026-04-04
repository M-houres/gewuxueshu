from __future__ import annotations

from contextlib import redirect_stdout
import io
import inspect
import json
from pathlib import Path
import sys
from typing import Any

from app.services.algo_package_service import _load_process_function, _normalize_zip_path


def _to_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    return str(value)


def _emit(payload: dict[str, Any]) -> int:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()
    return 0 if payload.get("ok") else 1


_TEXT_KEYS = ("text", "input_text", "input", "content", "body", "payload", "source", "document")


def _value_key(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return repr(value)


def _scalar_candidate(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in _TEXT_KEYS:
            if key in payload:
                return payload.get(key)
        if "data" in payload:
            return payload.get("data")
    return payload


def _iter_call_candidates(payload: Any, fallback_payload: Any | None):
    seen: set[tuple[str, str]] = set()

    def push(args: tuple[Any, ...], kwargs: dict[str, Any] | None = None):
        mapping = dict(kwargs or {})
        key = (
            "|".join(_value_key(item) for item in args),
            "|".join(f"{name}={_value_key(value)}" for name, value in sorted(mapping.items())),
        )
        if key in seen:
            return
        seen.add(key)
        yield args, mapping

    inputs = [payload]
    if fallback_payload is not None:
        inputs.append(fallback_payload)

    for candidate in inputs:
        yield from push((candidate,), None)
        if isinstance(candidate, dict):
            yield from push((), candidate)
            for key in _TEXT_KEYS:
                if key in candidate:
                    value = candidate.get(key)
                    yield from push((value,), None)
                    yield from push((), {key: value})
            if "data" in candidate:
                value = candidate.get("data")
                yield from push((value,), None)
                yield from push((), {"data": value})

        scalar = _scalar_candidate(candidate)
        for key in _TEXT_KEYS:
            yield from push((), {key: scalar})
        yield from push((scalar,), None)

    yield from push((), None)


def _invoke_process(process_fn, *, payload: Any, fallback_payload: Any | None) -> Any:
    try:
        signature = inspect.signature(process_fn)
    except (TypeError, ValueError):
        signature = None

    last_shape_error: Exception | None = None
    for args, kwargs in _iter_call_candidates(payload, fallback_payload):
        if signature is not None:
            try:
                signature.bind(*args, **kwargs)
            except TypeError:
                continue
        try:
            return process_fn(*args, **kwargs)
        except (TypeError, AttributeError, KeyError) as exc:
            last_shape_error = exc
            continue

    if last_shape_error is not None:
        raise last_shape_error
    raise RuntimeError("process invocation failed")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        return _emit({"ok": False, "error": "runner arguments invalid"})

    package_path = Path(args[0])
    entry_path = _normalize_zip_path(args[1])

    try:
        request = json.loads(sys.stdin.read() or "{}")
        if not isinstance(request, dict):
            raise ValueError("runner payload invalid")

        file_bytes = package_path.read_bytes()
        process_fn = _load_process_function(file_bytes, entry_path=entry_path)

        payload = request.get("payload")
        fallback_payload = request.get("fallback_payload")
        with redirect_stdout(io.StringIO()):
            result = _invoke_process(
                process_fn,
                payload=payload,
                fallback_payload=fallback_payload,
            )

        return _emit({"ok": True, "result": _to_json_safe(result)})
    except Exception as exc:
        return _emit({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
