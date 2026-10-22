import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('notion_export', ROOT/'scripts/notion_export.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
PARENT = '01234567-89ab-cdef-0123-456789abcdef'

class FakeNotion:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure
    def check_parent(self, parent):
        self.calls.append(('GET', parent))
    def request(self, method, path, payload):
        self.calls.append((method, path, payload))
        if self.failure:
            raise n.ExportError(self.failure)
        return {'id': PARENT, 'url': 'https://www.notion.so/'+PARENT}

class NotionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name)
        (self.run/'PANEL.md').write_text('# 평가\n\n- 근거\n> 인용\n\n본문')
        (self.run/'RESUME-IMPROVED.md').write_text('# 수정본\n\n개선 문장')

    def test_notion_urls_and_invalid_host(self):
        self.assertEqual(n.page_id('https://www.notion.so/Review-'+PARENT.replace('-', '')+'?source=copy_link'), PARENT)
        self.assertEqual(n.page_id(PARENT), PARENT)
        self.assertEqual(n.page_id('https://app.notion.com/p/'+PARENT.replace('-', '')+'?source=copy_link'), PARENT)
        for bad in ('https://notion.so.evil.com/'+PARENT, 'not-a-page', 'https://evil.com/'+PARENT):
            with self.assertRaises(n.ExportError): n.page_id(bad)

    def test_unicode_chunks_are_lossless_and_within_limit(self):
        text = '🦺안전'*2000
        parts = list(n.chunks(text))
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(p.encode('utf-16-le'))//2 <= 1800 for p in parts))

    def test_payload_preserves_reports_and_structures(self):
        payload, digest, size = n.prepare(self.run, PARENT)
        self.assertEqual(payload['parent'], {'page_id': PARENT})
        types = [b['type'] for b in payload['children']]
        self.assertIn('bulleted_list_item', types)
        self.assertIn('quote', types)
        self.assertEqual(len(digest), 64)
        self.assertLess(size, n.MAX_BYTES)

    def test_long_report_compacts_without_losing_text(self):
        text = '\n'.join('# 항목 '+str(i) for i in range(150))
        (self.run/'PANEL.md').write_text(text)
        payload, _, _ = n.prepare(self.run, PARENT)
        self.assertLessEqual(len(payload['children']), 100)
        first_document = payload['children'][1]
        self.assertEqual(first_document['paragraph']['rich_text'][0]['text']['content'], text)

    def test_missing_file_and_oversized_input_fail_before_network(self):
        (self.run/'PANEL.md').unlink()
        with self.assertRaises(n.ExportError): n.prepare(self.run, PARENT)
        (self.run/'PANEL.md').write_text('x'*(n.MAX_BYTES+1))
        with self.assertRaises(n.ExportError): n.prepare(self.run, PARENT)

    def test_export_duplicate_and_modified_run(self):
        payload, digest, _ = n.prepare(self.run, PARENT)
        api = FakeNotion()
        url, created = n.export(self.run, PARENT, payload, digest, api)
        self.assertTrue(created)
        self.assertEqual(n.export(self.run, PARENT, payload, digest, api), (url, False))
        self.assertEqual(len(api.calls), 2)
        with self.assertRaises(n.ExportError): n.export(self.run, PARENT, payload, 'changed', api)

    def test_uncertain_failure_blocks_duplicate_retry(self):
        payload, digest, _ = n.prepare(self.run, PARENT)
        with self.assertRaises(n.ExportError):
            n.export(self.run, PARENT, payload, digest, FakeNotion('Notion request failed.'))
        receipt = json.loads((self.run/n.RECEIPT).read_text())
        self.assertEqual(receipt['status'], 'pending')
        api = FakeNotion()
        with self.assertRaises(n.ExportError): n.export(self.run, PARENT, payload, digest, api)
        self.assertEqual(api.calls, [])

    def test_rejected_creation_can_retry_after_fix(self):
        payload, digest, _ = n.prepare(self.run, PARENT)
        with self.assertRaises(n.ExportError):
            n.export(self.run, PARENT, payload, digest, FakeNotion('Notion HTTP 403. Check permissions.'))
        self.assertFalse((self.run/n.RECEIPT).exists())
        self.assertTrue(n.export(self.run, PARENT, payload, digest, FakeNotion())[1])

    def test_dry_run_needs_no_secret_and_makes_no_requests(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(n, 'Notion') as api, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(n.main([str(self.run), '--dry-run']), 0)
            api.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())['network_calls'], 0)
        self.assertFalse((self.run/n.RECEIPT).exists())

    def test_token_stays_in_header_and_errors_are_redacted(self):
        client = n.Notion('fake-private-test-token')
        with patch.object(client.opener, 'open', side_effect=HTTPError('https://api.notion.com', 401, 'fake-private-test-token', {}, None)) as opener:
            with self.assertRaises(n.ExportError) as caught:
                client.request('GET', '/pages/'+PARENT)
            self.assertNotIn('fake-private-test-token', str(caught.exception))
            request = opener.call_args.args[0]
            self.assertEqual(request.get_header('Authorization'), 'Bearer fake-private-test-token')
            self.assertEqual(request.get_header('Notion-version'), n.VERSION)
        with patch.object(client.opener, 'open', side_effect=URLError('fake-private-test-token')):
            with self.assertRaises(n.ExportError) as caught: client.request('GET', '/pages/'+PARENT)
            self.assertNotIn('fake-private-test-token', str(caught.exception))
        self.assertIsNone(n.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.com'))

if __name__ == '__main__':
    unittest.main()
