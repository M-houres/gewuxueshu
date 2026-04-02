from __future__ import annotations

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
        try:
            result = process_fn(payload)
        except TypeError:
            if "fallback_payload" not in request:
                raise
            result = process_fn(request.get("fallback_payload"))

        return _emit({"ok": True, "result": _to_json_safe(result)})
    except Exception as exc:
        return _emit({"ok": False, "error": str(exc)})


if __name__ == "__main__":
    raise SystemExit(main())
