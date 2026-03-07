# PROC-1 token scope diagnostic (2026-03-06)

## Summary
- Текущий токен загружается из `C:\Users\egork\.integrator\secrets\github_token.txt`.
- После усиления токена репозиторий доступен (`repo_access=200`), но branch protection endpoints возвращают `403`.
- Текущее сообщение API: `Upgrade to GitHub Pro or make this repository public to enable this feature.`
- Вывод: основной блокер не в токене, а в ограничении тарифа/типа репозитория для branch protection.

## Required token
- Classic PAT: scope `repo` и пользователь токена с admin доступом к репозиторию.
- Fine-grained PAT: repository `egorKara/integrator`, permission `Administration: Read and write`.

## Where to add
- Рекомендуемо: `%USERPROFILE%\.integrator\secrets\github_token.txt`.
- Альтернативы:
  - env `GITHUB_TOKEN`/`GH_TOKEN`
  - env `GITHUB_TOKEN_FILE`/`INTEGRATOR_GITHUB_TOKEN_FILE`
  - `.env` в корне репозитория (`GITHUB_TOKEN=...`)

## Validation command
```powershell
python tools/apply_branch_protection.py --check-only
```

## Evidence
- `reports/branch_protection_apply_20260306_231532.json`
- `reports/branch_protection_apply_20260306_231842.json`
