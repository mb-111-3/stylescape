"""Shared runtime settings. Read saved keys per request, including across app processes."""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().with_name('.env')


def read_env(path=None):
    path = Path(path) if path is not None else ENV_PATH
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        name = name.strip().removeprefix('export ').strip()
        value = value.strip()
        if value.startswith(('"', "'")):
            quote = value[0]
            end = value.find(quote, 1)
            if end >= 0:
                value = value[1:end]
        else:
            value = value.split(' #', 1)[0].strip()
        values[name] = value
    return values


def get_api_key():
    # An explicitly saved value wins over an inherited, stale process value.
    return read_env().get('STABILITY_API_KEY', os.getenv('STABILITY_API_KEY', '')).strip()


def get_admin_password():
    return read_env().get('STYLESCAPE_ADMIN_PASSWORD', '').strip() or os.getenv('STYLESCAPE_ADMIN_PASSWORD', '').strip() or '123456'
