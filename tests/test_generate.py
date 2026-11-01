"""Modular tests for generate.py (prompting, API mocks, pipeline parameters)."""
import os
import unittest
from unittest.mock import patch
from PIL import Image

import generate
from utils import build_prompt

class TestGenerateModule(unittest.TestCase):
    def test_palette_and_prompt_reach_provider(self):
        brief = build_prompt('Bedroom', 'Modern', '#123456', 'Keep my desk', '#abcdef', '#654321')
        with patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), \
             patch.object(generate, 'get_api_key', return_value='test-key'), \
             patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}), \
             patch.object(generate, '_call_stability_structure_api', return_value=Image.new('RGB', (64, 64))) as api:
            results = generate.generate_redesign_variations(
                Image.new('RGB', (640, 480)), prompt=brief, count=2, strength=0.4
            )
            self.assertEqual(len(results), 2)
            for call in api.call_args_list:
                self.assertEqual(call.kwargs['prompt'], brief)
                self.assertIn('#123456', call.kwargs['prompt'])
                self.assertIn('Keep my desk', call.kwargs['prompt'])
                self.assertAlmostEqual(call.kwargs['control_strength'], 1.0)
            self.assertNotEqual(api.call_args_list[0].kwargs['seed'], api.call_args_list[1].kwargs['seed'])

    def test_local_prompt_reaches_pipeline(self):
        from types import SimpleNamespace
        brief = build_prompt('Kitchen', 'Modern', '#123456', 'Keep the cabinets')
        image = Image.new('RGB', (640, 480))
        with patch.object(generate, '_require_supported_runtime'), \
             patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), \
             patch.dict(os.environ, {'STABILITY_API_KEY': ''}), \
             patch.object(generate, 'load_pipeline') as loader, \
             patch.object(generate, 'make_depth_control_image', return_value=image):
            loader.return_value.return_value = SimpleNamespace(images=[image])
            result = generate.generate_redesign_variations(image, prompt=brief, count=1, strength=0.4)
            self.assertEqual(len(result), 1)
            self.assertEqual(loader.return_value.call_args.kwargs['prompt'], brief)
            self.assertEqual(loader.return_value.call_args.kwargs['strength'], 0.4)

    def test_architecture_preservation_caps_transform(self):
        with patch.object(generate, '_get_device_and_dtype', return_value=('cpu', None)), \
             patch.object(generate, 'get_api_key', return_value='test-key'), \
             patch.dict(os.environ, {'STABILITY_API_KEY': 'test-key'}), \
             patch.object(generate, '_call_stability_structure_api', return_value=Image.new('RGB', (512, 512))) as api:
            generate.generate_redesign_variations(Image.new('RGB', (512, 512)), strength=0.9, count=1)
            self.assertAlmostEqual(api.call_args.kwargs['control_strength'], 0.85)
            self.assertTrue(api.call_args.kwargs['prompt'].startswith('Restyle this existing room without architectural changes.'))

    def test_get_runtime_defaults(self):
        defaults = generate.get_runtime_defaults()
        self.assertIn('backend', defaults)
        self.assertIn('device', defaults)
        self.assertIn('num_inference_steps', defaults)

if __name__ == '__main__':
    unittest.main()
