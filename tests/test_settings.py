"""Modular tests for settings.py (reading .env, credentials, defaults)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings

class TestSettingsModule(unittest.TestCase):
    def test_read_env_parsing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / '.env'
            env_file.write_text(
                '# Comment line\n'
                'PLAIN=hello_world\n'
                'QUOTED="quoted value"\n'
                'SINGLE_QUOTED=\'single value\'\n'
                'WITH_COMMENT=my_val # inline comment\n'
                'export PREFIXED=exported_val\n'
            )
            data = settings.read_env(env_file)
            self.assertEqual(data.get('PLAIN'), 'hello_world')
            self.assertEqual(data.get('QUOTED'), 'quoted value')
            self.assertEqual(data.get('SINGLE_QUOTED'), 'single value')
            self.assertEqual(data.get('WITH_COMMENT'), 'my_val')
            self.assertEqual(data.get('PREFIXED'), 'exported_val')

    def test_get_admin_password_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD': ''}):
            env_file = Path(tmpdir) / '.env'
            env_file.write_text('')
            with patch.object(settings, 'ENV_PATH', env_file):
                self.assertEqual(settings.get_admin_password(), '123456')

    def test_get_admin_password_from_env_file(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD': ''}):
            env_file = Path(tmpdir) / '.env'
            env_file.write_text('STYLESCAPE_ADMIN_PASSWORD=custom_pass_987\n')
            with patch.object(settings, 'ENV_PATH', env_file):
                self.assertEqual(settings.get_admin_password(), 'custom_pass_987')

    def test_get_api_key_delegates_to_key_pool(self):
        with patch('key_pool.get_active_key', return_value='pool-key-abc'):
            self.assertEqual(settings.get_api_key(), 'pool-key-abc')

if __name__ == '__main__':
    unittest.main()
