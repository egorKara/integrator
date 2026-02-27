from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    repl: str


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _iter_md_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.md"):
        if p.is_file():
            yield p


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    notes_root = repo_root / "vault" / "Projects" / "AlgoTrading" / "Notes"
    if not notes_root.exists():
        raise SystemExit(f"Notes root not found: {notes_root}")

    rules = [
        Rule(
            name="vault_root_projects",
            pattern=re.compile(r"C:\\vault\\Projects", re.IGNORECASE),
            repl=r"${VAULT_ROOT}",
        ),
        Rule(
            name="localai_root",
            pattern=re.compile(r"C:\\LocalAI", re.IGNORECASE),
            repl=r"${LOCALAI_ROOT}",
        ),
        Rule(
            name="file_url_localai_root",
            pattern=re.compile(r"file:///C:/LocalAI", re.IGNORECASE),
            repl="file:///c:/integrator/LocalAI",
        ),
        Rule(
            name="file_url_old_integrator_root",
            pattern=re.compile(
                r"file:///C:/Users/egork/Documents/trae_projects/integrator", re.IGNORECASE
            ),
            repl="file:///c:/integrator",
        ),
        Rule(
            name="old_integrator_root_plain",
            pattern=re.compile(
                r"C:\\Users\\egork\\Documents\\trae_projects\\integrator", re.IGNORECASE
            ),
            repl=r"C:\\integrator",
        ),
    ]

    manifest: dict = {
        "notes_root": str(notes_root),
        "changed_files": [],
        "totals": {r.name: 0 for r in rules},
    }

    changed_count = 0
    for path in _iter_md_files(notes_root):
        before = _read_text(path)
        after = before
        file_counts: dict[str, int] = {}
        for r in rules:
            after, n = r.pattern.subn(r.repl, after)
            if n:
                file_counts[r.name] = file_counts.get(r.name, 0) + n
                manifest["totals"][r.name] += n
        if after != before:
            _write_text(path, after)
            changed_count += 1
            manifest["changed_files"].append(
                {"path": str(path), "replacements": file_counts}
            )

    reports_dir = repo_root / "vault" / "Projects" / "AlgoTrading" / "Reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = reports_dir / "normalize_notes_paths_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Changed files: {changed_count}")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
