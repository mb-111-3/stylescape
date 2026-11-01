"""Modular tests for app.py (admin auth, UI flows, streaming redesign)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient

import app
import settings

class TestAppModule(unittest.TestCase):
    def setUp(self):
        self.settings_patch = patch('settings.ENV_PATH', Path(tempfile.gettempdir()) / 'stylescape-tests-no-env' / '.env')
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_admin_auth(self):
        with patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD': 'test_admin_pass'}):
            self.assertTrue(app.admin_auth('admin', 'test_admin_pass'))
            self.assertFalse(app.admin_auth('admin', 'wrong_pass'))
            self.assertFalse(app.admin_auth('not_admin', 'test_admin_pass'))

    def test_save_api_key_persistence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            target = Path(directory) / '.env'
            target.write_text('OTHER=value\nSTABILITY_API_KEY=old\n')
            with patch.object(app, 'ENV_PATH', target):
                value, message = app.save_api_key('test-secret-123456')
                self.assertEqual(value, '')
                self.assertIn('saved', message.lower())
                self.assertIn('OTHER=value', target.read_text())
                self.assertEqual(os.environ['STABILITY_API_KEY'], 'test-secret-123456')
                app.save_api_key('bad\nvalue')
                self.assertEqual(os.environ['STABILITY_API_KEY'], 'test-secret-123456')

    def test_validation_failure_handling(self):
        result = app.run_redesign(None, 'Bedroom', 'Modern', '#123456', '', '#abcdef', '#654321', 0.6, 10, 25, 1)
        self.assertEqual(result[0], [])
        self.assertIn('upload', result[1].lower())

    def test_partial_results_remain_visible(self):
        def partial(*args, **kwargs):
            yield Image.new('RGB', (512, 512), 'navy')
            raise RuntimeError('The Stability account has insufficient credits.')
        with tempfile.TemporaryDirectory() as tmp, \
             patch('utils.OUTPUT_DIR', tmp), \
             patch.object(app, 'save_uploaded_image'), \
             patch.object(app, 'iter_redesign_variations', side_effect=partial):
            states = list(app.stream_redesign(
                Image.new('RGB', (512, 512)), 'Bedroom', 'Modern', '#123456', '', '#abcdef', '#654321', 0.6, 10, 25, 2
            ))
            self.assertEqual(len(states[1][0]), 1)
            gallery, status, downloads, original_view, generated_view = states[-1]
            self.assertEqual(len(gallery), 1)
            self.assertEqual(gallery[0][0], downloads[0])
            self.assertTrue(Path(downloads[0]).is_file())
            self.assertIn('insufficient credits', status)

    def test_admin_auth_and_public_studio(self):
        with patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD': '123456'}):
            with TestClient(app.create_app()) as client:
                self.assertEqual(client.get('/').status_code, 200)
                self.assertEqual(client.get('/admin/config').status_code, 401)
                self.assertEqual(client.post('/admin/login', data={'username': 'admin', 'password': 'wrong'}).status_code, 400)
                self.assertEqual(client.post('/admin/login', data={'username': 'admin', 'password': '123456'}).status_code, 200)
                config = client.get('/admin/config')
                self.assertEqual(config.status_code, 200)
                self.assertNotIn(os.getenv('STABILITY_API_KEY', 'impossible-secret'), config.text)
                client.get('/admin/logout')
                self.assertEqual(client.get('/admin/config').status_code, 401)

if __name__ == '__main__':
    unittest.main()
