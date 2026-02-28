DEFAULT_CHAINS = [
    {
        "name": "health",
        "description": "Быстрая проверка здоровья проектов",
        "steps": [
            ["python", "-m", "integrator", "diagnostics", "--only-problems", "--json"],
            [
                "python",
                "-m",
                "integrator",
                "agents",
                "status",
                "--json",
                "--only-problems",
                "--roots",
                r"C:\LocalAI",
                "--max-depth",
                "4",
            ],
            [
                "python",
                "-m",
                "integrator",
                "status",
                "--only-dirty",
                "--json",
                "--roots",
                r"C:\LocalAI",
                "--max-depth",
                "4",
            ],
        ],
    },
    {
        "name": "registry-audit",
        "description": "Проверка реестра и доступности roots",
        "steps": [
            ["python", "-m", "integrator", "registry", "list", "--json"],
            ["python", "-m", "integrator", "projects", "list", "--max-depth", "2"],
        ],
    },
    {
        "name": "rag-start",
        "description": "Запуск RAG сервера в фоне",
        "steps": [["python", "-m", "integrator", "localai", "assistant", "rag", "--cwd", r"C:\LocalAI\assistant", "--daemon"]],
    },
    {
        "name": "gardener-apply-semantic",
        "description": "Запуск садовника с semantic и apply для всего Vault",
        "steps": [
            [
                "pwsh",
                "-NoProfile",
                "-Command",
                "$env:SSOT_PATH='C:\\LocalAI\\assistant\\cache\\ssot_vault_override.md'; python C:\\LocalAI\\assistant\\scripts\\run_gardener_cycle.py --semantic --apply --actions C:\\LocalAI\\assistant\\cache\\gardener_actions_vault.json",
            ]
        ],
    },
]

DEFAULT_REGISTRY = [
    {
        "name": "integrator",
        "root": ".",
        "status": "active",
        "priority": "p0",
        "entrypoint": "python -m integrator",
        "tags": ["cli", "hub", "automation"],
    },
    {
        "name": "localai",
        "root": "vault/Projects/LocalAI",
        "status": "active",
        "priority": "p0",
        "entrypoint": "LocalAI/assistant",
        "tags": ["rag", "kb", "ssot"],
    },
    {
        "name": "localai-assistant",
        "root": "LocalAI/assistant",
        "status": "active",
        "priority": "p0",
        "entrypoint": "python LocalAI/assistant/mcp_server.py",
        "tags": ["assistant", "mcp", "rag"],
    },
    {
        "name": "vpn-manager",
        "root": "vault/Projects/vpn-manager",
        "status": "active",
        "priority": "p2",
        "entrypoint": "vault/Projects/vpn-manager",
        "tags": ["vpn", "fedora", "cpp"],
    },
]
