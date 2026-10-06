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

STYLES = [
    "Modern",
    "Luxury",
    "Contemporary Indian",
    "South Indian",
    "North Indian",
    "Maharashtrian",
    "Rajasthani",
    "Gujarati",
    "Kerala",
    "Bengali",
    "Punjabi",
    "Kashmiri",
    "Mughal / Indo-Islamic",
    "General Indian Traditional",
]

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
        "modern interior design, sleek clean lines, contemporary furniture with low-profile "
        "silhouettes, polished and matte surface mix, glass and brushed metal accents, "
        "balanced decorative accents, statement designer lighting fixtures, "
        "monochrome base palette with one bold accent"
    ),
    "Luxury": (
        "luxury interior design, opulent finishes, book-matched marble surfaces, "
        "brushed gold and brass accents, crystal chandeliers, plush velvet upholstered "
        "furniture, high-end materials, rich layered textures, five-star hotel ambiance, "
        "dramatic layered lighting"
    ),
    "Contemporary Indian": (
        "contemporary Indian interior design, warm earthy terracotta and ochre tones, "
        "handcrafted solid wood furniture with carved detailing, brass and copper accents, "
        "traditional block-print or ikat textile patterns, jali-inspired screen motifs, "
        "modern fusion of Indian heritage craftsmanship and contemporary comfort"
    ),
    "South Indian": (
        "traditional South Indian interior design inspired by Tamil Nadu, Karnataka and "
        "Andhra/Telangana heritage, dark teak and rosewood furniture, carved wooden pillars, "
        "courtyard-oriented layout cues, brass lamps and brass urli bowls, wooden swings, "
        "traditional geometric patterns, stone or patterned tile flooring, Tanjore-inspired "
        "gold-leaf artwork, large traditional carved wooden doors, cream, brown, maroon, "
        "mustard and deep green color palette, elegant grand temple-and-courtyard ambiance"
    ),
    "North Indian": (
        "traditional North Indian interior design, Mughal-inspired jaali lattice screens and "
        "arches, hand-carved sheesham wood furniture, rich jewel-tone textiles with zari and "
        "mirror-work embroidery, ornate brass and copper lanterns, royal Rajasthani color "
        "palette of deep reds, saffron, and indigo, intricate inlay or jharokha-style window "
        "framing, plush floor seating with bolster cushions, opulent heritage ambiance"
    ),
    "Maharashtrian": (
        "traditional Maharashtrian Wada-inspired interior design, wooden pillars and exposed "
        "beams, carved wooden furniture, a wooden jhula swing, paati and traditional low "
        "seating, brass samai and traditional oil lamps, copper and brass vessels as decor, "
        "terracotta or stone flooring, earthy beige, brown, ochre and muted red color palette, "
        "traditional Maharashtrian fabrics, traditional wooden doors and windows, "
        "courtyard-oriented planning cues, refined heritage Wada feel suited to a modern home"
    ),
    "Rajasthani": (
        "Rajasthani Haveli-inspired interior design, jharokhas and arched openings, carved "
        "wooden furniture, sandstone and marble surfaces, decorative hand-painted wall "
        "patterns, traditional miniature artwork, bandhani and embroidered textiles, rich red, "
        "terracotta, mustard yellow, royal blue and turquoise color palette, brass lanterns and "
        "decorative objects, ornamental jaali screens and wall niches, royal colorful artistic "
        "Haveli ambiance"
    ),
    "Gujarati": (
        "Gujarati interior design, bright and artistic interiors, traditional wooden furniture, "
        "a carved wooden Gujarati chowki, bandhani textiles with embroidery and mirror work, "
        "colorful wall decoration, handcrafted wooden elements, brass decor pieces, vibrant "
        "red, yellow, orange, green, pink and blue color palette, traditional cushions and "
        "floor seating, vibrant handcrafted culturally Gujarati feel without visual clutter"
    ),
    "Kerala": (
        "Kerala Nalukettu-inspired interior design, central-courtyard planning cues, sloping "
        "tiled-roof architectural character, large timber structural elements, teak and "
        "rosewood furniture, traditional carved wooden columns, brass nilavilakku lamps, "
        "natural stone and terracotta flooring, white, cream, brown and muted green color "
        "palette, Kerala handloom fabrics, open naturally ventilated climate-responsive "
        "layout with strong wood and courtyard connection"
    ),
    "Bengali": (
        "Bengali interior design, simple and artistic interiors, wooden and cane furniture, "
        "terracotta decorative elements, kantha-stitch textiles, Bengali handloom fabrics, "
        "traditional artwork, warm earthy color palette of terracotta red, cream, mustard, "
        "brown and muted green, handcrafted pottery accents, simple brass lighting, warm "
        "artistic comfortable Bengali cultural feel"
    ),
    "Punjabi": (
        "Punjabi interior design, vibrant and bold interiors, rich fabrics with phulkari "
        "embroidery, colorful cushions, heavy carved wooden furniture, traditional seating, "
        "brass decorative objects, warm layered lighting, red, orange, yellow, green and "
        "royal blue color palette, traditional Punjabi artwork and decorative textiles, "
        "energetic welcoming colorful luxurious Punjabi identity"
    ),
    "Kashmiri": (
        "Kashmiri interior design, detailed walnut wood carving, Kashmiri carpets, "
        "Persian-inspired patterns, papier-mache decorative accents, khatamband-inspired "
        "geometric ceiling patterns, rich textiles, deep red, burgundy, green, blue, brown "
        "and gold color palette, carved wooden furniture, decorative lamps, intricate "
        "geometric and floral motifs, luxurious warm artistic highly detailed ambiance"
    ),
    "Mughal / Indo-Islamic": (
        "Mughal palace-inspired Indo-Islamic interior design, arches and domed architectural "
        "cues, jaali screens, geometric patterns, symmetrical layout, marble and sandstone "
        "surfaces, brass accents, carved wood, rich silk velvet and brocade textiles, deep "
        "red, emerald green, royal blue, ivory and gold color palette, floral and geometric "
        "motifs, decorative lanterns, regal symmetrical sophisticated architectural detail"
    ),
    "General Indian Traditional": (
        "general Indian traditional interior design combining common Indian heritage "
        "elements, carved wooden furniture, brass lamps and vessels, Indian textiles, "
        "rangoli-inspired floor motifs, traditional paintings, jaali patterns, handcrafted "
        "decor, terracotta and stone accents, warm earthy color palette, traditional "
        "handicrafts and regional artwork, broadly and authentically Indian heritage feel"
    ),
}

