"""
generate.py
-----------
SDXL ControlNet image-to-image pipeline for interior redesign.

The pipeline uses two structural controls:
1. Canny edges to preserve windows, doors, walls, and perspective lines.
2. Depth map to preserve room geometry and camera structure.
"""

from __future__ import annotations

import os
from io import BytesIO

import cv2
import numpy as np
import requests
import torch
from diffusers import (
    ControlNetModel,
    StableDiffusionXLControlNetImg2ImgPipeline,
)
from PIL import Image, UnidentifiedImageError
from transformers import pipeline as transformers_pipeline

from settings import get_api_key
from utils import build_prompt, get_negative_prompt, resize_for_sdxl

BASE_MODEL_ID = os.getenv("STYLESCAPE_BASE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
CANNY_CONTROLNET_ID = os.getenv("STYLESCAPE_CANNY_CONTROLNET", "diffusers/controlnet-canny-sdxl-1.0")
DEPTH_CONTROLNET_ID = os.getenv("STYLESCAPE_DEPTH_CONTROLNET", "diffusers/controlnet-depth-sdxl-1.0")
DEPTH_MODEL_ID = os.getenv("STYLESCAPE_DEPTH_MODEL", "Intel/dpt-hybrid-midas")

DEFAULT_STRENGTH = 0.35
DEFAULT_GUIDANCE_SCALE = 10.0
DEFAULT_CONTROLNET_SCALE = [0.95, 1.0]
STABILITY_STRUCTURE_URL = "https://api.stability.ai/v2beta/stable-image/control/structure"

_pipeline = None
_depth_estimator = None


VARIATION_SEEDS = [42, 123, 456, 789]


def _get_device_and_dtype() -> tuple[str, torch.dtype]:
    if torch.cuda.is_available():
        return "cuda", torch.float16
    if torch.backends.mps.is_available():
        return "mps", torch.float32
    return "cpu", torch.float32


def get_runtime_defaults() -> dict:
    device, _ = _get_device_and_dtype()
    cloud_available = bool(get_api_key())
    image_size = 1024
    steps = 25
    if device == "cuda":
        total_vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        image_size = 640 if total_vram_gb < 6 else 1024
        steps = 25 if total_vram_gb < 6 else 35
    return {
        "backend": "sdxl-controlnet" if device != "cpu" else ("stability-cloud" if cloud_available else "cpu-unavailable"),
        "device": device,
        "image_size": image_size,
        "num_inference_steps": steps,
        "max_inference_steps": 50,
        "guidance_scale": DEFAULT_GUIDANCE_SCALE,
        "strength": DEFAULT_STRENGTH,
    }


def _require_supported_runtime() -> None:
    device, _ = _get_device_and_dtype()
    if device == "cpu" and get_api_key():
        return
    allow_cpu = os.getenv("STYLESCAPE_ALLOW_CPU_SDXL", "").strip().lower() in {"1", "true", "yes", "on"}
    if device == "cpu" and not allow_cpu:
        raise RuntimeError(
            "CUDA is not available inside this Python environment, and STABILITY_API_KEY is not set. "
            "For expected AI redesign output on this laptop, set a Stability AI API key on the admin page. "
            "For local generation, update the NVIDIA driver and install CUDA PyTorch using setup_cuda_torch.ps1."
        )


def _prepare_image(input_image: Image.Image) -> Image.Image:
    defaults = get_runtime_defaults()
    return resize_for_sdxl(input_image, target_size=defaults["image_size"]).convert("RGB")


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def make_canny_control_image(image: Image.Image) -> Image.Image:
    array = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, threshold1=80, threshold2=180)
    edges = np.stack([edges, edges, edges], axis=2)
    return Image.fromarray(edges)


def _load_depth_estimator():
    global _depth_estimator
    if _depth_estimator is None:
        device, _ = _get_device_and_dtype()
        device_arg = 0 if device == "cuda" else -1
        _depth_estimator = transformers_pipeline(
            task="depth-estimation",
            model=DEPTH_MODEL_ID,
            device=device_arg,
        )
    return _depth_estimator


def make_depth_control_image(image: Image.Image) -> Image.Image:
    depth = _load_depth_estimator()(image)["depth"]
    depth = depth.resize(image.size, Image.Resampling.BICUBIC).convert("L")
    depth_array = np.array(depth).astype(np.float32)
    depth_array -= depth_array.min()
    max_value = depth_array.max()
    if max_value > 0:
        depth_array = depth_array / max_value
    depth_array = (depth_array * 255).astype(np.uint8)
    depth_rgb = np.stack([depth_array, depth_array, depth_array], axis=2)
    return Image.fromarray(depth_rgb)


