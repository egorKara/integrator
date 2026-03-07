# CI Contract Smoke

- status: `pass`
- errors: `none`

## Validator Details
- positive_payload: `ok`
- canary_missing_key: `missing_keys:checks, checks:not_dict`
- canary_steps_shape_drift: `steps[0]:invalid_keys`
- canary_exit_status_mismatch: `exit_code_status_mismatch:fail_zero`
- canary_contract_version_drift: `contract_version:not_1_0`
- canary_extra_fields: `extra_keys:unexpected_field`

## Scenario Matrix
- positive_payload: `expected_valid=True` `detected=True`
- canary_missing_key: `expected_valid=False` `detected=True`
- canary_steps_shape_drift: `expected_valid=False` `detected=True`
- canary_exit_status_mismatch: `expected_valid=False` `detected=True`
- canary_contract_version_drift: `expected_valid=False` `detected=True`
- canary_extra_fields: `expected_valid=False` `detected=True`
