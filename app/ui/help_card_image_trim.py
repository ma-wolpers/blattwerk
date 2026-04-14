"""Utilities for trimming rendered lernhilfe images to visible card content."""

from __future__ import annotations

from PIL import Image, ImageChops


def trim_lernhilfe_image(image: Image.Image, white_tolerance: int = 245, pad: int = 8) -> Image.Image:
    """Trim near-white page margins while keeping a small safety padding.

    The tolerance avoids keeping full-page artifacts caused by antialiasing or
    slightly off-white backgrounds.
    """

    rgb_image = image.convert("RGB")
    red, green, blue = rgb_image.split()
    red_mask = red.point(lambda value: 255 if value < white_tolerance else 0)
    green_mask = green.point(lambda value: 255 if value < white_tolerance else 0)
    blue_mask = blue.point(lambda value: 255 if value < white_tolerance else 0)
    mask = ImageChops.lighter(ImageChops.lighter(red_mask, green_mask), blue_mask)
    bbox = mask.getbbox()
    if bbox is None:
        return rgb_image

    left, top, right, bottom = bbox
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(rgb_image.width, right + pad)
    bottom = min(rgb_image.height, bottom + pad)
    return rgb_image.crop((left, top, right, bottom))