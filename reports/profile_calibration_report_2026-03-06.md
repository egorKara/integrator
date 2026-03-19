# Profile calibration report (2026-03-06)

## Scope
- Task: P15 — калибровка профилей `research/coding/ops` для auto-finalize.
- Goal: уменьшить риск пере/недо-чувствительности и зафиксировать разделение профилей по чувствительности.

## Updated thresholds
| Profile | context_window_tokens | message_soft_limit | size_soft_limit_kb | token_soft_ratio | token_hard_ratio | score_threshold |
|---|---:|---:|---:|---:|---:|---:|
| research | 240000 | 80 | 320 | 0.82 | 0.93 | 0.85 |
| coding | 180000 | 45 | 190 | 0.72 | 0.86 | 0.76 |
| ops | 120000 | 24 | 96 | 0.55 | 0.70 | 0.60 |

## Calibration sample and expected behavior
- Synthetic fixture A: `30 x 3500 chars` messages.
  - Expected: `ops=true`, `coding=false`, `research=false`.
- Synthetic fixture B: `50 x 4500 chars` messages.
  - Expected: `ops=true`, `coding=true`, `research=false`.

## Verification
- Added tests in `tests/test_zapovednik.py`:
  - profile sensitivity ordering,
  - ops closes earlier than coding,
  - coding closes earlier than research.
- Regression tests pass in project test suite after threshold update.

## Outcome
- Profiles now have explicit monotonic sensitivity split: `ops` > `coding` > `research`.
- P15 DoD satisfied: thresholds calibrated on session sample and validated by tests.
