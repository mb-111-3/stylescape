"""Modular tests for utils.py (validation, prompt building, and image processing)."""
import unittest
from PIL import Image
from utils import (
    ROOM_TYPES,
    STYLES,
    WALL_COLORS,
    ValidationError,
    build_prompt,
    resize_for_sdxl,
    validate_inputs,
)

class TestUtilsModule(unittest.TestCase):
    def test_build_prompt_contains_all_components(self):
        prompt = build_prompt(
            room_type='Living Room',
            style='Modern',
            wall_color='#E8DDCC',
            custom_prompt='Add a low bookshelf',
            secondary='#A87652',
            accent='#536451',
        )
        self.assertIn('Living Room', prompt)
        self.assertIn('Modern', prompt)
        self.assertIn('#E8DDCC', prompt)
        self.assertIn('Add a low bookshelf', prompt)
        self.assertIn('#A87652', prompt)
        self.assertIn('#536451', prompt)

    def test_validate_inputs_valid(self):
        valid_img = Image.new('RGB', (512, 512), 'white')
        validate_inputs(valid_img, ROOM_TYPES[0], STYLES[0], '#E8DDCC')
        validate_inputs(valid_img, 'Bedroom', 'South Indian', 'Beige')

    def test_validate_inputs_missing_image(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(None, 'Bedroom', 'Modern', '#E8DDCC')
        self.assertIn('upload a room image', str(ctx.exception).lower())

    def test_validate_inputs_invalid_room(self):
        valid_img = Image.new('RGB', (512, 512), 'white')
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(valid_img, 'Dungeon', 'Modern', '#E8DDCC')
        self.assertIn('invalid room type', str(ctx.exception).lower())

    def test_validate_inputs_invalid_style(self):
        valid_img = Image.new('RGB', (512, 512), 'white')
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(valid_img, 'Bedroom', 'NonExistentStyle', '#E8DDCC')
        self.assertIn('invalid style', str(ctx.exception).lower())

    def test_validate_inputs_invalid_wall_color(self):
        valid_img = Image.new('RGB', (512, 512), 'white')
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(valid_img, 'Bedroom', 'Modern', 'invalid-color-123')
        self.assertIn('invalid wall color', str(ctx.exception).lower())

    def test_validate_inputs_image_too_small(self):
        tiny_img = Image.new('RGB', (100, 100), 'white')
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(tiny_img, 'Bedroom', 'Modern', '#E8DDCC')
        self.assertIn('at least 256 pixels', str(ctx.exception).lower())

    def test_resize_for_sdxl(self):
        original = Image.new('RGB', (1200, 600), 'red')
        original.paste('blue', (0, 0, 100, 600))
        result = resize_for_sdxl(original)
        self.assertEqual(result.size, (1024, 512))
        self.assertEqual(result.getpixel((0, 0)), (0, 0, 255))

if __name__ == '__main__':
    unittest.main()
