"""Rotating pool of Stability AI API keys.

Admins add a batch of keys. The pool hands out one "active" key at a time;
when the provider rejects a key as invalid/expired/out of credits, that key
is marked exhausted and the next active key in the pool takes over
automatically.
"""
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from settings import ENV_PATH, read_env

STORE_PATH = ENV_PATH.parent / '.settings-private' / 'keys.json'
_LOCK = Lock()


def _load():
    if not STORE_PATH.exists():
        return {'keys': [], 'active_id': None}
    try:
        data = json.loads(STORE_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {'keys': [], 'active_id': None}
    data.setdefault('keys', [])
    data.setdefault('active_id', None)
    return data


def _save(data):
    STORE_PATH.parent.mkdir(exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=STORE_PATH.parent, prefix='.keys-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(STORE_PATH)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink(missing_ok=True)


def _pick_next_active(data):
    """Choose the oldest-added key still marked active and make it the current one."""
    candidates = [entry for entry in data['keys'] if entry['status'] == 'active']
    candidates.sort(key=lambda entry: entry['added_at'])
    data['active_id'] = candidates[0]['id'] if candidates else None
    return data['active_id']


def add_keys(keys_text):
    """Add one or more newline-separated keys to the pool."""
    raw_lines = [line.strip() for line in (keys_text or '').splitlines()]
    candidates = [line for line in raw_lines if line]
    if not candidates:
        return 'Paste at least one API key, one per line.'
    for key in candidates:
        if len(key) < 10 or any(c.isspace() for c in key) or any(c in key for c in "'\"#="):
            return f'"{key[:6]}..." is not a valid key (no spaces or quotes). Nothing was added.'
    with _LOCK:
        data = _load()
        existing = {entry['key'] for entry in data['keys']}
        added = 0
        for key in candidates:
            if key in existing:
                continue
            data['keys'].append({
                'id': uuid.uuid4().hex,
                'key': key,
                'used_count': 0,
                'status': 'active',
                'added_at': datetime.now(timezone.utc).isoformat(),
            })
            existing.add(key)
            added += 1
        if data['active_id'] is None:
            _pick_next_active(data)
        _save(data)
    skipped = len(candidates) - added
    message = f'Added {added} key(s) to the pool.'
    if skipped:
        message += f' Skipped {skipped} duplicate(s) already in the pool.'
    return message


def get_active_key():
    """Return the key that should be used for the next request, rotating if needed."""
    with _LOCK:
        data = _load()
        if not data['keys']:
            # No pool configured yet: fall back to the legacy single .env key.
            return read_env().get('STABILITY_API_KEY', os.getenv('STABILITY_API_KEY', '')).strip()
        active = next((entry for entry in data['keys'] if entry['id'] == data['active_id']), None)
        if active is None or active['status'] != 'active':
            _pick_next_active(data)
            active = next((entry for entry in data['keys'] if entry['id'] == data['active_id']), None)
            _save(data)
        return active['key'] if active else ''


def record_use(key):
    """Call after a request goes out successfully on `key`, for display purposes only."""
    if not key:
        return
    with _LOCK:
        data = _load()
        entry = next((entry for entry in data['keys'] if entry['key'] == key), None)
        if entry is None:
            return
        entry['used_count'] += 1
        _save(data)


def mark_expired(key):
    """Call when the provider rejects `key` as invalid/expired/out of credits; rotates to the next key."""
    if not key:
        return
    with _LOCK:
        data = _load()
        entry = next((entry for entry in data['keys'] if entry['key'] == key), None)
        if entry is None:
            return
        entry['status'] = 'exhausted'
        if data['active_id'] == entry['id']:
            _pick_next_active(data)
        _save(data)


def list_keys():
    """Return masked, display-ready info about every key in the pool."""
    with _LOCK:
        data = _load()
        return [{
            'masked': f"...{entry['key'][-4:]}",
            'used_count': entry['used_count'],
            'status': 'current' if entry['id'] == data['active_id'] else entry['status'],
            'added_at': entry['added_at'],
        } for entry in sorted(data['keys'], key=lambda entry: entry['added_at'])]


def has_any_key():
    with _LOCK:
        data = _load()
        return bool(data['keys'])
