# MemoryDock

An open-source, reusable memory layer intended for Grace and future AI agents, independent of any one model or agent framework.

**Status: research and concept stage.** This repository contains project documentation only. The memory engine, connectors and performance targets are not implemented or validated yet.

[Read the one-page overview (PDF)](docs/MemoryDock-Overview.pdf)

## What we are creating

MemoryDock aims to help agents retain facts, experiences and reusable methods, then assemble the relevant context for their current task. It separates semantic, episodic and procedural long-term memory from the temporary working context used during a task.

The proposed design uses a graph of entities and relationships linked to original source records. Retrieval would combine keyword search, meaning-based search and bounded graph traversal.

Memory maintenance would decide whether to add, supersede, remove or leave information unchanged; record validity periods and sources; and merge duplicate derived records without losing their supporting evidence. Explicit forgetting would have its own deletion and retention rules.

## How agents would connect

The goal is a stable interface for saving, recalling, tracing, correcting and forgetting memories. Planned connection options are an HTTP API, an MCP adapter and a small SDK; an agent would need to support one of these interfaces or use a thin adapter.

An integration would identify its user, agent and project, supply scoped credentials, save relevant inputs and outcomes, and retrieve context before answering. These are proposed interfaces, not currently available integrations.

Memory and search backends should remain replaceable so agents do not depend directly on a particular database or vendor. Graphiti, Zep, Mem0 and a custom implementation remain options under study; none has been selected.

## Speed and reliability

The proposed flow saves source events durably and makes them available in recent context before graph enrichment runs in the background. Retrieval would account for pending updates and corrections, with deeper deduplication outside the response path.

Save latency, graph availability, retrieval latency and recall accuracy must be measured separately before performance claims are made.

## Open source

MemoryDock is licensed under the [MIT License](LICENSE). The public repository is for code and documentation; deployed personal memories and credentials belong in private, access-controlled storage.
