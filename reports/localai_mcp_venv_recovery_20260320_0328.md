# localai mcp venv recovery 2026-03-20 03:28

- objective:
  - restore `LocalAI/assistant` venv for Trae MCP `localai` server

- actions:
  - removed broken venv: `C:\integrator\LocalAI\assistant\venv`
  - created new venv with Python 3.12: `py -3.12 -m venv C:\integrator\LocalAI\assistant\venv`
  - upgraded pip and installed runtime dependency for MCP server:
    - `pip install requests`

- validation:
  - `C:\integrator\LocalAI\assistant\venv\pyvenv.cfg` exists
  - `python -V` from venv works
  - MCP initialize check:
    - request: `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}`
    - response: `serverInfo.name=localai-mcp`, `version=1.0.0`
  - MCP tools/list check:
    - returned tools: `localai_search`, `localai_get_ssot`

- config status:
  - Trae config already points to restored interpreter:
    - `C:\Users\egork\AppData\Roaming\Trae\User\mcp.json`
    - `mcpServers.localai.command = C:\integrator\LocalAI\assistant\venv\Scripts\python.exe`
    - `mcpServers.localai.args = ["C:\\integrator\\LocalAI\\assistant\\mcp_server.py"]`

- next step:
  - restart Trae MCP client (or Trae IDE) to reload `mcpServers.localai`