def load_pipeline() -> StableDiffusionXLControlNetImg2ImgPipeline:
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    _require_supported_runtime()
    device, dtype = _get_device_and_dtype()

    canny_controlnet = ControlNetModel.from_pretrained(
        CANNY_CONTROLNET_ID,
        torch_dtype=dtype,
        use_safetensors=True,
    )
    depth_controlnet = ControlNetModel.from_pretrained(
        DEPTH_CONTROLNET_ID,
        torch_dtype=dtype,
        use_safetensors=True,
    )

    pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
        BASE_MODEL_ID,
        controlnet=[canny_controlnet, depth_controlnet],
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if dtype == torch.float16 else None,
    )

    if device == "cuda":
        pipe.enable_model_cpu_offload()
        pipe.enable_attention_slicing()
        pipe.enable_vae_slicing()
        pipe.enable_vae_tiling()
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass
    else:
        pipe = pipe.to(device)
        pipe.enable_attention_slicing()

    _pipeline = pipe
    return _pipeline


def _call_stability_structure_api(
    input_image: Image.Image,
    prompt: str,
    seed: int,
    control_strength: float = 0.75,
) -> Image.Image:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("STABILITY_API_KEY is not set.")

    prepared_image = _prepare_image(input_image)
    response = requests.post(
        STABILITY_STRUCTURE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/*",
        },
        files={
            "image": ("room.png", _image_to_png_bytes(prepared_image), "image/png"),
        },
        data={
            "prompt": prompt,
            "negative_prompt": get_negative_prompt(),
            "control_strength": str(control_strength),
            "seed": str(seed),
            "output_format": "png",
        },
        timeout=180,
    )

    if response.status_code >= 400:
        raise RuntimeError({401: "The API key is invalid. Update it on the admin page.", 402: "The Stability account has insufficient credits.", 403: "The provider rejected this request. Try a different image or prompt.", 429: "The provider is busy. Please try again shortly."}.get(response.status_code, f"Generation provider returned HTTP {response.status_code}. Please try again."))

    try:
        return Image.open(BytesIO(response.content)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise RuntimeError("The provider returned no usable image. Please try another photo or brief.") from exc


def iter_redesign_variations(
    input_image: Image.Image,
    prompt: str | None = None,
    room_type: str | None = None,
    style: str | None = None,
    wall_color: str | None = None,
    strength: float = DEFAULT_STRENGTH,
    guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
    num_inference_steps: int = 35,
    count: int = 4,
    custom_prompt: str | None = None,
):
    """
    Generate one to four ControlNet-guided interior redesigns.

    Each variation follows the selected design brief with a different seed.
    """
    prompt = prompt or build_prompt(room_type or "Living Room", style or "Modern", wall_color or "Beige", custom_prompt or "")
    count = max(1, min(int(count), 4))
    # Enforce preservation for UI and programmatic callers alike.
    strength = max(0.25, min(float(strength), 0.45))

    _require_supported_runtime()
    device, _ = _get_device_and_dtype()
    if device == "cpu" and get_api_key():
        for seed in VARIATION_SEEDS[:count]:
            yield _call_stability_structure_api(
                input_image=input_image,
                prompt=prompt,
                seed=seed,
                control_strength=max(0.85, min(1.0, 1.3 - strength)),
            )
        return

    pipe = load_pipeline()
    defaults = get_runtime_defaults()

    prepared_image = _prepare_image(input_image)
    canny_control = make_canny_control_image(prepared_image)
    depth_control = make_depth_control_image(prepared_image)

    guidance_scale = max(8.0, min(float(guidance_scale), 12.0))
    num_inference_steps = max(20, min(int(num_inference_steps), defaults["max_inference_steps"]))

    for seed in VARIATION_SEEDS[:count]:
        generator = torch.Generator(device=device).manual_seed(seed)
        result = pipe(
            prompt=prompt,
            negative_prompt=get_negative_prompt(),
            image=prepared_image,
            control_image=[canny_control, depth_control],
            strength=strength,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            generator=generator,
            controlnet_conditioning_scale=DEFAULT_CONTROLNET_SCALE,
        )
        yield result.images[0]


def generate_redesign_variations(*args, **kwargs) -> list[Image.Image]:
    """Compatibility helper for callers that need a completed image list."""
    return list(iter_redesign_variations(*args, **kwargs))
