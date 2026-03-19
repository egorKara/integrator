# Trigger Validation Contract — Skills

Дата: 2026-03-07  
Контур: `C:\integrator`

## Цель

Проверить, что все исходные 17 skills имеют явные trigger/anti-trigger контракты и пригодны для предсказуемого роутинга.

## Метод

1. Базовый набор валидации: 17 исходных skills (без нового `knowledge-governance-ops`).
2. Для каждого skill проверены поля:
   - `name` в frontmatter
   - `description` в frontmatter
   - блок trigger (`Когда вызывать` или эквивалент)
   - блок anti-trigger (`Когда не вызывать` или эквивалент)
3. Отдельно проверена карта совместимости путей `.trae/skills` ↔ `.agents/skills`.

## Команды проверки

```bash
python -c "from pathlib import Path;import json;root=Path(r'c:\integrator');files=sorted([p for p in root.glob('.trae/skills/*/SKILL.md') if 'knowledge-governance-ops' not in str(p)] + list(root.glob('LocalAI/assistant/.trae/skills/*/SKILL.md')));res=[];ok=True
for p in files:
 t=p.read_text(encoding='utf-8'); checks={'has_name':'name:' in t,'has_description':'description:' in t,'has_trigger':('Когда вызывать' in t or 'When to invoke' in t or 'When to Use' in t),'has_antitrigger':('Когда не вызывать' in t or 'Do not invoke' in t or 'When NOT to use' in t)}; status=all(checks.values()); ok=ok and status; res.append({'skill':p.parent.name,'path':str(p.relative_to(root)).replace('\\','/'),'status':'pass' if status else 'fail',**checks})
print(json.dumps({'baseline_skill_count':len(files),'all_pass':ok,'results':res},ensure_ascii=False,indent=2))"
```

```bash
python -c "from pathlib import Path;import json;root=Path(r'c:\integrator');targets=[(root/'.agents/skills/skills_map.json',root),(root/'LocalAI/assistant/.agents/skills/skills_map.json',root/'LocalAI/assistant')];out=[];ok=True
for m,base in targets:
 data=json.loads(m.read_text(encoding='utf-8')); missing=[]
 for x in data['mappings']:
  p=base/x['canonical_path']
  if not p.exists(): missing.append(x['name'])
 out.append({'map':str(m.relative_to(root)).replace('\\','/'),'count':len(data['mappings']),'missing':missing,'status':'pass' if not missing else 'fail'})
 ok=ok and (not missing)
print(json.dumps({'all_pass':ok,'maps':out},ensure_ascii=False,indent=2))"
```

## Результаты

### 1) Trigger/anti-trigger контракт по 17 skills

- Проверено skills: **17**
- Итог: **all_pass = true**

| skill | path | status | has_name | has_description | has_trigger | has_antitrigger |
|---|---|---|---|---|---|---|
| claude-stealth-connect-ops | `.trae/skills/claude-stealth-connect-ops/SKILL.md` | pass | true | true | true | true |
| github-pr-reviewer | `.trae/skills/github-pr-reviewer/SKILL.md` | pass | true | true | true | true |
| github-security-reviewer | `.trae/skills/github-security-reviewer/SKILL.md` | pass | true | true | true | true |
| integrator-cli-engineer | `.trae/skills/integrator-cli-engineer/SKILL.md` | pass | true | true | true | true |
| localai-assistant-ops | `.trae/skills/localai-assistant-ops/SKILL.md` | pass | true | true | true | true |
| security-ops | `.trae/skills/security-ops/SKILL.md` | pass | true | true | true | true |
| vpn-manager-fedora-maintainer | `.trae/skills/vpn-manager-fedora-maintainer/SKILL.md` | pass | true | true | true | true |
| vpn-manager-maintainer | `.trae/skills/vpn-manager-maintainer/SKILL.md` | pass | true | true | true | true |
| architecture-advisor | `LocalAI/assistant/.trae/skills/architecture-advisor/SKILL.md` | pass | true | true | true | true |
| code-analyzer | `LocalAI/assistant/.trae/skills/code-analyzer/SKILL.md` | pass | true | true | true | true |
| dependency-manager | `LocalAI/assistant/.trae/skills/dependency-manager/SKILL.md` | pass | true | true | true | true |
| memory-manager | `LocalAI/assistant/.trae/skills/memory-manager/SKILL.md` | pass | true | true | true | true |
| metrics-manager | `LocalAI/assistant/.trae/skills/metrics-manager/SKILL.md` | pass | true | true | true | true |
| performance-optimizer | `LocalAI/assistant/.trae/skills/performance-optimizer/SKILL.md` | pass | true | true | true | true |
| predictive-debugger | `LocalAI/assistant/.trae/skills/predictive-debugger/SKILL.md` | pass | true | true | true | true |
| rag-diagnostics | `LocalAI/assistant/.trae/skills/rag-diagnostics/SKILL.md` | pass | true | true | true | true |
| test-generator | `LocalAI/assistant/.trae/skills/test-generator/SKILL.md` | pass | true | true | true | true |

### 2) Path compatibility map

- Проверено map-файлов: **2**
- Итог: **all_pass = true**

| map | count | missing | status |
|---|---:|---|---|
| `.agents/skills/skills_map.json` | 9 | [] | pass |
| `LocalAI/assistant/.agents/skills/skills_map.json` | 9 | [] | pass |

## Дополнение

Новый skill `knowledge-governance-ops` создан отдельно и включён в маршрутизацию, но не входит в baseline-валидацию 17 skills по условию задачи.

## Вердикт

Контракт trigger-validation для исходных 17 skills выполнен полностью и пригоден как проверяемый артефакт роутинга.
