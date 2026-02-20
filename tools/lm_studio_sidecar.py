from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from utils import _write_text_atomic
except ModuleNotFoundError:
    _repo_root = str(Path(__file__).resolve().parents[1])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    from utils import _write_text_atomic


@dataclass(frozen=True, slots=True)
class SidecarResult:
    outputs: list[str]
    response_json_path: str | None


def _timestamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())


def _safe_read_text(path: Path, max_chars: int) -> str:
    data = path.read_bytes()
    text = data.decode("utf-8", errors="replace")
    return text[: max(0, int(max_chars))]


def _is_sensitive_path(path: Path) -> bool:
    s = str(path).replace("\\", "/").lower()
    if s.endswith("/.env") or s.endswith(".env"):
        return True
    if "/vault/" in s or s.startswith("vault/"):
        return True
    if "/.trae/memory/" in s:
        return True
    if s.endswith("project_memory.xml"):
        return True
    return False


def _collect_inputs(paths: list[Path], max_chars: int, allow_sensitive: bool) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path in paths:
        if _is_sensitive_path(path) and not allow_sensitive:
            raise ValueError(f"sensitive input blocked: {path}")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
        items.append({"path": str(path), "content": _safe_read_text(path, max_chars=max_chars)})
    return {"inputs": items}


def _build_prompt(mode: str, payload: dict[str, Any]) -> tuple[str, str]:
    system = (
        "Ты инженерный ассистент. Работай по формуле Тезис → Антитезис → Синтез. "
        "Не выдумывай факты: опирайся только на входные артефакты. "
        "Не проси секреты и не включай секреты в вывод. "
        "Выводи коротко и по делу, со списками действий."
    )

    user_header = (
        "Ниже входные артефакты проекта integrator (файлы из reports/ и связанные логи). "
        "Сформируй результат в Markdown."
    )
    data = json.dumps(payload, ensure_ascii=False, indent=2)

    if mode == "recommendations":
        user = (
            f"{user_header}\n\n"
            "Задача: выдать приоритетные технические рекомендации по улучшению (производительность/качество/риски) "
            "и конкретные шаги. Обязательно: KPI и артефакт фиксации результата.\n\n"
            f"{data}"
        )
        return system, user

    if mode == "ci-triage":
        user = (
            f"{user_header}\n\n"
            "Задача: сделать triage проблем CI/quality gates. "
            "Формат: root cause → reproduction → fix → regression test.\n\n"
            f"{data}"
        )
        return system, user

    if mode == "tests":
        user = (
            f"{user_header}\n\n"
            "Задача: предложить точечные тесты/кейсы для поднятия покрытия и снижения регрессий. "
            "Не предлагай интеграции, которые требуют внешней сети.\n\n"
            f"{data}"
        )
        return system, user

    raise ValueError(f"unknown mode: {mode}")


def _chat_completion(base_url: str, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", "v1/chat/completions")
    body = json.dumps(
        {"model": model, "messages": messages, "temperature": 0.2},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60.0) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read() if hasattr(e, "read") else b""
        raise RuntimeError(f"lm_studio_http_error status={getattr(e, 'code', 0) or 0} body={raw[:2000]!r}") from e

    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        raise RuntimeError(f"lm_studio_invalid_json body={raw[:2000]!r}") from e


def _extract_markdown(resp: dict[str, Any]) -> str:
    choices = resp.get("choices", [])
    if not isinstance(choices, list) or not choices:
        raise ValueError("lm_studio_response_missing_choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("lm_studio_response_invalid_choice")
    msg = first.get("message", {})
    if not isinstance(msg, dict):
        raise ValueError("lm_studio_response_invalid_message")
    content = msg.get("content", "")
    if not isinstance(content, str):
        raise ValueError("lm_studio_response_invalid_content")
    return content


def run(
    *,
    mode: str,
    inputs: list[Path],
    output_dir: Path,
    base_url: str,
    model: str,
    max_chars: int,
    allow_sensitive: bool,
    write_response_json: bool,
    dry_run: bool,
) -> SidecarResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = _collect_inputs(inputs, max_chars=max_chars, allow_sensitive=allow_sensitive)
    system, user = _build_prompt(mode=mode, payload=payload)
    out_prefix = f"{mode.replace('-', '_')}_llm_{_timestamp()}"
    out_md = output_dir / f"{out_prefix}.md"
    out_json = output_dir / f"{out_prefix}.response.json" if write_response_json else None

    if dry_run:
        _write_text_atomic(out_md, "# Dry run\n\n(no request sent)\n", backup=True)
        return SidecarResult(outputs=[str(out_md)], response_json_path=str(out_json) if out_json else None)

    resp = _chat_completion(
        base_url=base_url,
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    md = _extract_markdown(resp)
    if md and not md.endswith("\n"):
        md += "\n"
    _write_text_atomic(out_md, md, backup=True)
    if out_json:
        _write_text_atomic(out_json, json.dumps(resp, ensure_ascii=False, indent=2) + "\n", backup=True)
    return SidecarResult(outputs=[str(out_md)], response_json_path=str(out_json) if out_json else None)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["recommendations", "ci-triage", "tests"], required=True)
    ap.add_argument("--input", action="append", default=[])
    ap.add_argument("--output-dir", default="reports")
    ap.add_argument("--base-url", default=os.environ.get("LMSTUDIO_BASE_URL") or "http://127.0.0.1:1234")
    ap.add_argument("--model", default=os.environ.get("LMSTUDIO_MODEL") or "local-model")
    ap.add_argument("--max-chars", type=int, default=200000)
    ap.add_argument("--allow-sensitive", action="store_true")
    ap.add_argument("--write-response-json", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    inputs = [Path(p).resolve() for p in (args.input or []) if str(p).strip()]
    if not inputs:
        raise SystemExit(2)
    try:
        run(
            mode=str(args.mode),
            inputs=inputs,
            output_dir=Path(args.output_dir).resolve(),
            base_url=str(args.base_url),
            model=str(args.model),
            max_chars=int(args.max_chars),
            allow_sensitive=bool(args.allow_sensitive),
            write_response_json=bool(args.write_response_json),
            dry_run=bool(args.dry_run),
        )
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
