import json
import tempfile
import unittest
from pathlib import Path
import tomllib

from memorydock.runner import toml_value
from memorydock.storage import TraceStore


class CoreTests(unittest.TestCase):
    def test_replay_preserves_order_and_payload(self):
        with tempfile.TemporaryDirectory() as root:
            store = TraceStore(root)
            rid = store.start('What did I prefer?')
            store.event(rid, 'semantic', 'returned', {'value': 'café\n"quoted"'})
            store.finish(rid, 'A response')
            reopened = TraceStore(root)
            events = reopened.events(rid)
            self.assertEqual([e['stage'] for e in events], ['prompt', 'semantic', 'response'])
            self.assertEqual(events[1]['payload']['value'], 'café\n"quoted"')
            self.assertEqual(reopened.runs()[0]['status'], 'completed')
            self.assertEqual(reopened.events("' OR 1=1--"), [])

    def test_toml_nested_provider_data_roundtrip(self):
        value = {'models': {'test.key': {'base_url': 'https://example.test', 'enabled': True,
                 'args': ['a', 'b\n"c"'], 'cost': 0.5, 'empty': {}}}}
        self.assertEqual(tomllib.loads('config = ' + toml_value(value))['config'], value)

    def test_failed_run_remains_replayable(self):
        with tempfile.TemporaryDirectory() as root:
            store = TraceStore(root)
            rid = store.start('test')
            store.event(rid, 'connection', 'MCP ready', {})
            store.finish(rid, 'Timed out', True)
            self.assertEqual(store.runs()[0]['status'], 'failed')
            self.assertEqual(len(store.events(rid)), 3)


if __name__ == '__main__': unittest.main()
