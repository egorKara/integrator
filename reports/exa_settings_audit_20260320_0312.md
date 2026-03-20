# exa settings audit 2026-03-20 03:12

- checked config:
  - `C:\Users\egork\AppData\Roaming\Trae\User\mcp.json`
  - `Exa Search.command = npx`
  - `Exa Search.args = ["-y","exa-mcp-server"]`
  - `EXA_API_KEY` is set

- mcp tool schema in current Trae profile:
  - enabled tools: `web_search_exa`, `get_code_context_exa`
  - supported search `type` values in `web_search_exa`: `auto`, `fast`
  - `deep` / `deep-reasoning` are not exposed in current local MCP tool schema

- runtime checks (real MCP tool calls):
  - `web_search_exa` with `type=auto` -> success
  - `get_code_context_exa` -> success
  - Exa MCP connectivity is operational

- alignment with provided guide:
  - npm-based MCP setup matches guide and is working
  - guide sections about deep search and extra tools are valid for remote MCP modes, but not active in current local schema
  - to use remote-only extras, switch server transport/config to remote MCP URL profile

- security note:
  - API key appears inline in your pasted examples/URLs; rotate key if this text was shared outside trusted scope
