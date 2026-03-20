# recommendations execution 2026-03-20 02:33

- request:
  - remove rule `requires 2 approving reviews` for `egorKara/integrator`

- action:
  - updated GitHub ruleset `integrator-main-protection` (`id=13609983`) via Rulesets API
  - set `pull_request.required_approving_review_count` from `2` to `0`

- verification:
  - API update report: `reports/ruleset_remove_approvals_20260320_0232.json`
  - readiness check confirms current value:
    - `repo_ruleset.ruleset_details.rules.pull_request.parameters.required_approving_review_count = 0`
    - source: `reports/public_repo_readiness_20260320_022908.json`

- notes:
  - merge rules still enforce `required_linear_history`
  - quality tool now reports mismatch versus desired policy (because local desired baseline keeps `required_approvals=2`)
