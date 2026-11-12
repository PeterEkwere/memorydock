import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlparse

from .grace import GraceMemory
from .runner import run
from .storage import TraceStore


def serve(args):
    store = TraceStore(args.state)
    lock = threading.Lock()
    static = Path(__file__).parent / 'static'
    # A crashed process cannot leave old runs looking live forever.
    with store.connect() as db:
        db.execute("UPDATE runs SET status='failed',response='Server restarted before completion; inspect saved events.' WHERE status='running'")

    class Handler(BaseHTTPRequestHandler):
        def send(self, data, status=200, mime='application/json'):
            body = json.dumps(data, ensure_ascii=False).encode() if mime == 'application/json' else data
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{args.port}', f'localhost:{args.port}'}

        def do_GET(self):
            if not self.valid_host(): return self.send({'error': 'Invalid host'}, 403)
            path = urlparse(self.path).path
            if path == '/api/runs': return self.send(store.runs())
            if path.startswith('/api/runs/'):
                rid = path.split('/')[-1]
                if len(rid) != 32 or any(c not in '0123456789abcdef' for c in rid): return self.send({}, 400)
                return self.send({'events': store.events(rid)})
            if path == '/api/memory':
                memory = GraceMemory(args.state, args.grace_code)
                try: data = memory.inventory()
                finally: memory.close()
                snap = Path(args.state) / 'snapshot.json'
                data['snapshot'] = json.loads(snap.read_text()) if snap.exists() else None
                return self.send(data)
            if path == '/api/health':
                return self.send({'ready': Path(args.grace_config).exists(), 'transport': 'MCP stdio', 'agent': 'Grace', 'busy': lock.locked(), 'agents': store.docked_agents()})
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if path in files:
                name, mime = files[path]
                return self.send((static / name).read_bytes(), mime=mime)
            self.send({'error': 'Not found'}, 404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self.valid_host() or origin not in {f'http://127.0.0.1:{args.port}', f'http://localhost:{args.port}'}:
                return self.send({'error': 'Same-origin browser request required'}, 403)
            if self.path != '/api/runs': return self.send({}, 404)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 16000: raise ValueError()
                payload = json.loads(self.rfile.read(size))
                prompt = payload['prompt']
                if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000: raise ValueError()
            except (ValueError, KeyError, TypeError): return self.send({'error': 'Enter a prompt of 1–4000 characters'}, 400)
            if not lock.acquire(blocking=False): return self.send({'error': 'Grace is already running a prompt'}, 409)
            rid = store.start(prompt.strip())
            def worker():
                try: run(args.state, rid, prompt.strip(), args.grace_config, args.grace_code, args.binary)
                finally: lock.release()
            threading.Thread(target=worker, daemon=True).start()
            self.send({'id': rid}, 202)

        def log_message(self, *_): pass

    print(f'MemoryDock: http://127.0.0.1:{args.port}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
