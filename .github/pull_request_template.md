# Linked Issue
- Closes #

# T+A=S
- Тезис (ситуация):
- Антитезис (проблема/риски):
- Синтез (решение/подход):

# Verification
- [ ] `python -m ruff check .`
- [ ] `python -m mypy .`
- [ ] `python -m unittest discover -s tests -p "test*.py"`
- [ ] `python -m coverage report -m --fail-under=80`

# Compatibility
- [ ] No breaking CLI changes
- [ ] Output contracts preserved (`--json`, `--json-strict`)

# Security
- [ ] No secrets committed (`.env`, tokens, vault contents)
- [ ] Files under `vault/` remain excluded from checks

# SSOT / Knowledge
- [ ] No SSOT changes required
- [ ] SSOT/docs updated (link):

# Ops checklist
- [ ] Token discovery done (present/len only)
- [ ] Fact checks done (API access confirmed) before mutations

# Docs / Rollback
- [ ] README/CHANGELOG updated (if applicable)
- [ ] Rollback steps documented
