"""Run on Grace's server. Temporary isolated data; no model/API cost."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from memorydock.grace import GraceMemory

with tempfile.TemporaryDirectory() as state:
    memory = GraceMemory(state)
    memory.seed()
    memory.close()
    process = subprocess.Popen([sys.executable, str(ROOT/'dock.py'), '--state', state, 'mcp', '--run-id', 'test'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    counter = 0
    def rpc(method, params=None):
        global counter
        counter += 1
        process.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': counter, 'method': method, 'params': params or {}})+'\n')
        process.stdin.flush()
        return json.loads(process.stdout.readline())['result']
    def call(name, arguments):
        return rpc('tools/call', {'name': name, 'arguments': arguments})
    try:
        assert rpc('initialize')['serverInfo']['name']=='memorydock-grace'
        names={t['name'] for t in rpc('tools/list')['tools']}
        assert names=={'knowledge_save','knowledge_forget','semantic_recall','memory_inventory','work_get','procedure_read','procedure_propose'}
        save={'key':'demo.test','kind':'explicit_preference','claim':'I prefer blue','source_ref':'test:user','confidence':'explicit'}
        assert not call('knowledge_save',save).get('isError')
        save['claim']='I prefer green'
        assert not call('knowledge_save',save).get('isError')
        recalled=json.loads(call('semantic_recall',{'query':'prefer'})['content'][0]['text'])
        assert [r['claim'] for r in recalled['records'] if r['key']=='demo.test']==['I prefer green']
        assert call('semantic_recall',{'query':'x','scope':'production'}).get('isError')
        assert call('shell',{'command':'whoami'}).get('isError')
        assert call('knowledge_save',{**save,'kind':'inference','confidence':'explicit'}).get('isError')
        episode=json.loads(call('work_get',{'task_id':'demo-rehearsal'})['content'][0]['text'])
        assert 'demo-rehearsal' in json.dumps(episode)
        candidate=call('procedure_propose',{'name':'demo-method','instructions':'Read sources before answering','use_when':'Demo','source_ref':'test:user'})
        assert json.loads(candidate['content'][0]['text'])['status']=='candidate'
        assert call('procedure_review',{}).get('isError')
        print('PASS: MCP handshake, tool allowlist, correction, recall, episode, candidate-only procedure, scope and authority rejection')
    finally:
        process.stdin.close()
        process.wait(timeout=10)
