from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from github_api import load_github_token
from github_issues import issue_comment, issue_create, parse_repo_slug


@dataclass(frozen=True)
class BridgeConfig:
    token: str
    allowed_chat_ids: set[int]
    repo_owner: str
    repo_name: str
    dry_run: bool
    offset_file: Path
    events_file: Path
    media_dir: Path
    top6_json_path: Path | None
    lock_file: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        row = json.loads(raw)
    except Exception:
        return None
    if isinstance(row, dict):
        return row
    return None


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _parse_id_set(raw: str) -> set[int]:
    out: set[int] = set()
    for piece in (raw or "").replace(";", ",").split(","):
        v = piece.strip()
        if not v:
            continue
        out.add(int(v))
    return out


def _latest_top6_json() -> Path | None:
    root = Path(__file__).resolve().parents[1] / "reports"
    candidates = sorted(root.glob("project_top6_priorities_*.json"))
    return candidates[-1] if candidates else None


def _build_config(args: argparse.Namespace) -> BridgeConfig:
    token = (args.token or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("missing_telegram_token")
    raw_chat_ids = (args.allowed_chat_ids or os.environ.get("TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS") or "").strip()
    if not raw_chat_ids:
        raise RuntimeError("missing_allowed_chat_ids")
    allowed_chat_ids = _parse_id_set(raw_chat_ids)
    raw_repo = (args.repo or os.environ.get("TELEGRAM_BRIDGE_REPO") or "").strip()
    slug = parse_repo_slug(raw_repo)
    if slug is None:
        raise RuntimeError("invalid_repo_slug")
    owner, repo = slug
    top6_path: Path | None = Path(args.top6_json).resolve() if args.top6_json else _latest_top6_json()
    return BridgeConfig(
        token=token,
        allowed_chat_ids=allowed_chat_ids,
        repo_owner=owner,
        repo_name=repo,
        dry_run=bool(args.dry_run),
        offset_file=Path(args.offset_file).resolve(),
        events_file=Path(args.events_file).resolve(),
        media_dir=Path(args.media_dir).resolve(),
        top6_json_path=top6_path,
        lock_file=Path(args.lock_file).resolve(),
    )


def _tg_api_call(token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode("utf-8", errors="replace"))
    if not isinstance(out, dict):
        raise RuntimeError("telegram_api_invalid_payload")
    return out


def _send_message(token: str, chat_id: int, text: str) -> None:
    _tg_api_call(token, "sendMessage", {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def _download_telegram_file(token: str, file_id: str, media_dir: Path) -> Path | None:
    info = _tg_api_call(token, "getFile", {"file_id": file_id})
    result = info.get("result")
    if not isinstance(result, dict):
        return None
    file_path = result.get("file_path")
    if not isinstance(file_path, str) or not file_path.strip():
        return None
    suffix = Path(file_path).suffix or ".bin"
    target_name = f"{int(time.time() * 1000)}_{file_id}{suffix}"
    media_dir.mkdir(parents=True, exist_ok=True)
    target = media_dir / target_name
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        target.write_bytes(resp.read())
    return target


def _load_offset(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _save_offset(path: Path, offset: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(offset), encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    payload = json.dumps({"pid": pid, "ts_utc": _utc_now()}, ensure_ascii=False)
    try:
        with path.open("x", encoding="utf-8") as fh:
            fh.write(payload)
        return
    except FileExistsError:
        pass
    stale = False
    try:
        row = _read_json(path) or {}
        old_pid = int(row.get("pid") or 0)
        stale = not _pid_alive(old_pid)
    except Exception:
        stale = True
    if stale:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        with path.open("x", encoding="utf-8") as fh:
            fh.write(payload)
        return
    raise RuntimeError("telegram_bridge_already_running")


def _release_lock(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _extract_message_payload(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat")
    sender = message.get("from")
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return None
    chat_id = chat.get("id")
    user_id = sender.get("id")
    text_raw = message.get("text")
    caption_raw = message.get("caption")
    text = text_raw.strip() if isinstance(text_raw, str) else ""
    caption = caption_raw.strip() if isinstance(caption_raw, str) else ""
    photo = message.get("photo")
    photo_file_id: str | None = None
    if isinstance(photo, list):
        for item in photo:
            if not isinstance(item, dict):
                continue
            item_file_id = item.get("file_id")
            if isinstance(item_file_id, str) and item_file_id.strip():
                photo_file_id = item_file_id.strip()
    if not isinstance(chat_id, int) or not isinstance(user_id, int):
        return None
    return {
        "chat_id": chat_id,
        "user_id": user_id,
        "message_id": message.get("message_id"),
        "text": text or caption,
        "photo_file_id": photo_file_id,
        "has_photo": bool(photo_file_id),
    }


def _format_help() -> str:
    return (
        "Команды:\n"
        "/task <текст> — создать GitHub Issue\n"
        "/reply <event_id> <текст> — ответить в поток задачи\n"
        "/inbox [N] — последние входящие события\n"
        "/next — показать следующий приоритет\n"
        "/status — показать краткий статус board\n"
        "/help — справка"
    )


def _next_item(top6_json_path: Path | None) -> dict[str, Any] | None:
    if top6_json_path is None:
        return None
    row = _read_json(top6_json_path)
    if row is None:
        return None
    items = row.get("items")
    if not isinstance(items, list):
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("state", "")).lower() == "planned":
            return item
    return None


def _status_text(top6_json_path: Path | None) -> str:
    if top6_json_path is None:
        return "Статус board недоступен: не найден файл project_top6_priorities_*.json"
    row = _read_json(top6_json_path)
    if row is None:
        return "Статус board недоступен: не удалось прочитать JSON"
    items = row.get("items")
    if not isinstance(items, list):
        return "Статус board недоступен: items отсутствует"
    total = 0
    completed = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        total += 1
        if str(item.get("state", "")).lower() == "completed":
            completed += 1
    nxt = _next_item(top6_json_path)
    if nxt:
        return f"Board: {completed}/{total} completed. Next: {nxt.get('id')} — {nxt.get('direction', '')}"
    return f"Board: {completed}/{total} completed. Next: нет planned задач."


def _task_text_to_title_body(text: str, user_id: int, chat_id: int, attachment_note: str | None = None) -> tuple[str, str]:
    body = (
        "Источник: Telegram remote bridge\n"
        f"Время UTC: {_utc_now()}\n"
        f"Chat ID: {chat_id}\n"
        f"User ID: {user_id}\n\n"
        f"Запрос:\n{text}\n"
    )
    if attachment_note:
        body += f"\nВложение:\n{attachment_note}\n"
    title = text.strip()
    if len(title) > 120:
        title = title[:117].rstrip() + "..."
    return title or "Telegram task", body


def _build_inbox_text(events: list[dict[str, Any]], chat_id: int, limit: int) -> str:
    selected: list[dict[str, Any]] = []
    for row in reversed(events):
        if row.get("status") != "processed":
            continue
        if row.get("chat_id") != chat_id:
            continue
        event_id = row.get("event_id")
        text = row.get("text")
        if not isinstance(event_id, str) or not isinstance(text, str):
            continue
        selected.append(row)
        if len(selected) >= limit:
            break
    if not selected:
        return "Inbox пуст."
    lines = ["Inbox:"]
    for row in selected:
        item_id = str(row.get("event_id"))
        text = str(row.get("text"))
        issue_number = row.get("issue_number")
        photo_suffix = " | photo" if row.get("photo_path") else ""
        issue_suffix = f" | issue #{issue_number}" if isinstance(issue_number, int) else ""
        preview = text if len(text) <= 70 else text[:67].rstrip() + "..."
        lines.append(f"- {item_id}: {preview}{issue_suffix}{photo_suffix}")
    return "\n".join(lines)


def _find_event_by_id(events: list[dict[str, Any]], event_id: str, chat_id: int) -> dict[str, Any] | None:
    target = event_id.strip()
    for row in reversed(events):
        if row.get("chat_id") != chat_id:
            continue
        if str(row.get("event_id", "")).strip() == target:
            return row
    return None


def _format_github_error(prefix: str, status: int, error_kind: str | None) -> str:
    kind = (error_kind or "unknown").strip() or "unknown"
    if kind in {"auth_error", "auth_missing", "not_found_or_authz"} or status in {401, 403}:
        return (
            f"{prefix}: status={status} kind={kind}\n"
            "Проверьте токен и права на repo. Быстрое восстановление:\n"
            "Set-Location C:\\integrator\n"
            ".\\scripts\\setup_integrator_secrets.ps1 -RotateGithubToken -Json\n"
            ".\\scripts\\manage_telegram_bridge_task.ps1 -Action restart"
        )
    return f"{prefix}: status={status} kind={kind}"


def _handle_command(
    config: BridgeConfig,
    chat_id: int,
    user_id: int,
    text: str,
    event_id: str,
    attachment_note: str | None,
) -> dict[str, Any]:
    if text.startswith("/help"):
        return {"reply": _format_help()}
    if text.startswith("/status"):
        return {"reply": _status_text(config.top6_json_path)}
    if text.startswith("/next"):
        nxt = _next_item(config.top6_json_path)
        if nxt is None:
            return {"reply": "Следующая задача не найдена."}
        return {
            "reply": (
                f"Следующий приоритет: {nxt.get('id')}\n"
                f"Направление: {nxt.get('direction', '')}\n"
                f"DoD: {nxt.get('dod', '')}\n"
                f"Gate: {nxt.get('gate_metric', '')}"
            )
        }
    if text.startswith("/inbox"):
        raw_limit = text[len("/inbox") :].strip()
        try:
            limit = int(raw_limit) if raw_limit else 5
        except ValueError:
            limit = 5
        limit = max(1, min(limit, 20))
        events = _read_jsonl(config.events_file)
        return {"reply": _build_inbox_text(events=events, chat_id=chat_id, limit=limit)}
    if text.startswith("/reply"):
        payload = text[len("/reply") :].strip()
        if not payload:
            return {"reply": "Использование: /reply <event_id> <текст>"}
        parts = payload.split(" ", 1)
        if len(parts) != 2:
            return {"reply": "Использование: /reply <event_id> <текст>"}
        source_event_id = parts[0].strip()
        reply_text = parts[1].strip()
        if not source_event_id or not reply_text:
            return {"reply": "Использование: /reply <event_id> <текст>"}
        events = _read_jsonl(config.events_file)
        source = _find_event_by_id(events=events, event_id=source_event_id, chat_id=chat_id)
        if source is None:
            return {"reply": f"Событие {source_event_id} не найдено в inbox."}
        if config.dry_run:
            return {
                "reply": f"[dry-run] Ответ будет привязан к {source_event_id}: {reply_text}",
                "reply_to_event_id": source_event_id,
            }
        token = load_github_token()
        issue_number = source.get("issue_number")
        if isinstance(issue_number, int):
            result = issue_comment(
                config.repo_owner,
                config.repo_name,
                token=token,
                number=issue_number,
                body=(
                    "Ответ из Telegram remote bridge\n"
                    f"Время UTC: {_utc_now()}\n"
                    f"Reply event: {event_id}\n"
                    f"Source event: {source_event_id}\n\n"
                    f"{reply_text}"
                    + (f"\n\nВложение reply:\n{attachment_note}" if attachment_note else "")
                ),
            )
            if result.ok:
                return {
                    "reply": f"Комментарий добавлен в issue #{issue_number}.",
                    "reply_to_event_id": source_event_id,
                    "issue_number": issue_number,
                }
            return {
                "reply": _format_github_error("Не удалось добавить комментарий", result.status, result.error_kind),
                "reply_to_event_id": source_event_id,
            }
        title, body = _task_text_to_title_body(
            f"Reply to {source_event_id}: {reply_text}",
            user_id=user_id,
            chat_id=chat_id,
            attachment_note=attachment_note,
        )
        body = body + f"\nИсточник reply: {source_event_id}\n"
        result = issue_create(
            config.repo_owner,
            config.repo_name,
            token=token,
            title=title,
            body=body,
            labels=["remote", "telegram", "reply"],
        )
        if result.ok and isinstance(result.json, dict):
            issue_url = str(result.json.get("html_url", "")).strip()
            new_issue = result.json.get("number")
            return {
                "reply": f"Создан issue по reply: #{new_issue} {issue_url}".strip(),
                "reply_to_event_id": source_event_id,
                "issue_number": int(new_issue) if isinstance(new_issue, int) else None,
                "issue_url": issue_url,
            }
        return {
            "reply": _format_github_error("Не удалось создать issue по reply", result.status, result.error_kind),
            "reply_to_event_id": source_event_id,
        }
    if text.startswith("/task"):
        payload = text[len("/task") :].strip()
        if not payload:
            return {"reply": "Использование: /task <описание задачи>"}
        title, body = _task_text_to_title_body(payload, user_id=user_id, chat_id=chat_id, attachment_note=attachment_note)
        if config.dry_run:
            return {"reply": f"[dry-run] Issue будет создан: {title}"}
        token = load_github_token()
        result = issue_create(
            config.repo_owner,
            config.repo_name,
            token=token,
            title=title,
            body=body,
            labels=["remote", "telegram"],
        )
        if result.ok and isinstance(result.json, dict):
            issue_url = str(result.json.get("html_url", "")).strip()
            issue_num = result.json.get("number")
            return {
                "reply": f"Issue создан: #{issue_num} {issue_url}".strip(),
                "issue_number": int(issue_num) if isinstance(issue_num, int) else None,
                "issue_url": issue_url,
            }
        return {"reply": _format_github_error("Не удалось создать issue", result.status, result.error_kind)}
    return {"reply": "Неизвестная команда. Наберите /help"}


def _process_updates(config: BridgeConfig, updates: list[dict[str, Any]]) -> int:
    max_update_id = 0
    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            max_update_id = max(max_update_id, update_id)
        payload = _extract_message_payload(update)
        if payload is None:
            continue
        chat_id_raw = payload.get("chat_id")
        user_id_raw = payload.get("user_id")
        if not isinstance(chat_id_raw, int) or not isinstance(user_id_raw, int):
            continue
        chat_id = chat_id_raw
        user_id = user_id_raw
        text = str(payload.get("text", "")).strip()
        photo_file_id = payload.get("photo_file_id")
        photo_path: str | None = None
        attachment_note: str | None = None
        if isinstance(photo_file_id, str) and photo_file_id:
            try:
                saved = _download_telegram_file(config.token, photo_file_id, config.media_dir)
                if saved is not None:
                    photo_path = str(saved)
                    attachment_note = f"photo_path={photo_path}"
            except Exception:
                photo_path = None
                attachment_note = "photo_download_failed"
        event_id = f"e{update_id}" if isinstance(update_id, int) else f"e{int(time.time())}"
        event: dict[str, Any] = {
            "kind": "telegram_remote_bridge_event",
            "event_id": event_id,
            "update_id": update_id if isinstance(update_id, int) else None,
            "ts_utc": _utc_now(),
            "chat_id": chat_id,
            "user_id": user_id,
            "text": text,
            "photo_path": photo_path or "",
            "status": "ignored",
        }
        if chat_id not in config.allowed_chat_ids:
            event["status"] = "rejected_chat_not_allowed"
            _append_jsonl(config.events_file, event)
            continue
        if not text and photo_path:
            reply = "Скриншот получен. Добавьте подпись через /task <описание> или используйте /reply <event_id> <текст>."
            _send_message(config.token, chat_id, reply)
            event["status"] = "processed"
            event["reply"] = reply
            _append_jsonl(config.events_file, event)
            continue
        command_result = _handle_command(
            config,
            chat_id=chat_id,
            user_id=user_id,
            text=text,
            event_id=event_id,
            attachment_note=attachment_note,
        )
        reply = str(command_result.get("reply", "")).strip() or "OK"
        _send_message(config.token, chat_id, reply)
        event["status"] = "processed"
        event["reply"] = reply
        issue_number = command_result.get("issue_number")
        if isinstance(issue_number, int):
            event["issue_number"] = issue_number
        issue_url = command_result.get("issue_url")
        if isinstance(issue_url, str) and issue_url:
            event["issue_url"] = issue_url
        reply_to_event_id = command_result.get("reply_to_event_id")
        if isinstance(reply_to_event_id, str) and reply_to_event_id:
            event["reply_to_event_id"] = reply_to_event_id
        _append_jsonl(config.events_file, event)
    return max_update_id


def run_loop(config: BridgeConfig, once: bool) -> int:
    current_offset = _load_offset(config.offset_file)
    while True:
        payload = {"offset": current_offset + 1, "timeout": 25, "allowed_updates": ["message"]}
        try:
            row = _tg_api_call(config.token, "getUpdates", payload)
        except urllib.error.HTTPError as exc:
            if int(getattr(exc, "code", 0) or 0) == 409:
                raise RuntimeError("telegram_conflict_single_instance") from exc
            raise
        ok = bool(row.get("ok"))
        result = row.get("result")
        if not ok or not isinstance(result, list):
            return 1
        updates: list[dict[str, Any]] = [x for x in result if isinstance(x, dict)]
        max_id = _process_updates(config, updates)
        if max_id > 0:
            current_offset = max_id
            _save_offset(config.offset_file, current_offset)
        if once:
            return 0
        time.sleep(0.3)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram remote bridge: smartphone -> project task flow")
    parser.add_argument("--token", default=None, help="Telegram bot token (or TELEGRAM_BOT_TOKEN)")
    parser.add_argument("--repo", default=None, help="GitHub repo slug owner/repo (or TELEGRAM_BRIDGE_REPO)")
    parser.add_argument(
        "--allowed-chat-ids",
        default=None,
        help="Comma-separated chat IDs (or TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS)",
    )
    parser.add_argument("--offset-file", default="reports/telegram_bridge_offset.txt")
    parser.add_argument("--events-file", default="reports/telegram_bridge_events.jsonl")
    parser.add_argument("--media-dir", default="reports/telegram_media")
    parser.add_argument("--top6-json", default=None)
    parser.add_argument("--lock-file", default="reports/telegram_bridge.lock")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        config = _build_config(args)
        _acquire_lock(config.lock_file)
        try:
            code = run_loop(config=config, once=bool(args.once))
        finally:
            _release_lock(config.lock_file)
        if args.json:
            print(
                json.dumps(
                    {
                        "kind": "telegram_remote_bridge",
                        "status": "pass" if code == 0 else "fail",
                        "repo": f"{config.repo_owner}/{config.repo_name}",
                        "events_file": str(config.events_file),
                        "offset_file": str(config.offset_file),
                        "lock_file": str(config.lock_file),
                        "dry_run": config.dry_run,
                    },
                    ensure_ascii=False,
                )
            )
        return code
    except Exception as exc:
        if args.json:
            print(json.dumps({"kind": "telegram_remote_bridge", "status": "fail", "error": str(exc)}, ensure_ascii=False))
        else:
            print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
