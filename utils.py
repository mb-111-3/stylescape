"""
utils.py
--------
Utility functions for StyleScape-MVP.

Responsibilities:
- Validate user inputs (room image, room type, style, wall color).
- Build a high-quality Stable Diffusion prompt from the selected options
  and any optional custom prompt text.
- Provide filesystem helpers for saving uploaded / generated images.
"""

import os
import uuid
from datetime import datetime

from PIL import Image, ImageOps
import re

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

ROOM_TYPES = ["Living Room", "Bedroom", "Kitchen", "Bathroom"]

STYLES = ["Modern", "Minimal", "Luxury", "Scandinavian", "Contemporary Indian"]

PALETTES = {
    "Warm sanctuary": ("#E8DDCC", "#A87652", "#536451"),
    "Coastal calm": ("#E8F0F2", "#7095A5", "#D6C2A3"),
    "Earth & clay": ("#D9B6A3", "#9C614B", "#646B50"),
    "Quiet luxury": ("#EAE5DC", "#8B8178", "#393C39"),
    "Forest retreat": ("#CBD2C1", "#52644E", "#B89570"),
    "Custom": ("#E8DDCC", "#A87652", "#536451"),
}

WALL_COLORS = ["White", "Beige", "Blue", "Green", "Grey"]

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

# Descriptive fragments used to enrich the auto-generated prompt.
STYLE_DESCRIPTIONS = {
    "Modern": (
        "modern interior design, sleek clean lines, contemporary furniture, "
        "polished surfaces, balanced decorative accents, "
        "designer lighting fixtures"
    ),
    "Minimal": (
        "minimalist interior design, uncluttered space, simple geometric forms, "
        "functional furniture, hidden storage, soft neutral tones, calm and airy atmosphere"
    ),
    "Luxury": (
        "luxury interior design, opulent finishes, marble and gold accents, "
        "elegant chandeliers, plush upholstered furniture, high-end materials, "
        "rich textures, five-star hotel ambiance"
    ),
    "Scandinavian": (
        "scandinavian interior design, light wood furniture, cozy textiles, "
        "hygge atmosphere, soft natural lighting, white and pastel tones, "
        "functional and warm minimalism"
    ),
    "Contemporary Indian": (
        "contemporary Indian interior design, warm earthy tones, handcrafted wooden "
        "furniture, brass and terracotta accents, traditional textile patterns, "
        "modern fusion of Indian heritage and contemporary comfort"
    ),
}

ROOM_TYPE_DESCRIPTIONS = {
    "Living Room": "spacious living room with sofa, coffee table, and entertainment area",
    "Bedroom": "comfortable bedroom with bed, nightstands, and soft ambient lighting",
    "Kitchen": "functional kitchen with countertops, cabinetry, and modern appliances",
    "Bathroom": "clean bathroom with vanity, fixtures, and elegant tiling",
}

WALL_COLOR_DESCRIPTIONS = {
    "White": "crisp white painted walls",
    "Beige": "warm beige painted walls",
    "Blue": "calm soft blue painted walls",
    "Green": "fresh sage green painted walls",
    "Grey": "sophisticated grey painted walls",
}

