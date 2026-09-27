import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
import app
import generate
from utils import build_prompt, resize_for_sdxl

class StudioTests(unittest.TestCase):
    def setUp(self):
        # Isolate tests from the user's real credentials and .env contents.
        self.settings_patch = patch('settings.ENV_PATH', Path(tempfile.gettempdir()) / 'stylescape-tests-no-env' / '.env')
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_saved_key_overrides_stale_environment(self):
        import settings
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'STABILITY_API_KEY': 'stale-key'}):
            target = Path(directory) / '.env'
            target.write_text('OTHER=value\nSTABILITY_API_KEY=previous-key\n')
            with patch.object(app, 'ENV_PATH', target), patch.object(settings, 'ENV_PATH', target):
                app.save_api_key('new-dynamic-key-123')
                os.environ['STABILITY_API_KEY'] = 'stale-other-server-key'
                self.assertEqual(settings.get_api_key(), 'new-dynamic-key-123')
                target.write_text('STABILITY_API_KEY="edited-key-456" # comment\n')
                self.assertEqual(settings.get_api_key(), 'edited-key-456')

    def test_blank_admin_password_uses_requested_default(self):
        import settings
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD': ''}):
            target = Path(directory) / '.env'
            target.write_text('STYLESCAPE_ADMIN_PASSWORD=\n')
            with patch.object(settings, 'ENV_PATH', target):
                self.assertTrue(app.admin_auth('admin', '123456'))
                self.assertFalse(app.admin_auth('admin', 'wrong'))

    def test_palette_and_prompt_reach_provider(self):
        brief = build_prompt('Bedroom', 'Minimal', '#123456', 'Keep my desk', '#abcdef', '#654321')
        with patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), patch.dict(os.environ, {'STABILITY_API_KEY':'test-key'}), patch.object(generate, '_call_stability_structure_api', return_value=Image.new('RGB',(64,64))) as api:
            results = generate.generate_redesign_variations(Image.new('RGB',(640,480)), prompt=brief, count=2, strength=.4)
            self.assertEqual(len(results), 2)
            for call in api.call_args_list:
                self.assertEqual(call.kwargs['prompt'], brief)
                self.assertIn('#123456', call.kwargs['prompt'])
                self.assertIn('Keep my desk', call.kwargs['prompt'])
                self.assertAlmostEqual(call.kwargs['control_strength'], .9)
            self.assertNotEqual(api.call_args_list[0].kwargs['seed'], api.call_args_list[1].kwargs['seed'])

    def test_local_prompt_reaches_pipeline(self):
        from types import SimpleNamespace
        brief = build_prompt('Kitchen', 'Modern', '#123456', 'Keep the cabinets')
        image = Image.new('RGB', (640, 480))
        with patch.object(generate, '_require_supported_runtime'), patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), patch.dict(os.environ, {'STABILITY_API_KEY': ''}), patch.object(generate, 'load_pipeline') as loader, patch.object(generate, 'make_depth_control_image', return_value=image):
            loader.return_value.return_value = SimpleNamespace(images=[image])
            result = generate.generate_redesign_variations(image, prompt=brief, count=1, strength=.4)
            self.assertEqual(len(result), 1)
            self.assertEqual(loader.return_value.call_args.kwargs['prompt'], brief)
            self.assertEqual(loader.return_value.call_args.kwargs['strength'], .4)

    def test_partial_results_remain_visible_and_downloadable(self):
        def partial(*args, **kwargs):
            yield Image.new('RGB', (512,512), 'navy')
            raise RuntimeError('The Stability account has insufficient credits.')
        with tempfile.TemporaryDirectory() as tmp, patch('utils.OUTPUT_DIR', tmp), patch.object(app, 'save_uploaded_image'), patch.object(app, 'iter_redesign_variations', side_effect=partial):
            states = list(app.stream_redesign(Image.new('RGB',(512,512)), 'Bedroom', 'Minimal', '#123456', '', '#abcdef', '#654321', .6, 10, 25, 2))
            self.assertEqual(len(states[1][0]), 1)
            gallery, status, downloads = states[-1]
            self.assertEqual(len(gallery), 1)
            self.assertEqual(gallery[0][0], downloads[0])
            self.assertTrue(Path(downloads[0]).is_file())
            self.assertIn('insufficient credits', status)

    def test_gallery_image_can_be_fetched(self):
        import asyncio
        import gradio as gr
        from urllib.parse import quote
        with tempfile.TemporaryDirectory() as tmp, patch('utils.OUTPUT_DIR', tmp), patch.object(app, 'save_uploaded_image'), patch.object(app, 'iter_redesign_variations', return_value=iter([Image.new('RGB', (512,512), 'navy')])):
            gallery, status, downloads = app.run_redesign(Image.new('RGB',(512,512)), 'Bedroom', 'Minimal', '#123456', '', '#abcdef', '#654321', .6, 10, 25, 1)
            demo = app.build_interface()
            component = next(c for c in demo.blocks.values() if isinstance(c, gr.Gallery))
            data = component.postprocess(gallery).model_dump()
            from gradio.processing_utils import async_move_files_to_cache
            cached = asyncio.run(async_move_files_to_cache(data, component, postprocess=True))
            from fastapi import FastAPI
            with TestClient(gr.mount_gradio_app(FastAPI(), demo, path='/')) as client:
                response = client.get(quote(cached[0]['image']['url'], safe='/:='))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.headers['content-type'].startswith('image/'))

    def test_architecture_preservation_caps_transform(self):
        with patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}), patch.object(generate, '_call_stability_structure_api', return_value=Image.new('RGB', (512,512))) as api:
            generate.generate_redesign_variations(Image.new('RGB', (512,512)), strength=.9, count=1)
            self.assertAlmostEqual(api.call_args.kwargs['control_strength'], .85)
            self.assertTrue(api.call_args.kwargs['prompt'].startswith('Restyle this existing room without architectural changes.'))

    def test_full_frame(self):
        original = Image.new('RGB', (1200,600), 'red')
        original.paste('blue', (0,0,100,600))
        result = resize_for_sdxl(original)
        self.assertEqual(result.size, (1024,512))
        self.assertEqual(result.getpixel((0,0)), (0,0,255))

    def test_key_persistence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            target = Path(directory) / '.env'
            target.write_text('OTHER=value\nSTABILITY_API_KEY=old\n')
            with patch.object(app, 'ENV_PATH', target):
                value, message = app.save_api_key('test-secret-123456')
                self.assertEqual(value, '')
                self.assertIn('saved', message)
                self.assertIn('OTHER=value', target.read_text())
                self.assertEqual(os.environ['STABILITY_API_KEY'], 'test-secret-123456')
                app.save_api_key('bad\nvalue')
                self.assertEqual(os.environ['STABILITY_API_KEY'], 'test-secret-123456')

    def test_validation(self):
        result = app.run_redesign(None, 'Bedroom', 'Minimal', '#123456', '', '#abcdef', '#654321', .6, 10, 25, 1)
        self.assertEqual(result[0], [])
        self.assertIn('upload', result[1])

    def test_admin_auth_and_public_studio(self):
        with patch.dict(os.environ, {'STYLESCAPE_ADMIN_PASSWORD':'123456'}):
            with TestClient(app.create_app()) as client:
                self.assertEqual(client.get('/').status_code, 200)
                self.assertEqual(client.get('/admin/config').status_code, 401)
                self.assertEqual(client.post('/admin/login', data={'username':'admin','password':'wrong'}).status_code, 400)
                self.assertEqual(client.post('/admin/login', data={'username':'admin','password':'123456'}).status_code, 200)
                config = client.get('/admin/config')
                self.assertEqual(config.status_code, 200)
                self.assertNotIn(os.getenv('STABILITY_API_KEY', 'impossible-secret'), config.text)
                client.get('/admin/logout')
                self.assertEqual(client.get('/admin/config').status_code, 401)

if __name__ == '__main__':
    unittest.main()
