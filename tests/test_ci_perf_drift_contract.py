from pathlib import Path
import unittest


class CIPerfDriftContractTests(unittest.TestCase):
    def test_ci_uses_reference_and_current_perf_baselines(self) -> None:
        ci_path = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        text = ci_path.read_text(encoding="utf-8")
        self.assertIn("python -m integrator perf baseline --roots . --max-depth 2 --report-max-depth 1 --repeat 1 --write-report reports/perf_baseline_current.json --json", text)
        self.assertIn("python -m integrator perf check --baseline reports/perf_baseline_reference.json --current reports/perf_baseline_current.json --max-degradation-pct 20 --json", text)
        self.assertIn("python -m tools.check_p17_phase1_gate --reports-dir reports --docs-dir docs --json", text)


if __name__ == "__main__":
    unittest.main()
