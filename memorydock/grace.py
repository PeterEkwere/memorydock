"""Adapter over Grace's installed Python memory implementation, not a replacement engine.

Only explicitly allowed methods are reachable. All writes target a separate Store.
No model-supplied scope, SQL, filesystem path, command, or transport metadata.
"""
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

from .storage import now


def load(root):
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('grace_autonomy_dock', Path(root) / 'grace-autonomy.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GraceMemory:
    def __init__(self, state, code='/opt/grace/bin'):
        self.state = Path(state)
        self.module = load(code)
        self.store = self.module.Store(self.state / 'memory', 'grace')
        self.allowed = {'knowledge_save', 'knowledge_forget', 'procedure_read', 'procedure_propose', 'work_get'}

    def tools(self):
        result = [t for t in self.store.tools if t['name'] in self.allowed]
        result.append(self.module.schema('semantic_recall', 'Search Grace semantic knowledge using her installed bounded lexical retriever. Returns facts, not proof of influence on the answer.', {'query': {'type': 'string', 'maxLength': 200}}, ['query']))
        result.append(self.module.schema('memory_inventory', 'List demonstration memory keys, episode task IDs, and procedure names. All records are isolated fixtures or labelled read-only snapshots.', {}, []))
        return result

    def inventory(self):
        db = self.store.db
        return {'semantic': [dict(r) for r in db.execute('SELECT * FROM knowledge ORDER BY updated_at DESC LIMIT 50')],
                'episodic': [dict(r) for r in db.execute('SELECT * FROM tasks ORDER BY updated_at DESC LIMIT 50')],
                'procedural': [dict(r) for r in db.execute('SELECT * FROM procedures ORDER BY name,version DESC LIMIT 50')],
                'implementation': 'Grace installed scoped_memory.py / grace-autonomy.py / learning_procedures.py',
                'scope': 'Isolated demonstration; not the owner’s production conversations',
                'retrieval': 'Bounded lexical overlap; up to 300 candidates, 12 results, 5500-character budget; no vector search',
                'context_inclusion': 'Tool results returned to Grace; full assembled model prompt is not instrumented'}

    def call(self, name, args):
        if not isinstance(args, dict):
            raise ValueError('Arguments must be an object')
        args = dict(args)
        args.pop('_transport_provenance', None)
        if name == 'memory_inventory':
            if args: raise ValueError('No arguments expected')
            return self.inventory()
        if name == 'semantic_recall':
            if set(args) != {'query'} or not isinstance(args['query'], str) or len(args['query']) > 200:
                raise ValueError('Provide query of at most 200 characters')
            import scoped_memory
            with self.store.db:
                rows = scoped_memory.retrieve(self.store.db, args['query'], now())
            terms = scoped_memory.tokens(args['query'])
            return {'records': rows, 'method': 'Grace bounded lexical retrieval',
                    'matches': [{'key': r['key'], 'word_overlap': len(terms & scoped_memory.tokens(r['key'] + ' ' + r['claim']))} for r in rows],
                    'caveat': 'Zero-overlap facts can still be returned; a retrieval result is not a relevance guarantee.'}
        if name not in self.allowed:
            raise ValueError('Tool not enabled in this presentation scope')
        before = None
        if name in {'knowledge_save', 'knowledge_forget'}:
            before = self.store.rows('SELECT * FROM knowledge WHERE key=?', (args.get('key'),))
        result = self.store.call(name, args)
        if before is not None:
            result = {**result, 'before': before,
                      'after': self.store.rows('SELECT * FROM knowledge WHERE key=?', (args.get('key'),)),
                      'write_evidence': 'Database read after successful Grace store transaction'}
        return result

    def seed(self, live_db=None):
        db = self.store.db
        if db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0] == 0:
            self.call('knowledge_save', {'key': 'demo.presentation.style', 'kind': 'explicit_preference',
                'claim': 'For the MemoryDock demonstration, the presenter prefers short answers with concrete examples.',
                'source_ref': 'fixture:memorydock-presentation', 'confidence': 'explicit'})
        with db:
            db.execute('INSERT OR IGNORE INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)', ('demo-rehearsal',
                'MemoryDock rehearsal', 'Explain the three memory types', 'completed', '',
                'DEMO FIXTURE: the rehearsal showed that a keyword mismatch can return irrelevant facts.',
                None, 'fixture:memorydock-rehearsal', None, now()))
        if live_db:
            source = sqlite3.connect('file:' + str(live_db) + '?mode=ro', uri=True)
            source.row_factory = sqlite3.Row
            rows = source.execute("SELECT * FROM procedures WHERE name='repeated_local_identifier_lookup'").fetchall()
            with db:
                for r in rows:
                    db.execute('INSERT OR IGNORE INTO procedures VALUES(?,?,?,?,?,?,?,?)', tuple(r))
            snapshot = {'captured_at': now(), 'source': 'Grace production — read-only inventory and selected procedure snapshot',
                'counts': {t: source.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in ('knowledge', 'tasks', 'procedures', 'learning')},
                'copied_procedure': 'repeated_local_identifier_lookup', 'copied_versions': len(rows),
                'private_conversations_copied': False}
            (self.state / 'snapshot.json').write_text(json.dumps(snapshot, indent=2))
            source.close()

    def close(self):
        self.store.db.close()
