# Skills Index

## Назначение

Единый реестр навыков проекта с явными границами применения и security-gate.

## Реестр

| skill | scope | trigger | anti-trigger | owner | path | security gate |
|---|---|---|---|---|---|---|
| integrator-cli-engineer | Integrator CLI | Изменение CLI-команд, парсеров, контрактов JSON/JSONL, тестов CLI | Чистый security-аудит без изменения CLI, RAG-операции LocalAI, VPN/VPS задачи | Integrator Core | `.trae/skills/integrator-cli-engineer/SKILL.md` | security-ops |
| security-ops | Cross-project baseline security | Базовый security-аудит, secret hygiene, hardening, baseline checks | PR-ревью логики/контрактов без security-фокуса, доменные оптимизации производительности | Security Owner | `.trae/skills/security-ops/SKILL.md` | self |
| github-pr-reviewer | PR quality gate | Pre-merge функциональный review, release readiness, контрактный review | Security-аудит токенов/прав, базовые security-проверки окружения | Integrator Core | `.trae/skills/github-pr-reviewer/SKILL.md` | github-security-reviewer |
| github-security-reviewer | PR security gate | Изменения auth/token/API/integrations, release hardening, permission review | Обычный функциональный review без security-поверхности, локальная RAG-эксплуатация | Security Owner | `.trae/skills/github-security-reviewer/SKILL.md` | security-ops |
| localai-assistant-ops | LocalAI assistant orchestration | Эксплуатация RAG/SSOT/indexing/MCP и межмодульная диагностика LocalAI assistant | Узкий анализ кода/метрик/тестов внутри LocalAI без ops-контекста | LocalAI Owner | `.trae/skills/localai-assistant-ops/SKILL.md` | security-ops |
| vpn-manager-maintainer | vpn-manager project | Изменения core/config/build/release только проекта `vpn-manager` | Любые задачи `vpn-manager-fedora`, общие security-аудиты без доменного изменения | VPN Owner | `.trae/skills/vpn-manager-maintainer/SKILL.md` | security-ops |
| vpn-manager-fedora-maintainer | vpn-manager-fedora project | Изменения core/config/build/release только проекта `vpn-manager-fedora` | Любые задачи `vpn-manager`, общие security-аудиты без доменного изменения | VPN Fedora Owner | `.trae/skills/vpn-manager-fedora-maintainer/SKILL.md` | security-ops |
| claude-stealth-connect-ops | Stealth Nexus project | VPS/proxy setup, chain diagnostics, ops automation скрипты | Integrator CLI refactor, LocalAI RAG diagnostics, PR-only review | Proxy Ops Owner | `.trae/skills/claude-stealth-connect-ops/SKILL.md` | security-ops |
| architecture-advisor | LocalAI assistant architecture | Архитектурный дизайн, decomposition, trade-off и границы модулей | Профилирование runtime, CVE-аудит, генерация тест-кейсов | LocalAI Owner | `LocalAI/assistant/.trae/skills/architecture-advisor/SKILL.md` | security-ops |
| code-analyzer | LocalAI assistant code analysis | Статический/динамический анализ дефектов и причин сбоев в коде | Архитектурные RFC, KPI-отчёты, dependency policy | LocalAI Owner | `LocalAI/assistant/.trae/skills/code-analyzer/SKILL.md` | security-ops |
| dependency-manager | LocalAI assistant dependencies | Обновления зависимостей, CVE triage, version conflicts, lock-файлы | Базовый секретный аудит репо, PR вердикт без dependency scope | LocalAI Owner | `LocalAI/assistant/.trae/skills/dependency-manager/SKILL.md` | github-security-reviewer |
| memory-manager | LocalAI assistant memory | Чтение/запись долговременной памяти и retrieval контекста | SSOT/RAG daemon ops, GitHub issue loop governance | LocalAI Owner | `LocalAI/assistant/.trae/skills/memory-manager/SKILL.md` | security-ops |
| metrics-manager | LocalAI assistant metrics | KPI/SLI отчётность, quality trend, success-rate анализ | Ручное профилирование bottleneck, crash-forensics | LocalAI Owner | `LocalAI/assistant/.trae/skills/metrics-manager/SKILL.md` | security-ops |
| performance-optimizer | LocalAI assistant performance | Профилирование и оптимизация latency/throughput/memory hotspots | Контрактный PR review, CVE triage, governance отчётность | LocalAI Owner | `LocalAI/assistant/.trae/skills/performance-optimizer/SKILL.md` | security-ops |
| predictive-debugger | LocalAI assistant reliability | Интермитентные сбои, трассы, гипотезы причин и диагностический план | Плановая архитектурная декомпозиция, KPI dashboard, dependency updates | LocalAI Owner | `LocalAI/assistant/.trae/skills/predictive-debugger/SKILL.md` | security-ops |
| rag-diagnostics | LocalAI assistant RAG diagnostics | Сжатая диагностика `/health`/`/_build`, проверка полноты и компактности ответа | Полноценная эксплуатация RAG/SSOT/indexer, архитектурный review | LocalAI Owner | `LocalAI/assistant/.trae/skills/rag-diagnostics/SKILL.md` | localai-assistant-ops |
| test-generator | LocalAI assistant testing | Генерация тест-сценариев, coverage plan, регрессии по рискам | Финальный PR verdict, CVE remediation policy, runtime ops мониторинг | LocalAI Owner | `LocalAI/assistant/.trae/skills/test-generator/SKILL.md` | github-pr-reviewer |
| knowledge-governance-ops | Knowledge base governance | Agent Memory + Obsidian + GitHub memory-loop governance, intake, traceability | Низкоуровневый refactor CLI, CVE triage без KB-контекста, VPS/VPN ops | Knowledge Owner | `.trae/skills/knowledge-governance-ops/SKILL.md` | github-security-reviewer |

## Правило выбора

1. Сначала выбирается доменный skill по scope.
2. Затем обязательно добавляется security gate из колонки `security gate`.
3. Для pre-merge skill-изменений обязательно: `github-pr-reviewer` + `github-security-reviewer` + `security-ops`.
