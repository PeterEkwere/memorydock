import datetime
import json
import sqlite3
import uuid
from pathlib import Path


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class TraceStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,prompt TEXT,status TEXT,response TEXT,created TEXT);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,run_id TEXT,stage TEXT,title TEXT,payload TEXT,created TEXT);
            ''')

    def connect(self):
        db = sqlite3.connect(self.root / 'traces.sqlite3', timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def start(self, prompt):
        rid = uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES(?,?,?,?,?)', (rid, prompt, 'running', '', now()))
        self.event(rid, 'prompt', 'Prompt submitted', {'prompt': prompt, 'agent': 'Grace', 'scope': 'isolated presentation'})
        return rid

    def event(self, rid, stage, title, payload):
        with self.connect() as db:
            db.execute('INSERT INTO events(run_id,stage,title,payload,created) VALUES(?,?,?,?,?)',
                       (rid, stage, title, json.dumps(payload, ensure_ascii=False), now()))

    def finish(self, rid, response, failed=False):
        with self.connect() as db:
            db.execute('UPDATE runs SET status=?,response=? WHERE id=?', ('failed' if failed else 'completed', response, rid))
        self.event(rid, 'error' if failed else 'response', 'Run failed' if failed else 'Grace replied', {'response': response})

    def runs(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM runs ORDER BY created DESC LIMIT 50')]

    def events(self, rid):
        with self.connect() as db:
            return [{**dict(r), 'payload': json.loads(r['payload'])} for r in db.execute('SELECT * FROM events WHERE run_id=? ORDER BY id', (rid,))]
