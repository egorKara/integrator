import unittest
from pathlib import Path

from tools.telegram_remote_bridge import (
    _build_inbox_text,
    _extract_message_payload,
    _find_event_by_id,
    _format_github_error,
    _next_item,
    _parse_id_set,
    _status_text,
    _task_text_to_title_body,
)


class TelegramRemoteBridgeTests(unittest.TestCase):
    def test_parse_id_set(self) -> None:
        self.assertEqual(_parse_id_set("1, 2;3"), {1, 2, 3})

    def test_task_title_body(self) -> None:
        title, body = _task_text_to_title_body("Сделать удалённый канал", user_id=7, chat_id=9)
        self.assertIn("Сделать удалённый канал", title)
        self.assertIn("User ID: 7", body)
        self.assertIn("Chat ID: 9", body)

    def test_next_and_status(self) -> None:
        root = Path(__file__).resolve().parent
        path = root / ".tmp_top6.json"
        path.write_text(
            """{
              "items": [
                {"id":"P12","state":"completed","direction":"done"},
                {"id":"P13","state":"planned","direction":"next","dod":"x","gate_metric":"g"}
              ]
            }""",
            encoding="utf-8",
        )
        try:
            nxt = _next_item(path)
            self.assertIsNotNone(nxt)
            if nxt is not None:
                self.assertEqual(nxt.get("id"), "P13")
            status = _status_text(path)
            self.assertIn("1/2 completed", status)
            self.assertIn("P13", status)
        finally:
            path.unlink(missing_ok=True)

    def test_inbox_and_find_event(self) -> None:
        events = [
            {
                "event_id": "e100",
                "chat_id": 1,
                "text": "/task one",
                "status": "processed",
                "issue_number": 42,
                "photo_path": "reports/telegram_media/p.png",
            },
            {"event_id": "e101", "chat_id": 1, "text": "/status", "status": "processed"},
            {"event_id": "e102", "chat_id": 2, "text": "/task other", "status": "processed"},
        ]
        text = _build_inbox_text(events=events, chat_id=1, limit=5)
        self.assertIn("Inbox:", text)
        self.assertIn("e101", text)
        self.assertIn("e100", text)
        self.assertIn("issue #42", text)
        self.assertIn("photo", text)
        found = _find_event_by_id(events=events, event_id="e100", chat_id=1)
        self.assertIsNotNone(found)
        if found is not None:
            self.assertEqual(found.get("event_id"), "e100")

    def test_extract_message_payload_photo_caption(self) -> None:
        update = {
            "message": {
                "message_id": 9,
                "chat": {"id": 10},
                "from": {"id": 11},
                "caption": "/task приложил скрин",
                "photo": [{"file_id": "small"}, {"file_id": "large"}],
            }
        }
        row = _extract_message_payload(update)
        self.assertIsNotNone(row)
        if row is not None:
            self.assertEqual(row.get("chat_id"), 10)
            self.assertEqual(row.get("user_id"), 11)
            self.assertEqual(row.get("text"), "/task приложил скрин")
            self.assertEqual(row.get("photo_file_id"), "large")

    def test_format_github_error_auth_hint(self) -> None:
        text = _format_github_error("Не удалось создать issue", 401, "auth_error")
        self.assertIn("setup_integrator_secrets.ps1", text)
        self.assertIn("manage_telegram_bridge_task.ps1", text)
