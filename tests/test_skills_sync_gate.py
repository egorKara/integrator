import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import check_skills_sync as mod


def _write_skill(path: Path, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f'name: "{name}"',
                'description: "x"',
                "---",
                "",
                f"# {name}",
                "",
                "## Когда вызывать",
                "- x",
                "",
                "## Когда не вызывать",
                "- y",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_layout(root: Path) -> None:
    _write_skill(root / ".trae/skills/alpha/SKILL.md", "alpha")
    _write_skill(root / "LocalAI/assistant/.trae/skills/beta/SKILL.md", "beta")

    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs/SKILLS_INDEX.md").write_text(
        "\n".join(
            [
                "# Skills Index",
                "",
                "| skill | scope | trigger | anti-trigger | owner | path | security gate |",
                "|---|---|---|---|---|---|---|",
                "| alpha | A | t | nt | o | `.trae/skills/alpha/SKILL.md` | self |",
                "| beta | B | t | nt | o | `LocalAI/assistant/.trae/skills/beta/SKILL.md` | self |",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (root / "AGENTS.md").write_text(
        "\n".join(
            [
                "# Agents",
                "",
                "## Skill Routing",
                "- `alpha`: test.",
                "- `beta`: test.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (root / ".agents/skills").mkdir(parents=True, exist_ok=True)
    (root / ".agents/skills/skills_map.json").write_text(
        json.dumps(
            {
                "version": 1,
                "source_of_truth": ".trae/skills",
                "mappings": [
                    {
                        "name": "alpha",
                        "canonical_path": ".trae/skills/alpha/SKILL.md",
                        "standard_path": ".agents/skills/alpha/SKILL.md",
                        "status": "active",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    (root / "LocalAI/assistant/.agents/skills").mkdir(parents=True, exist_ok=True)
    (root / "LocalAI/assistant/.agents/skills/skills_map.json").write_text(
        json.dumps(
            {
                "version": 1,
                "source_of_truth": ".trae/skills",
                "mappings": [
                    {
                        "name": "beta",
                        "canonical_path": ".trae/skills/beta/SKILL.md",
                        "standard_path": ".agents/skills/beta/SKILL.md",
                        "status": "active",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


class SkillsSyncGateTests(unittest.TestCase):
    def test_check_sync_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_layout(root)
            result = mod.check_sync(project_root=root)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.counts["index_skills"], 2)

    def test_check_sync_detects_map_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_layout(root)
            bad_map = root / ".agents/skills/skills_map.json"
            payload = json.loads(bad_map.read_text(encoding="utf-8"))
            payload["mappings"] = []
            bad_map.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            result = mod.check_sync(project_root=root)
        self.assertFalse(result.ok)
        self.assertTrue(any(err.startswith("missing_in_maps:") for err in result.errors))

    def test_main_json_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_layout(root)
            (root / "docs/SKILLS_INDEX.md").unlink()
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                code = mod.main(["--root", str(root), "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["kind"], "skills_sync")
        self.assertEqual(payload["status"], "fail")


if __name__ == "__main__":
    unittest.main()
