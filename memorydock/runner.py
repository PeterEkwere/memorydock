import copy
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tomllib

from .storage import TraceStore


def toml_value(value):
    if isinstance(value, dict):
        return '{' + ', '.join(json.dumps(k) + ' = ' + toml_value(v) for k, v in value.items()) + '}'
    if isinstance(value, list): return '[' + ', '.join(map(toml_value, value)) + ']'
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, (int, float)): return str(value)
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    raise TypeError(type(value).__name__)


def prepare(state, rid, source, code):
    """Copy provider configuration locally on server; never export secrets to browser/repo."""
    original = tomllib.loads(Path(source).read_text())
    root = Path(state) / 'runs' / rid
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    agent = copy.deepcopy(original['agents']['grace'])
    agent.update(channels=[], cron_jobs=[], delegates=[], skill_bundles=[], knowledge_bundles=[],
                 mcp_bundles=['dock'], risk_profile='dock', runtime_profile='dock')
    agent['memory'] = {'backend': 'none'}
    agent['workspace'] = {'access': {}, 'unrestricted_filesystem': False, 'read_memory_from': []}
    profile = copy.deepcopy(original['runtime_profiles']['grace'])
    profile.update(max_tool_iterations=8, max_history_messages=20, max_context_tokens=16000,
                   max_system_prompt_chars=12000, max_tool_result_chars=14000)
    names = ['semantic_recall', 'memory_inventory', 'knowledge_save', 'knowledge_forget', 'procedure_read', 'procedure_propose', 'work_get']
    tools = ['memorydock__' + n for n in names]
    config = {'schema_version': original['schema_version'], 'providers': original['providers'],
        'agents': {'grace': agent}, 'runtime_profiles': {'dock': profile},
        'risk_profiles': {'dock': {'level': 'supervised', 'workspace_only': True,
            'allowed_tools': tools, 'auto_approve': tools, 'allowed_commands': [],
            'excluded_tools': ['shell', 'file_read', 'file_write', 'memory_store', 'memory_recall', 'memory_forget'],
            'delegation_policy': {'mode': 'forbidden'}}},
        'mcp': {'deferred_loading': False, 'servers': [{'name': 'memorydock', 'transport': 'stdio',
            'command': '/usr/bin/python3', 'args': [str(Path(__file__).resolve().parents[1] / 'dock.py'),
                '--state', str(state), '--grace-code', str(code), 'mcp', '--run-id', rid], 'tool_timeout_secs': 30}]},
        'mcp_bundles': {'dock': {'servers': ['memorydock'], 'exclude': []}}}
    encoded = '\n'.join(json.dumps(k) + ' = ' + toml_value(v) for k, v in config.items()) + '\n'
    tomllib.loads(encoded)
    path = root / 'config.toml'
    path.write_text(encoded)
    path.chmod(0o600)
    for name in ('.secret_key', 'auth-profiles.json'):
        credential = Path(source).parent / name
        if credential.exists():
            shutil.copyfile(credential, root / name)
            (root / name).chmod(0o600)
    workspace = root / 'agents' / 'grace' / 'workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / 'AGENTS.md').write_text('''You are Grace, in an isolated MemoryDock presentation session.
Use the connected memorydock MCP tools for memory operations. This is your real installed
memory implementation with isolated demonstration records, not production conversations.
For questions about preferences use semantic_recall. To remember/correct a preference,
use knowledge_save with a stable key (demo.presentation.style for presentation style),
kind explicit_preference, confidence explicit, and source_ref presentation:user.
To inspect a previous event use work_get on demo-rehearsal. For procedures use
procedure_read on repeated_local_identifier_lookup. memory_inventory lists available records.
When asked to save a procedure, procedure_propose creates a candidate, never an approved method.
Never claim a write succeeded without a successful tool result. Do not claim to have executed
a procedure. Reply concisely and explain relevant memory limitations. Do not mention secrets.
''')
    (workspace / 'SOUL.md').write_text('You are Grace: warm, direct, thoughtful, and precise. Explain memory evidence plainly.')
    return root


def run(state, rid, prompt, source, code, binary):
    traces = TraceStore(state)
    try:
        config = prepare(state, rid, source, code)
        traces.event(rid, 'agent', 'Grace runtime started', {'runtime': 'ZeroClaw', 'transport': 'MCP stdio', 'memory_scope': 'isolated'})
        process = subprocess.Popen([binary, 'agent', '--config-dir', str(config), '--agent', 'grace', '-m', prompt],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
            env={**os.environ, 'NO_COLOR': '1'})
        try:
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise
        # CLI stderr can contain provider diagnostics. Retain privately, never expose credentials.
        (config / 'stderr.log').write_text(stderr)
        if process.returncode:
            traces.finish(rid, 'Grace could not complete this run. Inspect the private server log; retry or replay a saved run.', True)
        else:
            reply = re.sub(r'\x1b\[[0-9;]*m', '', stdout).strip()
            traces.finish(rid, reply or 'The runtime returned no response.', not bool(reply))
    except subprocess.TimeoutExpired:
        traces.finish(rid, 'Grace exceeded the 180-second time limit. Saved memory events remain available.', True)
    except Exception as exc:
        traces.finish(rid, 'Run could not start: ' + type(exc).__name__ + '. Check server setup.', True)
