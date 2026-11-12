#!/usr/bin/env python3
"""Read-only presentation replay; Python 3.9+, no Grace installation or network needed."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bundle = json.loads((ROOT / '.state/replay.json').read_text())


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:7778', 'localhost:7778'):
            self.send_error(403); return
        mime = 'application/json'
        if self.path == '/api/health':
            body = json.dumps({'ready': True, 'busy': False, 'replay_only': True}).encode()
        elif self.path == '/api/runs': body = json.dumps(bundle['runs']).encode()
        elif self.path == '/api/memory': body = json.dumps(bundle['memory']).encode()
        elif self.path.startswith('/api/runs/'):
            body = json.dumps({'events': bundle['events'].get(self.path.split('/')[-1], [])}).encode()
        elif self.path in ('/', '/app.js', '/style.css'):
            name = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}[self.path]
            body = (ROOT / 'memorydock/static' / name).read_bytes()
            mime = {'/': 'text/html; charset=utf-8', '/app.js': 'text/javascript', '/style.css': 'text/css'}[self.path]
        else: self.send_error(404); return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; frame-ancestors 'none'")
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *_): pass


print('Offline MemoryDock replay: http://127.0.0.1:7778 — no live model calls. Ctrl+C to stop.', flush=True)
HTTPServer(('127.0.0.1', 7778), Handler).serve_forever()
