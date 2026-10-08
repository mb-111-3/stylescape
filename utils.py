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
# Every ROOM_TYPES x STYLES combination is covered so no style falls back
# to a generic look that can drift into the wrong room type.
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
    ("Living Room", "Maharashtrian"): "carved wooden sofa with paithani-fabric cushions, wooden pillars and beams, brass samai lamps as decor",
    ("Bedroom", "Maharashtrian"): "carved wooden bed with traditional Maharashtrian textiles, wooden jhula-style bench, brass samai table lamps",
    ("Kitchen", "Maharashtrian"): "wood-finish cabinets with brass handles, stone backsplash, copper vessels on display shelf",
    ("Bathroom", "Maharashtrian"): "stone-look tiles, carved wood vanity, brass fixtures and traditional lamp accent",
    ("Living Room", "Rajasthani"): "carved wooden sofa with bandhani cushions, jharokha niche, brass lanterns and miniature art",
    ("Bedroom", "Rajasthani"): "carved wooden bed with bandhani bedding, arched headboard wall, brass lantern bedside lights",
    ("Kitchen", "Rajasthani"): "carved wood cabinet fronts, hand-painted tile backsplash, brass and copper fixtures",
    ("Bathroom", "Rajasthani"): "hand-painted tile accent wall, carved wood vanity, brass fixtures and wall niches",
    ("Living Room", "Gujarati"): "carved wooden sofa with bandhani and mirror-work cushions, colorful wall art, brass decor pieces",
    ("Bedroom", "Gujarati"): "carved wooden bed with mirror-work Gujarati bedding, colorful cushions, brass bedside decor",
    ("Kitchen", "Gujarati"): "bright wood cabinets, colorful embroidered runner, brass hardware and decor",
    ("Bathroom", "Gujarati"): "colorful tile accents, wooden vanity, brass fixtures and mirror-work framed mirror",
    ("Living Room", "Kerala"): "teak and rosewood sofa with Kerala handloom cushions, carved wooden columns, brass nilavilakku lamp",
    ("Bedroom", "Kerala"): "teak four-poster style bed, Kerala handloom bedding, carved columns, brass nilavilakku lamps",
    ("Kitchen", "Kerala"): "teak wood cabinetry, natural stone backsplash, brass vessels and traditional storage cues",
    ("Bathroom", "Kerala"): "natural stone tiles, teak vanity, brass fixtures and nilavilakku-style accent",
    ("Living Room", "Bengali"): "wooden and cane sofa with kantha cushions, terracotta decor, Bengali handloom throw",
    ("Bedroom", "Bengali"): "wooden bed with kantha bedding, cane bench, terracotta accents and brass lighting",
    ("Kitchen", "Bengali"): "wood and cane-front cabinets, terracotta tile backsplash, brass and pottery accents",
    ("Bathroom", "Bengali"): "terracotta tile accents, wood vanity, cane detail, simple brass fixtures",
    ("Living Room", "Punjabi"): "heavy carved wooden sofa with phulkari cushions, colorful rug, brass objects and warm layered light",
    ("Bedroom", "Punjabi"): "heavy carved wooden bed with phulkari bedding, colorful cushions, brass lamps and artwork",
    ("Kitchen", "Punjabi"): "rich wood cabinets with brass handles, colorful backsplash, phulkari runner and brass decor",
    ("Bathroom", "Punjabi"): "warm colorful tile accent, carved wood vanity, brass fixtures and textile accent",
    ("Living Room", "Kashmiri"): "walnut carved sofa with Kashmiri carpet rug, papier-mache accents, khatamband-pattern ceiling detail",
    ("Bedroom", "Kashmiri"): "walnut carved bed with rich Kashmiri textiles, carpet rug, papier-mache lamps",
    ("Kitchen", "Kashmiri"): "walnut-finish cabinets, Persian-pattern backsplash, brass fixtures and carpet runner",
    ("Bathroom", "Kashmiri"): "geometric khatamband-pattern accent, walnut vanity, brass fixtures and rich textile accent",
    ("Living Room", "Mughal / Indo-Islamic"): "symmetrical carved seating with silk cushions, jaali screen, arched niches, brass lanterns",
    ("Bedroom", "Mughal / Indo-Islamic"): "carved bed with silk velvet bedding, symmetrical nightstands, jaali screen, brass lanterns",
    ("Kitchen", "Mughal / Indo-Islamic"): "symmetrical cabinetry with jaali inserts, marble backsplash, brass fixtures",
    ("Bathroom", "Mughal / Indo-Islamic"): "symmetrical marble layout, jaali-pattern tile, brass fixtures, arched mirror",
    ("Living Room", "General Indian Traditional"): "carved wooden sofa with Indian textile cushions, brass lamps, rangoli-motif rug, traditional art",
    ("Bedroom", "General Indian Traditional"): "carved wooden bed with Indian textile bedding, brass lamps, traditional art and rug",
    ("Kitchen", "General Indian Traditional"): "carved wood cabinets, brass handles, traditional tile backsplash, brass vessels",
    ("Bathroom", "General Indian Traditional"): "traditional tile accents, carved wood vanity, brass fixtures and framed mirror",
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
    "room type change, bedroom converted to living room, living room converted to bedroom, "
    "kitchen converted to bedroom, bathroom converted to bedroom, bedroom converted to kitchen, "
    "wrong room function, office, dining room conversion, "
    "cluttered, dark, noisy, low resolution"
)

