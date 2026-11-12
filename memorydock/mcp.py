"""Newline-delimited JSON-RPC MCP stdio server. stdout is protocol only."""
import json
import sys
import time

from .grace import GraceMemory
from .storage import TraceStore


def serve(state, run_id, code):
    traces = TraceStore(state)
    memory = GraceMemory(state, code)
    external = run_id == 'external'
    if external:
        run_id = traces.start('External MCP client session — Grace demo memory adapter')
    for line in sys.stdin:
        req = {}
        try:
            if len(line) > 100000: raise ValueError('Request too large')
            req = json.loads(line)
            if 'id' not in req: continue
            method = req.get('method')
            if method == 'initialize':
                result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                          'serverInfo': {'name': 'memorydock-grace', 'version': '0.1.0'}}
                client_name = (req.get('params', {}).get('clientInfo', {}).get('name') or 'External agent') if external else 'Grace'
                traces.event(run_id, 'connection', client_name + ' has docked', {'protocol': '2024-11-05', 'transport': 'stdio',
                    'client': req.get('params', {}).get('clientInfo', {}), 'external': external})
            elif method == 'ping': result = {}
            elif method == 'tools/list': result = {'tools': memory.tools()}
            elif method == 'tools/call':
                name = req['params']['name']
                args = req['params'].get('arguments', {})
                stage = ('semantic' if name.startswith(('knowledge_', 'semantic_')) else
                         'procedural' if name.startswith('procedure_') else 'episodic' if name == 'work_get' else 'retrieval')
                traces.event(run_id, stage, name + ' requested', {'tool': name, 'arguments': args, 'evidence': 'Observed MCP request'})
                started = time.monotonic()
                try:
                    value = memory.call(name, args)
                    traces.event(run_id, stage, name + ' completed', {'tool': name, 'result': value,
                        'elapsed_ms': round((time.monotonic()-started)*1000, 2), 'evidence': 'Observed adapter result after operation completed'})
                    result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}
                    traces.event(run_id, 'context', 'Tool result returned to Grace', {'tool': name, 'characters': len(result['content'][0]['text']),
                        'full_prompt_observed': False, 'answer_influence': 'Unknown'})
                except Exception as exc:
                    traces.event(run_id, 'error', name + ' failed', {'error': str(exc)[:500]})
                    result = {'isError': True, 'content': [{'type': 'text', 'text': str(exc)[:500]}]}
            else:
                raise ValueError('Unsupported MCP method')
            response = {'jsonrpc': '2.0', 'id': req['id'], 'result': result}
        except Exception as exc:
            response = {'jsonrpc': '2.0', 'id': req.get('id'), 'error': {'code': -32602, 'message': str(exc)[:300]}}
        print(json.dumps(response, ensure_ascii=False), flush=True)
    memory.close()
    if external:
        traces.finish(run_id, 'External MCP session ended. The external agent’s final response is not instrumented.')
