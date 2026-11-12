#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

os.umask(0o077)
p = argparse.ArgumentParser(description='MemoryDock presentation visualizer and MCP stdio server')
p.add_argument('--state', default=str(Path.home() / '.local/share/memorydock'))
p.add_argument('--grace-code', default='/opt/grace/bin')
sub = p.add_subparsers(dest='command', required=True)
m = sub.add_parser('mcp'); m.add_argument('--run-id', default='external')
s = sub.add_parser('serve')
s.add_argument('--port', type=int, default=7777)
s.add_argument('--grace-config', default='/var/lib/grace/runtime/config.toml')
s.add_argument('--binary', default='/opt/grace/bin/zeroclaw')
i = sub.add_parser('seed'); i.add_argument('--live-db')
a = p.parse_args()
if a.command == 'mcp':
    from memorydock.mcp import serve
    serve(a.state, a.run_id, a.grace_code)
elif a.command == 'serve':
    from memorydock.server import serve
    serve(a)
else:
    from memorydock.grace import GraceMemory
    memory = GraceMemory(a.state, a.grace_code)
    memory.seed(a.live_db)
    memory.close()
    print('Isolated Grace demo memory ready.')
