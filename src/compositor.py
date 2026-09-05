import textwrap
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

from src.parser import MemoryItem

# Standard system font candidates
_BOLD_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

_REGULAR_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def _get_font(font_paths: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in font_paths:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def resize_and_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Resize and center-crop image to exactly fill target dimensions."""
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # Source is wider than target: fit height, crop width
        new_h = target_h
        new_w = int(target_h * src_ratio)
    else:
        # Source is taller than target: fit width, crop height
        new_w = target_w
        new_h = int(target_w / src_ratio)

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def create_rounded_pip(
    pip_img: Image.Image,
    target_width: int = 310,
    corner_radius: int = 24,
    border_width: int = 3,
) -> Image.Image:
    """Creates a rounded PIP image with a clean white border and subtle drop shadow."""
    # Scale PIP image maintaining aspect ratio
    aspect = pip_img.height / pip_img.width
    target_height = int(target_width * aspect)
    resized_pip = pip_img.resize((target_width, target_height), Image.Resampling.LANCZOS).convert("RGBA")

    # High-resolution mask for smooth antialiased corners (4x supersampling)
    scale = 4
    sw, sh = target_width * scale, target_height * scale
    sr = corner_radius * scale
    mask = Image.new("L", (sw, sh), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.rounded_rectangle([(0, 0), (sw, sh)], radius=sr, fill=255)
    mask = mask.resize((target_width, target_height), Image.Resampling.LANCZOS)

    # Apply mask
    rounded_pip = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    rounded_pip.paste(resized_pip, (0, 0), mask=mask)

    # Add white border
    draw_pip = ImageDraw.Draw(rounded_pip)
    draw_pip.rounded_rectangle(
        [(border_width // 2, border_width // 2), (target_width - border_width // 2 - 1, target_height - border_width // 2 - 1)],
        radius=corner_radius,
        outline=(255, 255, 255, 240),
        width=border_width,
    )

    # Add shadow
    shadow_margin = 16
    total_w = target_width + 2 * shadow_margin
    total_h = target_height + 2 * shadow_margin
    shadow_canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_canvas)
    shadow_draw.rounded_rectangle(
        [
            (shadow_margin, shadow_margin + 4),
            (shadow_margin + target_width, shadow_margin + target_height + 4),
        ],
        radius=corner_radius,
        fill=(0, 0, 0, 90),
    )
    shadow_canvas = shadow_canvas.filter(ImageFilter.GaussianBlur(radius=8))
    shadow_canvas.paste(rounded_pip, (shadow_margin, shadow_margin), mask=rounded_pip)

    return shadow_canvas


def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    pos: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    text_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    shadow_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
    shadow_offset: Tuple[int, int] = (2, 2),
    align: str = "left",
) -> None:
    """Draws text with a drop shadow for high contrast on any background."""
    x, y = pos
    # Draw drop shadow
    draw.text((x + shadow_offset[0], y + shadow_offset[1]), text, font=font, fill=shadow_color, align=align)
    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color, align=align)


def render_caption_banner(
    caption: str,
    max_width: int = 860,
    max_font_size: int = 40,
    min_font_size: int = 24,
) -> Optional[Image.Image]:
    """Renders an adaptive caption pill with dynamic font scaling to prevent overflow."""
    clean_caption = caption.strip()
    if not clean_caption:
        return None

    # Iteratively find the best font size and line wrapping
    best_font = None
    best_lines = []
    
    for font_size in range(max_font_size, min_font_size - 1, -2):
        font = _get_font(_BOLD_FONTS, font_size)
        # Estimate wrap width in characters
        # Average character width is approx font_size * 0.55
        approx_char_w = max(1, int(font_size * 0.55))
        wrap_chars = max(15, max_width // approx_char_w)
        
        lines = textwrap.wrap(clean_caption, width=wrap_chars)
        if len(lines) > 3:
            continue
            
        # Check actual pixel width of all lines
        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        line_widths = [dummy_draw.textbbox((0, 0), line, font=font)[2] for line in lines]
        
        if all(w <= max_width for w in line_widths):
            best_font = font
            best_lines = lines
            break

    if best_font is None:
        best_font = _get_font(_BOLD_FONTS, min_font_size)
        best_lines = textwrap.wrap(clean_caption, width=35)[:3]

    dummy_img = Image.new("RGBA", (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    line_bboxes = [dummy_draw.textbbox((0, 0), line, font=best_font) for line in best_lines]
    max_line_w = max(b[2] - b[0] for b in line_bboxes)
    line_h = max(b[3] - b[1] for b in line_bboxes) + 8
    total_text_h = line_h * len(best_lines)

    pad_x, pad_y = 28, 16
    pill_w = max_line_w + 2 * pad_x
    pill_h = total_text_h + 2 * pad_y

    pill = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
    draw_pill = ImageDraw.Draw(pill)
    draw_pill.rounded_rectangle([(0, 0), (pill_w, pill_h)], radius=18, fill=(0, 0, 0, 165))

    for i, line in enumerate(best_lines):
        line_w = dummy_draw.textbbox((0, 0), line, font=best_font)[2]
        line_x = (pill_w - line_w) // 2
        line_y = pad_y + i * line_h
        draw_pill.text((line_x, line_y), line, font=best_font, fill=(255, 255, 255, 255))

    return pill


def compose_frame(
    memory: MemoryItem,
    width: int = 1080,
    height: int = 1920,
) -> Image.Image:
    """
    Renders a single 1080x1920 BeReal recap frame:
    - Large background photo (back camera) center-cropped
    - Top-left selfie photo (front camera) in rounded PIP with border
    - Top-right date and location overlay
    - Bottom adaptive caption overlay
    """
    # 1. Background image
    with Image.open(memory.back_image_path) as back_raw:
        # Correct EXIF orientation if present
        back_oriented = ImageOps.exif_transpose(back_raw).convert("RGB")
        frame = resize_and_crop(back_oriented, width, height)

    # 2. Top-Left Selfie PIP
    with Image.open(memory.front_image_path) as front_raw:
        front_oriented = ImageOps.exif_transpose(front_raw).convert("RGB")
        pip_with_shadow = create_rounded_pip(front_oriented, target_width=310, corner_radius=24, border_width=3)
        # Position at (40 - 16, 40 - 16) to compensate for shadow margin
        frame.paste(pip_with_shadow, (40 - 16, 40 - 16), mask=pip_with_shadow)

    # 3. Top-Right Date and Location Text
    draw = ImageDraw.Draw(frame)
    date_font = _get_font(_BOLD_FONTS, 38)
    loc_font = _get_font(_REGULAR_FONTS, 28)

    right_margin = width - 40
    top_pos = 45

    # Date
    date_text = memory.formatted_date
    date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
    date_w = date_bbox[2] - date_bbox[0]
    draw_text_with_shadow(draw, (right_margin - date_w, top_pos), date_text, font=date_font)

    # Location (if available)
    if memory.location_name:
        loc_text = memory.location_name
        loc_bbox = draw.textbbox((0, 0), loc_text, font=loc_font)
        loc_w = loc_bbox[2] - loc_bbox[0]
        loc_y = top_pos + (date_bbox[3] - date_bbox[1]) + 10
        draw_text_with_shadow(draw, (right_margin - loc_w, loc_y), loc_text, font=loc_font)

    # 4. Bottom Caption Overlay
    if memory.caption:
        caption_pill = render_caption_banner(memory.caption, max_width=width - 160)
        if caption_pill:
            cap_x = (width - caption_pill.width) // 2
            cap_y = height - caption_pill.height - 180
            frame.paste(caption_pill, (cap_x, cap_y), mask=caption_pill)

    return frame
