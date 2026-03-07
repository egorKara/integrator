from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence


TEMPLATE_BLOCK = """
## Ежедневный шаблон приоритизации P0/P1/P2
- Дата цикла: {cycle_date}
- Контекст: daily audit / backlog sync

### P0 (критично сегодня)
- [ ] Проверить open GitHub issues и выделить блокеры
- [ ] Зафиксировать и закрыть критичные инциденты/регрессии
- [ ] Подтвердить зелёный preflight и базовые quality gates

### P1 (важно в текущем цикле)
- [ ] Синхронизировать execution plans с фактом выполнения
- [ ] Обновить статусы и артефакты в reports/docs
- [ ] Принять решение issue-only vs Projects по readiness-сигналу

### P2 (улучшения и развитие)
- [ ] Обновить runbook/словарь/операционные шаблоны
- [ ] Запланировать исследования и продуктовые гипотезы
- [ ] Зафиксировать follow-up задачи следующего цикла

### Выход цикла
- [ ] Open issues после выполнения: ____
- [ ] Итоговый отчёт сохранён: ____
- [ ] Проверки консистентности: pass/fail ____
""".strip()


def _resolve_report_path(report: str | None, reports_dir: str) -> Path:
    if report:
        return Path(report).resolve()
    base = Path(reports_dir).resolve()
    candidates = sorted(base.glob("github_project_backlog_execution_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidates:
        return candidates[0]
    today = date.today().isoformat()
    return (base / f"github_project_backlog_execution_{today}.md").resolve()


def ensure_template(report_path: Path, cycle_date: str) -> dict[str, object]:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        text = report_path.read_text(encoding="utf-8")
    else:
        text = f"# GitHub + Project Backlog Execution ({cycle_date})\n"
    marker = "## Ежедневный шаблон приоритизации P0/P1/P2"
    added = False
    if marker not in text:
        suffix = TEMPLATE_BLOCK.format(cycle_date=cycle_date)
        text = text.rstrip() + "\n\n" + suffix + "\n"
        report_path.write_text(text, encoding="utf-8")
        added = True
    return {"ok": True, "report": str(report_path), "added": added}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Добавляет ежедневный шаблон P0/P1/P2 в отчёт")
    parser.add_argument("--report", default=None)
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report_path = _resolve_report_path(args.report, args.reports_dir)
    payload = ensure_template(report_path, str(args.date))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"report={payload['report']}")
        print(f"added={payload['added']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