NEGATIVE_PROMPT = (
    "blurry, low quality, distorted proportions, watermark, text, logo, "
    "extra furniture floating, unrealistic lighting, deformed walls, moved windows, extra windows, missing doors, new doorways, "
    "swapped doors, mirrored layout, changed floor plan, altered ceiling height, different camera angle, "
    "removed built-in cabinetry, moved kitchen cabinets, changed countertops, altered bathroom fixtures, "
    "cluttered, dark, noisy, low resolution"
)


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when user-provided inputs are invalid."""
    pass


def validate_inputs(image, room_type: str, style: str, wall_color: str) -> None:
    """
    Validate all required user inputs before running generation.
    Raises ValidationError with a human-readable message if anything is invalid.
    """
    if image is None:
        raise ValidationError("Please upload a room image before generating a design.")

    if not isinstance(image, Image.Image):
        raise ValidationError("Please upload a valid room photo.")
    width, height = image.size
    if min(width, height) < 256 or max(width, height) / min(width, height) > 2.5:
        raise ValidationError("Use a photo at least 256 pixels on each side with an aspect ratio between 1:2.5 and 2.5:1.")

    if room_type not in ROOM_TYPES:
        raise ValidationError(
            f"Invalid room type '{room_type}'. Please choose one of: {', '.join(ROOM_TYPES)}."
        )

    if style not in STYLES:
        raise ValidationError(
            f"Invalid style '{style}'. Please choose one of: {', '.join(STYLES)}."
        )

    if wall_color not in WALL_COLORS and not re.fullmatch(r"#[0-9a-fA-F]{6}", wall_color or ""):
        raise ValidationError(
            f"Invalid wall color '{wall_color}'. Please choose one of: {', '.join(WALL_COLORS)}."
        )


# --------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------

def build_prompt(room_type: str, style: str, wall_color: str, custom_prompt: str = "", secondary: str = "#A87652", accent: str = "#536451") -> str:
    """
    Construct a rich Stable Diffusion prompt from structured selections
    and an optional free-text custom prompt.
    """
    for color in (secondary, accent):
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color or ""):
            raise ValidationError("Choose valid six-digit hex colors.")
    if len(custom_prompt or "") > 1500:
        raise ValidationError("Keep your custom prompt under 1,500 characters.")
    room_desc = ROOM_TYPE_DESCRIPTIONS.get(room_type, room_type.lower())
    style_desc = STYLE_DESCRIPTIONS.get(style, style.lower())
    wall_desc = WALL_COLOR_DESCRIPTIONS.get(wall_color, f"{wall_color.lower()} walls")

    base_prompt = (
        "Preserve the exact architecture: camera angle, floor plan, wall positions, ceiling, floor, windows, doors, "
        "door swings, kitchen cabinets, countertops, built-in storage, bathroom fixtures, and all openings stay in "
        "their original places. Do not move, swap, mirror, add, or remove windows, doors, or cabinetry. Restyle only "
        "paint, textures, textiles, lighting, loose furniture, and decor. Keep existing furniture in the same "
        "locations and realistic scale. Photorealistic interior, natural light matching the photo, high detail, "
        "clean and uncluttered. "
        f"A redesign of a {room_desc}, {style_desc}, {wall_desc}, "
        f"Use {wall_color} as the dominant wall color (60 percent), {secondary} for furniture and textiles (30 percent), and {accent} for small accents (10 percent). These colors override any style defaults. "
        f"professional interior photography, architectural digest style, 8k, ultra sharp focus"
    )

    custom_prompt = (custom_prompt or "").strip()
    if custom_prompt:
        base_prompt = f"{base_prompt}. Additional decor preferences, only where compatible with preserving the architecture: {custom_prompt}"

    return base_prompt


def get_negative_prompt() -> str:
    """Return the shared negative prompt used across generations."""
    return NEGATIVE_PROMPT


# --------------------------------------------------------------------------
# Filesystem helpers
# --------------------------------------------------------------------------

def ensure_directories() -> None:
    """Ensure that upload and output directories exist."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_uploaded_image(image: Image.Image) -> str:
    """
    Save the uploaded PIL image to the uploads directory with a unique name.
    Returns the saved file path.
    """
    ensure_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"upload_{timestamp}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(UPLOAD_DIR, filename)
    image.convert("RGB").save(path, format="PNG")
    return path


def save_generated_image(image: Image.Image) -> str:
    """
    Save the generated PIL image to the outputs directory with a unique name.
    Returns the saved file path.
    """
    ensure_directories()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"design_{timestamp}_{uuid.uuid4().hex[:8]}.png"
    path = os.path.join(OUTPUT_DIR, filename)
    image.convert("RGB").save(path, format="PNG")
    return path


def save_generated_images(images: list[Image.Image]) -> list[str]:
    """
    Save generated PIL images to the outputs directory.
    Returns the saved file paths.
    """
    return [save_generated_image(image) for image in images]


def resize_for_sdxl(image: Image.Image, target_size: int = 1024) -> Image.Image:
    """Preserve the full frame, rounding dimensions to SDXL multiples of 64."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = image.size
    scale = target_size / max(width, height)
    size = tuple(max(64, round(value * scale / 64) * 64) for value in (width, height))
    return image.resize(size, Image.Resampling.LANCZOS)
