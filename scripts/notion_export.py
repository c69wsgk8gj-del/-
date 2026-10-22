#!/usr/bin/env python3
"""Export one hiring-panel run to a child Notion page; no third-party packages."""
import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

API = 'https://api.notion.com/v1'
VERSION = '2025-09-03'
RECEIPT = '.notion-upload.json'
MAX_BYTES = 450_000

class ExportError(Exception):
    pass


def page_id(value):
    value = value.strip()
    if '://' in value:
        url = urlparse(value)
        host = (url.hostname or '').lower()
        if url.scheme != 'https' or not any(host == h or host.endswith('.'+h) for h in ('notion.so', 'notion.site', 'notion.com')):
            raise ExportError('Use a Notion page URL or a page UUID.')
        value = url.path.rstrip('/').rsplit('/', 1)[-1]
    match = re.search(r'([0-9a-fA-F]{32}|[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12})$', value)
    if not match:
        raise ExportError('Notion page ID is invalid; database URLs are not supported as parents.')
    return str(uuid.UUID(match.group(1)))


def chunks(text, limit=1800):
    # UTF-16 counting stays within Notion's 2000-character limit even with emoji.
    current, size = [], 0
    for char in text:
        width = len(char.encode('utf-16-le')) // 2
        if size + width > limit:
            yield ''.join(current)
            current, size = [], 0
        current.append(char)
        size += width
    if current:
        yield ''.join(current)


def block(kind, text):
    return {'object': 'block', 'type': kind, kind: {'rich_text': [{'type': 'text', 'text': {'content': text}}]}}


def markdown_blocks(text):
    result = []
    paragraph = []
    def emit(kind, value):
        for part in chunks(value):
            result.append(block(kind, part))
    def flush():
        if paragraph:
            emit('paragraph', '\n'.join(paragraph))
            paragraph.clear()
    for line in text.splitlines():
        heading = re.match(r'^(#{1,6})\s+(.*)', line)
        bullet = re.match(r'^\s*[-*+]\s+(.*)', line)
        number = re.match(r'^\s*\d+[.)]\s+(.*)', line)
        quote = re.match(r'^>\s?(.*)', line)
        if not line.strip():
            flush()
        elif heading or bullet or number or quote:
            flush()
            if heading:
                emit('heading_'+str(min(len(heading[1]), 3)), heading[2])
            elif bullet:
                emit('bulleted_list_item', bullet[1])
            elif number:
                emit('numbered_list_item', number[1])
            else:
                emit('quote', quote[1] or ' ')
        else:
            paragraph.append(line)
    flush()
    return result


def prepare(run, parent, title=None):
    run = Path(run).resolve()
    documents = []
    for name in ('PANEL.md', 'RESUME-IMPROVED.md'):
        path = run / name
        if not path.is_file():
            raise ExportError(f'Missing required result file: {name}')
        if path.stat().st_size > MAX_BYTES:
            raise ExportError(f'Result file is too large: {name}')
        text = path.read_text(encoding='utf-8')
        if not text.strip():
            raise ExportError(f'Result file is empty: {name}')
        documents.append(text)
    title = title or f'이력서 검토 · {run.name}'
    if not title.strip() or len(title.encode('utf-16-le')) // 2 > 1800:
        raise ExportError('Page title must contain 1–1800 UTF-16 characters.')
    children = []
    for label, text in zip(('심사단 평가', '수정 이력서'), documents):
        children.append(block('heading_1', label))
        children.extend(markdown_blocks(text))
    if len(children) > 100:
        # Keep the full text for long reports without unsafe multi-request appends.
        children = []
        for label, text in zip(('심사단 평가', '수정 이력서'), documents):
            children.append(block('heading_1', label))
            children.extend(block('paragraph', part) for part in chunks(text))
    if len(children) > 100:
        raise ExportError('Export exceeds 100 Notion blocks. Shorten the documents or export them separately; nothing was sent.')
    payload = {'parent': {'page_id': parent}, 'properties': {'title': {'type': 'title', 'title': [{'type': 'text', 'text': {'content': title}}]}}, 'children': children}
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    if len(encoded) > MAX_BYTES:
        raise ExportError('Export exceeds the safe 450 KB request limit; nothing was sent.')
    return payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward an Authorization header to another destination.