# Elements that belong to OTHER room types and must not leak into the
# selected room type's redesign (prevents e.g. a bed appearing in a kitchen).
ROOM_TYPE_EXCLUSIONS = {
    "Living Room": "bed, headboard, nightstand, bedroom dresser, wardrobe in place of seating, kitchen cabinets, countertops, stove, oven, kitchen sink, shower, bathtub, toilet, bathroom vanity",
    "Bedroom": "sofa set, living room sectional, coffee table as main furniture, TV media wall replacing bed, kitchen cabinets, countertops, stove, oven, kitchen sink, shower, bathtub, toilet, bathroom vanity, office desk setup replacing bed",
    "Kitchen": "bed, headboard, nightstand, wardrobe, sofa set, sectional, coffee table, shower, bathtub, toilet, bathroom vanity, office setup",
    "Bathroom": "bed, headboard, nightstand, wardrobe, sofa set, sectional, coffee table, kitchen cabinets, countertops, stove, oven, kitchen sink, dining table",
}

# Furniture/fixtures that MUST stay in the same place for each room type.
# Injected into the positive prompt so the model keeps the room's function
# and only restyles surfaces, textiles, lighting, and decor.
ROOM_TYPE_ANCHORS = {
    "Living Room": (
        "Keep this as a living room only: keep the sofa set, coffee table, area rug, "
        "accent chairs, and media console in their original positions. Do not add a bed."
    ),
    "Bedroom": (
        "Keep this as a bedroom only: keep the bed with headboard as the central furniture "
        "in its original position, plus nightstands with lamps and wardrobe/dresser. "
        "Do not replace the bed with a sofa, do not remove the bed, do not add kitchen "
        "cabinets, stoves, showers, or toilets."
    ),
    "Kitchen": (
        "Keep this as a kitchen only: keep countertops, base and wall cabinets, backsplash, "
        "sink, and appliances in their original positions. Do not add a bed, sofa, shower, or toilet."
    ),
    "Bathroom": (
        "Keep this as a bathroom only: keep the vanity with mirror, toilet, and shower/tub "
        "in their original positions. Do not add a bed, sofa, kitchen cabinets, or stove."
    ),
}


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

    The room type is locked: the prompt forces the model to keep the
    original room function (e.g. bedroom stays a bedroom) and only apply
    the selected interior style on top of it.
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
    anchor = ROOM_TYPE_ANCHORS.get(room_type, f"Keep this strictly as a {room_type}.")
    exclusions = ROOM_TYPE_EXCLUSIONS.get(room_type, "")

    base_prompt = (
        "Restyle this existing room without architectural changes. "
        f"STYLE PRIORITY: redesign this room fully in {style} style, immediately recognizable as {style}. "
        f"{style_desc}. "
        f"ROOM LOCK: This space is strictly a {room_type} and must remain a {room_type} "
        f"after redesign. Do not convert it into any other room type. {anchor} "
        "Preserve the exact architecture: camera angle, floor plan, wall positions, ceiling, floor, windows, doors, "
        "door swings, kitchen cabinets, countertops, built-in storage, bathroom fixtures, and all openings stay in "
        "their original places. Do not move, swap, mirror, add, or remove windows, doors, or cabinetry. Restyle "
        "paint, textures, textiles, lighting, furniture finishes, and decor to express the selected style. Keep existing furniture in the same "
        "locations and realistic scale. Photorealistic interior, natural light matching the photo, high detail, "
        "clean and uncluttered. "
        f"A redesign of a {room_desc}, {wall_desc}, unmistakably in {style} style. "
        + (f"Include details true to this room and style: {refinement}. " if refinement else "")
        + (f"Strictly forbid in this {room_type}: {exclusions}. " if exclusions else "")
        + f"Use {wall_color} walls as a base adapted to the {style} palette, with {secondary} for furniture and textiles and {accent} for small accents, harmonized with authentic {style} colors and materials. "
        f"The finished {room_type} must read clearly as {style} at first glance. "
        "Materials, furniture scale, and lighting direction must stay physically consistent with the original photo. "
        "professional interior photography, architectural digest style, shot on a full-frame DSLR with a wide-angle "
        "lens, balanced exposure, true-to-life colors, sharp focus throughout, 8k, ultra-detailed, hyperrealistic"
    )

    custom_prompt = (custom_prompt or "").strip()
    if custom_prompt:
        base_prompt = f"{base_prompt}. Additional decor preferences, only where compatible with preserving the architecture: {custom_prompt}"

    return base_prompt


def get_negative_prompt(room_type: str = "") -> str:
    """
    Return the shared negative prompt, extended with the furniture/fixtures
    that belong to other room types so the output stays true to the room
    type the user actually selected.
    """
    exclusions = ROOM_TYPE_EXCLUSIONS.get(room_type, "")
    if exclusions:
        return f"{NEGATIVE_PROMPT}, {exclusions}"
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