ROOM_TYPE_DESCRIPTIONS = {
    "Living Room": (
        "spacious living room with a sofa set, coffee table, area rug, accent chairs, "
        "media console, and a defined entertainment area, wide-angle architectural view"
    ),
    "Bedroom": (
        "comfortable bedroom with a dressed bed, headboard, nightstands with lamps, "
        "a wardrobe or dresser, and soft ambient layered lighting"
    ),
    "Kitchen": (
        "functional kitchen with countertops, base and wall cabinetry, a backsplash, "
        "modern appliances, and clearly defined worktop and sink areas"
    ),
    "Bathroom": (
        "clean bathroom with a vanity and mirror, shower or tub area, fixtures and "
        "fittings, and elegant floor-to-ceiling tiling"
    ),
}

# Per-(room type, style) accuracy refinements so furniture and materials stay
# plausible for both the space and the chosen aesthetic simultaneously.
ROOM_STYLE_REFINEMENTS = {
    ("Living Room", "Modern"): "low sectional sofa, geometric area rug, floating media wall",
    ("Living Room", "Luxury"): "tufted velvet sofa set, marble coffee table, statement chandelier over seating",
    ("Living Room", "Contemporary Indian"): "carved wooden sofa with Indian textile cushions, brass coffee table, jali screen accent",
    ("Bedroom", "Modern"): "platform bed with upholstered headboard, floating nightstands, minimal pendant lighting",
    ("Bedroom", "Luxury"): "upholstered tufted headboard, silk bedding, crystal bedside lamps, plush bench",
    ("Bedroom", "Contemporary Indian"): "carved wooden bed frame, block-print bedding, brass table lamps",
    ("Kitchen", "Modern"): "handleless flat-panel cabinets, quartz countertop, waterfall island edge",
    ("Kitchen", "Luxury"): "marble countertops and backsplash, brass hardware, under-cabinet lighting",
    ("Kitchen", "Contemporary Indian"): "warm wood cabinetry with brass handles, terracotta backsplash accent",
    ("Bathroom", "Modern"): "floating vanity, frameless glass shower, matte black fixtures",
    ("Bathroom", "Luxury"): "marble-clad walls, freestanding tub, gold fixtures, backlit mirror",
    ("Bathroom", "Contemporary Indian"): "terracotta tile accents, brass fixtures, carved wood vanity",
    ("Living Room", "South Indian"): "carved rosewood sofa with cane inlay, Athangudi-tile-pattern rug, brass kuthu vilakku lamp as accent",
    ("Living Room", "North Indian"): "sheesham wood low seating with bolster cushions, jaali screen partition, ornate brass lantern pendant",
    ("Bedroom", "South Indian"): "teak wood carved bed frame, temple-motif headboard, brass table lamp, woven cane bench",
    ("Bedroom", "North Indian"): "sheesham wood carved bed, mirror-work and zari bedding, jharokha-style window frame, brass lanterns",
    ("Kitchen", "South Indian"): "dark wood cabinetry with brass handles, Athangudi tile backsplash, traditional brass vessel display shelf",
    ("Kitchen", "North Indian"): "carved wood cabinet fronts, jaali-pattern cabinet inserts, copper and brass fixtures",
    ("Bathroom", "South Indian"): "Athangudi tile flooring, teak wood vanity, brass fixtures and mirror frame",
    ("Bathroom", "North Indian"): "jaali-pattern tile accent wall, carved wood vanity, ornate brass fixtures",
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
    refinement = ROOM_STYLE_REFINEMENTS.get((room_type, style), "")

    base_prompt = (
        "Preserve the exact architecture: camera angle, floor plan, wall positions, ceiling, floor, windows, doors, "
        "door swings, kitchen cabinets, countertops, built-in storage, bathroom fixtures, and all openings stay in "
        "their original places. Do not move, swap, mirror, add, or remove windows, doors, or cabinetry. Restyle only "
        "paint, textures, textiles, lighting, loose furniture, and decor. Keep existing furniture in the same "
        "locations and realistic scale. Photorealistic interior, natural light matching the photo, high detail, "
        "clean and uncluttered. "
        f"A redesign of a {room_desc}, {style_desc}, {wall_desc}. "
        + (f"Include details true to this room and style: {refinement}. " if refinement else "")
        + f"Use {wall_color} as the dominant wall color (60 percent), {secondary} for furniture and textiles (30 percent), and {accent} for small accents (10 percent). These colors override any style defaults. "
        "Materials, furniture scale, and lighting direction must stay physically consistent with the original photo. "
        "professional interior photography, architectural digest style, shot on a full-frame DSLR with a wide-angle "
        "lens, balanced exposure, true-to-life colors, sharp focus throughout, 8k, ultra-detailed, hyperrealistic"
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