class Notion:
    def __init__(self, token):
        if not token:
            raise ExportError('NOTION_TOKEN is missing. Add it securely in environment settings, not in chat or command arguments.')
        self.token = token
        self.opener = build_opener(NoRedirect)

    def request(self, method, path, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        req = Request(API+path, data=data, method=method, headers={
            'Authorization': 'Bearer '+self.token,
            'Notion-Version': VERSION, 'Content-Type': 'application/json',
        })
        try:
            with self.opener.open(req, timeout=30) as response:
                return json.load(response)
        except HTTPError as exc:
            hints = {401: 'Check the integration token.', 403: 'Check API network policy and integration capabilities.', 404: 'Share this page with the API integration.', 429: 'Rate limited; retry later.'}
            # Do not print the response body, request headers, or token.
            raise ExportError(f'Notion HTTP {exc.code}. '+hints.get(exc.code, 'Request failed.')) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise ExportError('Notion request failed or response was invalid. Check network access; creation may require reconciliation before retry.') from None

    def check_parent(self, parent):
        page = self.request('GET', '/pages/'+parent)
        if page.get('object') != 'page' or page.get('archived') or page.get('in_trash'):
            raise ExportError('Parent must be an active Notion page, not a database or archived page.')
        return page


def save_receipt(path, value, exclusive=False):
    if exclusive:
        with path.open('x', encoding='utf-8') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
    else:
        tmp = path.with_suffix('.tmp')
        with tmp.open('w', encoding='utf-8') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        tmp.replace(path)


def export(run, parent, payload, digest, api):
    path = Path(run).resolve() / RECEIPT
    if path.exists():
        try:
            saved = json.loads(path.read_text())
        except (ValueError, OSError):
            raise ExportError('Upload receipt is unreadable; do not retry until it is checked.') from None
        if saved.get('status') == 'complete' and saved.get('digest') == digest and saved.get('parent') == parent:
            return saved['url'], False
        raise ExportError('This run has an existing or pending upload. Check its receipt and Notion page before changing or retrying it; duplicate creation was blocked.')
    api.check_parent(parent)
    pending = {'status': 'pending', 'parent': parent, 'digest': digest}
    try:
        save_receipt(path, pending, exclusive=True)
    except FileExistsError:
        raise ExportError('Another upload is in progress for this run.') from None
    # A single create call includes all content. No automatic POST retries.
    try:
        page = api.request('POST', '/pages', payload)
    except ExportError as exc:
        # These statuses explicitly reject creation; retry after configuration fixes is safe.
        if re.match(r'Notion HTTP (400|401|403|404|409|422|429)\.', str(exc)):
            path.unlink()
        raise
    if not page.get('id') or not page.get('url'):
        raise ExportError('Creation response was incomplete; pending receipt retained to prevent duplicates.')
    save_receipt(path, {**pending, 'status': 'complete', 'page_id': page['id'], 'url': page['url']})
    return page['url'], True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', nargs='?', type=Path)
    parser.add_argument('--parent', default=os.environ.get('NOTION_PARENT_PAGE_ID'))
    parser.add_argument('--title')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--dry-run', action='store_true', help='Validate locally without credentials or network calls.')
    group.add_argument('--check', action='store_true', help='Check API access to the parent page; writes nothing.')
    args = parser.parse_args(argv)
    try:
        parent = page_id(args.parent) if args.parent else None
        if not args.dry_run and not parent:
            raise ExportError('Set NOTION_PARENT_PAGE_ID or pass --parent with a Notion page link.')
        if args.check:
            Notion(os.environ.get('NOTION_TOKEN')).check_parent(parent)
            print('PASS: Notion parent page is readable. Insert-content permission is checked only by an actual upload.')
            return 0
        if args.run_dir is None:
            raise ExportError('Provide a hiring-panel run directory containing both result files.')
        payload, digest, size = prepare(args.run_dir, parent, args.title)
        if args.dry_run:
            print(json.dumps({'status': 'dry-run', 'blocks': len(payload['children']), 'bytes': size, 'parent_configured': bool(parent), 'network_calls': 0}, ensure_ascii=False))
        else:
            url, created = export(args.run_dir, parent, payload, digest, Notion(os.environ.get('NOTION_TOKEN')))
            print(('Created: ' if created else 'Already exported: ')+url)
        return 0
    except (ExportError, OSError, UnicodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
