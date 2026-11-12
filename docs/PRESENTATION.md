# Presenting MemoryDock with Grace

## Open it

The deployed dashboard is a separate `memorydock.service` on Grace's server. It binds only to `127.0.0.1:7777`; there is no public dashboard URL.

On the configured Mac, double-click **Launch MemoryDock.command**, or run:

```sh
sh scripts/present.sh
```

Keep that terminal open and visit **http://127.0.0.1:7777** manually. Do not start a second tunnel if one is already running. If the launcher reports that port 7777 is occupied, first try the URL: the existing tunnel may already work. Ctrl+C closes the tunnel, not the remote dashboard.

The Mac needs the existing `forefada-live` SSH configuration and key. This launcher does not install or expose credentials. Other computers need their own authorized SSH access.

## A five-minute presentation

**Opening:** “MemoryDock lets us inspect what an agent retrieves and saves. This is Grace's actual runtime and memory code, connected over MCP. We're using isolated demo records so private conversations stay private.”

1. Click **Recall a preference**, then **Run with Grace**. Watch Semantic light up. Open `semantic_recall completed` in Evidence. Show the record and its source. Explain that durable memory is available even though every run starts a fresh conversation.
2. Click **Correct a memory** and run it. Inspect `knowledge_save completed`: the confirmed before/after database records show the correction. Recall again. Explain that a write is different from merely saying “I'll remember.” The preloaded correction replay shows the original short-answer preference changing to detailed explanations. Subsequent repeats may show no change; edit the preference to a new value to demonstrate another correction.
3. Click **Past experience**. Open the Episodic event. This is a clearly labelled fixture task read through Grace's real `work_get`, not a claimed historical production conversation.
4. Click **Inspect a procedure**. Show active v1 and rejected v2. These versions are a read-only snapshot of Grace's real reviewed `repeated_local_identifier_lookup` procedure. Explain that “newer” does not mean “approved,” and reading instructions does not execute them.
5. Click **Expose a retrieval flaw**. Show zero word overlap for “penguin spacecraft.” Explain the advantage of simple inspectable retrieval and its relevance limitation. A model can reject an irrelevant returned fact; retrieval itself has not guaranteed relevance.

**Close:** “The important distinction is between memory that exists, memory that was returned, and memory that influenced an answer. This version proves the first two. It does not claim to inspect hidden reasoning or prove causal influence.”

## Replay if the model or network is slow

Select a completed run in **Replay the evidence**. Click **Replay**, **Step**, or drag the slider. These are recorded real operations, clearly labelled RECORDED REPLAY. Expand individual events to show raw evidence. **Show all** exits stepped playback. The Memory stores tab always shows current state, not reconstructed historical state.

Five initial successful model runs are saved on the server. Replay needs the dashboard connection but does not make model calls. Live model runs have a 180-second limit and are serialized; most test runs were much shorter. A disconnected browser can reconnect and recover the stored trace.

**Completely offline fallback:** on the configured Mac, double-click **Offline Replay.command** and open **http://127.0.0.1:7778**. It serves a private local export of the verified Grace demo runs, requires no server or internet, and disables new prompts. Select a run and click Replay. The export lives in `.state/replay.json` (gitignored); it is a snapshot, not a live connection. A fresh clone does not include that private export.

## Boundaries and troubleshooting

- Grace uses her installed memory implementation against `/var/lib/memorydock/memory/grace/work.sqlite3`. Production memory is not modified.
- Only selected procedure rows and aggregate counts were copied read-only from production. Facts and the past-task example are labelled fixtures.
- This is the first MemoryDock visualizer, not the planned full memory engine. No vector search, universal connector, automatic procedure approval, or full-context instrumentation is claimed.
- No production WhatsApp, email, scheduling, shell, or business tools are available to the demo agent.
- If status says Disconnected, restart the SSH tunnel. If a run fails, select a completed replay. Server diagnostics are private in `/var/lib/memorydock/runs/<id>/stderr.log`.
- Check the server with `ssh forefada-live 'systemctl status memorydock.service --no-pager'`.
- Restart only this dashboard with `ssh forefada-live 'systemctl restart memorydock.service'`. This does not restart Grace's production service; it interrupts an active demo run.
- To stop the dashboard after the presentation: `ssh forefada-live 'systemctl stop memorydock.service'`. To prevent automatic startup: `ssh forefada-live 'systemctl disable memorydock.service'`.

## What was tested

- Real Grace runtime connected to MemoryDock through MCP stdio.
- Real semantic recall, correction followed by recall, past-task lookup, active/rejected procedure lookup, and zero-overlap retrieval demonstration.
- MCP initialization, tool inventory, rejected unsupported tools/scope input, inference validation, and candidate-only procedure creation.
- Persisted event ordering, replayable failed runs, and generated TOML configuration round-trip.
- Browser assets and localhost health endpoint over the SSH tunnel. No automated browser rendering test was run.
