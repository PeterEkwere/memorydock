# MCP integration and adapter contract

## Transport

Grace is the MCP client. MemoryDock is a newline-delimited JSON-RPC MCP server over stdio. Each dashboard run starts an isolated ZeroClaw process; its configuration starts MemoryDock as an MCP subprocess. The model chooses memory tools. The server records each request, actual adapter result, and the result returned to the client. The launcher captures the agent's final response.

The browser uses a localhost web API to submit prompts and poll trace events. This is UI transport; the agent-to-memory connection is MCP, not an HTTP memory API. There is no public endpoint.

## Connecting another MCP client to the current Grace memory adapter

On a server with Grace's installed helper code, an MCP client can use this server configuration (adapt key names to the client):

```json
{
  "mcpServers": {
    "memorydock": {
      "command": "/usr/bin/python3",
      "args": [
        "/opt/memorydock/dock.py",
        "--state", "/var/lib/memorydock",
        "mcp"
      ]
    }
  }
}
```

Use an authorized OS account and a separate state directory for a different user. The initial server is single-user, not a multi-tenant service. Do not expose its SQLite files or browser port publicly.

Supported tools: `semantic_recall`, `knowledge_save`, `knowledge_forget`, `work_get`, `procedure_read`, `procedure_propose`, `memory_inventory`. Writes target the isolated demo store. The server rejects other tools. It does not expose raw SQL or model-selected scopes, filesystem paths, or commands.

## Supporting another agent's own memory implementation

MCP connectivity alone does not expose a client's internal memories. A new adapter must supply:

- `tools()`: MCP tool definitions for supported operations.
- `call(name, arguments)`: invoke the real backing implementation and return an observed result.
- `inventory()`: inspect the scoped backing stores and report retrieval limitations.
- A runner connector if prompts should launch that agent from the dashboard.

`GraceMemory` in `memorydock/grace.py` is the first concrete adapter. The current dashboard runner is Grace-specific. Connecting arbitrary agents' existing private stores without an adapter is not implemented.

Trace payloads have `run_id`, an increasing event `id`, `stage`, `title`, JSON `payload`, and UTC `created`. Stages include prompt, agent, connection, retrieval, semantic, episodic, procedural, context, response, and error. Operation results include measured elapsed milliseconds. Knowledge writes include before/after records read around the committed operation. No hidden reasoning is collected.

## Deployment

Requires Python 3.11+ and the deployed Grace runtime/helpers. The dashboard has no pip, npm, Docker, or CDN dependencies. Native JavaScript/CSS keeps the presentation lightweight and offline with respect to frontend assets. SQLite WAL stores traces. One model run at a time limits resource use. The MCP implementation supports initialization, ping, tools/list and tools/call; it is intentionally a small tool server, not every optional MCP feature.

The supplied service confines writes to `/var/lib/memorydock`, uses the existing grace OS account, and caps memory at 600 MB. Provider credentials are copied only inside protected per-run directories on the server. They never enter the repository, trace API, or browser. Grace's production configuration is read but not edited.

Tests: `python3 -m unittest discover -s tests -v`; on the Grace server also run `python3 scripts/check_grace_mcp.py` with permission to read the installed helpers. The integration test uses a temporary memory store and no model calls.
