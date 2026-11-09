"""
Zero-Extra-Dependency PDF Export Engine for AI Presentation Bot (with Photo-Editorial support).
1. Uses headless LibreOffice if available on the host.
2. Otherwise uses a built-in High-Resolution Pillow (PIL) 16:9 PDF Renderer
   with Dynamic Y-Flow (zero overlap), aspect-preserving photo cropping, and Kazakh/Russian/English typography.
"""
import base64
import io
import os
import shutil
import subprocess
import tempfile
import logging
from typing import Optional, List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.core.types import PresentationData
from app.core.themes import THEMES_REGISTRY, get_theme_heading_color
from app.pptx_generator.engine import clean_slide_text

logger = logging.getLogger(__name__)


def hex_to_rgb_tuple(hex_code: str) -> Tuple[int, int, int]:
    """Convert 6-character hex string to (R, G, B) tuple."""
    c = hex_code.strip().lstrip("#")
    if len(c) == 3:
        c = "".join([x * 2 for x in c])
    if len(c) != 6:
        return (0, 0, 0)
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except Exception:
        return (0, 0, 0)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """
    Loads a Unicode TrueType font supporting Kazakh Cyrillic across Windows, Linux, and macOS.
    """
    if bold:
        candidates = [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\calibrib.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass

    try:
        import matplotlib
        mpl_font = os.path.join(
            os.path.dirname(matplotlib.__file__),
            "mpl-data", "fonts", "ttf",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        )
        if os.path.exists(mpl_font):
            return ImageFont.truetype(mpl_font, size=size)
    except Exception:
        pass

    return ImageFont.load_default()


def _wrap_text_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> List[str]:
    """Wraps text into lines that fit within max_width pixels."""
    if not text:
        return []
    words = text.split()
    lines: List[str] = []
    current: List[str] = []

    for word in words:
        test_line = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int],
    line_height: int,
) -> int:
    """Draws wrapped multiline text and returns the ending Y coordinate."""
    lines = _wrap_text_lines(draw, text, font, max_w)
    cur_y = y
    for line in lines:
        if cur_y + line_height > y + max_h:
            break
        draw.text((x, cur_y), line, font=font, fill=color)
        cur_y += line_height
    return cur_y


def _draw_bullets(
    draw: ImageDraw.ImageDraw,
    items: List[str],
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    font: ImageFont.FreeTypeFont,
    dot_color: Tuple[int, int, int],
    text_color: Tuple[int, int, int],
    line_height: int,
    item_gap: int = 10,
):
    """Draws clean colored bullets with wrapped text."""
    cur_y = y
    for item in items:
        clean_it = clean_slide_text(item)
        if not clean_it:
            continue
        if cur_y + line_height > y + max_h:
            break
        draw.ellipse([x, cur_y + 7, x + 7, cur_y + 14], fill=dot_color)
        lines = _wrap_text_lines(draw, clean_it, font, max_w - 22)
        for line in lines:
            if cur_y + line_height > y + max_h:
                break
            draw.text((x + 20, cur_y), line, font=font, fill=text_color)
            cur_y += line_height
        cur_y += item_gap


def _paste_framed_photo(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    image_b64: str,
    x: int,
    y: int,
    w: int,
    h: int,
    card_bg_rgb: Tuple[int, int, int],
    accent_rgb: Tuple[int, int, int],
):
    """Pastes a decoded base64 image inside an editorial frame using aspect-preserving center crop."""
    try:
        raw = base64.b64decode(image_b64)
        with Image.open(io.BytesIO(raw)).convert("RGB") as im:
            photo = ImageOps.fit(im, (w, h), method=Image.Resampling.LANCZOS)
        draw.rounded_rectangle([x - 7, y - 7, x + w + 7, y + h + 7], radius=12, fill=card_bg_rgb, outline=accent_rgb, width=2)
        canvas.paste(photo, (x, y))
    except Exception:
        pass


def build_pdf_pillow(presentation: PresentationData) -> bytes:
    """
    Renders a crisp, minimalist or photo-editorial 16:9 widescreen PDF (1600x900 per slide) using Pillow
    with sequential dynamic Y-positioning so texts never overlap.
    """
    theme = THEMES_REGISTRY.get(presentation.design_id, THEMES_REGISTRY["swiss_minimalism"])
    heading_color_hex = get_theme_heading_color(theme)

    bg_rgb = hex_to_rgb_tuple(theme.bgColor)
    card_bg_rgb = hex_to_rgb_tuple(theme.cardBg)
    border_rgb = hex_to_rgb_tuple(theme.borderColor)
    accent_rgb = hex_to_rgb_tuple(theme.accentColor)
    secondary_rgb = hex_to_rgb_tuple(theme.secondaryColor)
    text_rgb = hex_to_rgb_tuple(theme.textColor)
    text_muted_rgb = hex_to_rgb_tuple(theme.textMuted)
    heading_rgb = hex_to_rgb_tuple(heading_color_hex)

    W, H = 1600, 900
    S = 160.0  # px per inch

    font_cover_title = _load_font(36, bold=True)
    font_cover_title_sm = _load_font(30, bold=True)
    font_slide_title = _load_font(29, bold=True)
    font_slide_title_sm = _load_font(25, bold=True)
    font_stat_val = _load_font(34, bold=True)
    font_step_num = _load_font(21, bold=True)
    font_card_title = _load_font(18, bold=True)
    font_quote = _load_font(18, bold=False)
    font_num_badge = _load_font(19, bold=True)
    font_body = _load_font(16, bold=False)
    font_small = _load_font(15, bold=False)

    images: List[Image.Image] = []
    total_slides = len(presentation.slides)

    for idx, slide_item in enumerate(presentation.slides):
        img = Image.new("RGB", (W, H), bg_rgb)
        draw = ImageDraw.Draw(img)

        slide_title = clean_slide_text(slide_item.title) or f"Слайд {idx + 1}"
        subtitle_text = clean_slide_text(slide_item.subtitle)
        content_text = clean_slide_text(slide_item.content)
        key_points = [clean_slide_text(p) for p in (slide_item.key_points or []) if clean_slide_text(p)]
        has_img = bool(slide_item.image_bytes_b64)

        def draw_card(cx: float, cy: float, cw: float, ch: float, r: int = 12):
            x0, y0 = int(cx * S), int(cy * S)
            x1, y1 = int((cx + cw) * S), int((cy + ch) * S)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=card_bg_rgb, outline=border_rgb, width=2)

        def draw_header(lead_text: Optional[str] = None) -> float:
            t_font = font_slide_title if len(slide_title) <= 50 else font_slide_title_sm
            t_lh = 35 if len(slide_title) <= 50 else 31
            end_title_y = _draw_wrapped_text(
                draw, slide_title, int(0.68 * S), int(0.40 * S), int(7.75 * S), int(0.78 * S),
                t_font, heading_rgb, t_lh
            )
            counter_str = f"{idx + 1:02d} / {total_slides:02d}"
            bbox = draw.textbbox((0, 0), counter_str, font=font_small)
            cw = bbox[2] - bbox[0]
            draw.text((int(9.32 * S) - cw, int(0.44 * S)), counter_str, font=font_small, fill=text_muted_rgb)

            clean_lead = clean_slide_text(lead_text)
            if clean_lead:
                lead_y_px = end_title_y + 8
                end_lead_y = _draw_wrapped_text(
                    draw, clean_lead, int(0.68 * S), lead_y_px, int(7.85 * S), int(0.75 * S),
                    font_body, text_muted_rgb, 23
                )
                return max(1.08, min(1.92, (end_lead_y + 18) / S))
            return max(1.06, (end_title_y + 18) / S)

        # 1. COVER SLIDE
        if idx == 0 or slide_item.type in ("cover", "photo_hero"):
            draw.rectangle(
                [int(0.68 * S), int(0.52 * S), int(1.33 * S), int(0.57 * S)],
                fill=secondary_rgb
            )
            if has_img:
                c_font = font_cover_title_sm if len(slide_title) > 48 else font_slide_title
                c_lh = 36 if len(slide_title) > 48 else 38
                end_cov_y = _draw_wrapped_text(
                    draw, slide_title, int(0.68 * S), int(0.68 * S), int(4.88 * S), int(1.45 * S),
                    c_font, heading_rgb, c_lh
                )
                overview = content_text or subtitle_text
                if overview:
                    ov_y = end_cov_y + 12
                    rem_ov_px = max(60, int(3.32 * S) - ov_y)
                    _draw_wrapped_text(
                        draw, overview, int(0.68 * S), ov_y, int(4.85 * S), rem_ov_px,
                        font_body, text_muted_rgb, 23
                    )
                _paste_framed_photo(
                    img, draw, slide_item.image_bytes_b64,
                    int(5.80 * S), int(0.66 * S), int(3.50 * S), int(2.52 * S),
                    card_bg_rgb, secondary_rgb,
                )
                if key_points:
                    card_w, gap, card_y, card_h = 2.74, 0.21, 3.42, 1.72
                    for k_idx, pt_text in enumerate(key_points[:3]):
                        pos_x = 0.68 + k_idx * (card_w + gap)
                        draw_card(pos_x, card_y, card_w, card_h, r=12)
                        draw.text(
                            (int((pos_x + 0.22) * S), int((card_y + 0.16) * S)),
                            f"0{k_idx + 1}", font=font_num_badge, fill=secondary_rgb,
                        )
                        _draw_wrapped_text(
                            draw, pt_text,
                            int((pos_x + 0.22) * S), int((card_y + 0.44) * S),
                            int((card_w - 0.44) * S), int((card_h - 0.56) * S),
                            font_small, text_rgb, 21
                        )
            else:
                c_font = font_cover_title if len(slide_title) <= 55 else font_cover_title_sm
                end_cov_y = _draw_wrapped_text(
                    draw, slide_title, int(0.68 * S), int(0.74 * S), int(8.64 * S), int(1.30 * S),
                    c_font, heading_rgb, 42
                )
                sub_parts = [p for p in (subtitle_text, content_text) if p]
                combined_overview = " — ".join(sub_parts) if len(sub_parts) > 1 else (sub_parts[0] if sub_parts else "")
                if combined_overview:
                    ov_y = end_cov_y + 14
                    rem_ov_px = max(60, int(3.22 * S) - ov_y)
                    _draw_wrapped_text(
                        draw, combined_overview, int(0.68 * S), ov_y, int(8.40 * S), rem_ov_px,
                        font_body, text_muted_rgb, 24
                    )
                if key_points:
                    card_w, gap, card_y, card_h = 2.74, 0.21, 3.35, 1.78
                    for k_idx, pt_text in enumerate(key_points[:3]):
                        pos_x = 0.68 + k_idx * (card_w + gap)
                        draw_card(pos_x, card_y, card_w, card_h, r=12)
                        draw.text(
                            (int((pos_x + 0.22) * S), int((card_y + 0.18) * S)),
                            f"0{k_idx + 1}", font=font_num_badge, fill=secondary_rgb,
                        )
                        _draw_wrapped_text(
                            draw, pt_text,
                            int((pos_x + 0.22) * S), int((card_y + 0.46) * S),
                            int((card_w - 0.44) * S), int((card_h - 0.58) * S),
                            font_small, text_rgb, 21
                        )

        # 2. TWO PERSON COMPARISON
        elif slide_item.type == "two_person_comparison" and slide_item.comparison:
            card_y = draw_header(subtitle_text or content_text)
            card_h = max(2.8, 5.15 - card_y)
            col_w, col_gap = 4.20, 0.24
            for c_idx, entity in enumerate([slide_item.comparison.entityA, slide_item.comparison.entityB]):
                pos_x = 0.68 + c_idx * (col_w + col_gap)
                dot_rgb = secondary_rgb if c_idx == 0 else accent_rgb
                draw_card(pos_x, card_y, col_w, card_h, r=12)
                ent_name = clean_slide_text(entity.name)
                end_name_y = _draw_wrapped_text(
                    draw, ent_name,
                    int((pos_x + 0.24) * S), int((card_y + 0.18) * S),
                    int((col_w - 0.48) * S), int(0.55 * S),
                    font_card_title, heading_rgb, 24
                )
                line_y = end_name_y + 8
                draw.rectangle(
                    [int((pos_x + 0.24) * S), line_y, int((pos_x + col_w - 0.24) * S), line_y + 2],
                    fill=border_rgb
                )
                if entity.points:
                    b_y = line_y + 12
                    rem_px = max(80, int((card_y + card_h - 0.16) * S) - b_y)
                    _draw_bullets(
                        draw, entity.points[:4],
                        int((pos_x + 0.24) * S), b_y,
                        int((col_w - 0.48) * S), rem_px,
                        font_small, dot_rgb, text_rgb, 21, item_gap=8
                    )

        # 3. TIMELINE
        elif slide_item.type == "timeline" and slide_item.timeline and len(slide_item.timeline) > 0:
            card_y = draw_header(content_text or subtitle_text)
            card_h = max(2.8, 5.15 - card_y)
            card_w, gap = 2.74, 0.21
            for t_idx, item in enumerate(slide_item.timeline[:3]):
                pos_x = 0.68 + t_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, card_h, r=12)
                step_num = clean_slide_text(item.step) or f"0{t_idx + 1}"
                draw.text(
                    (int((pos_x + 0.22) * S), int((card_y + 0.18) * S)),
                    step_num, font=font_step_num, fill=secondary_rgb,
                )
                t_title = clean_slide_text(item.title)
                end_t_y = _draw_wrapped_text(
                    draw, t_title,
                    int((pos_x + 0.22) * S), int((card_y + 0.50) * S),
                    int((card_w - 0.44) * S), int(0.75 * S),
                    font_card_title, heading_rgb, 23
                )
                desc_y = end_t_y + 10
                rem_desc_px = max(60, int((card_y + card_h - 0.16) * S) - desc_y)
                _draw_wrapped_text(
                    draw, clean_slide_text(item.desc),
                    int((pos_x + 0.22) * S), desc_y,
                    int((card_w - 0.44) * S), rem_desc_px,
                    font_small, text_muted_rgb, 21
                )

        # 4. STATISTICS
        elif slide_item.type == "statistics" and slide_item.stats and len(slide_item.stats) > 0:
            card_y = draw_header(content_text or subtitle_text)
            metric_h, card_w, gap = 1.32, 2.74, 0.21
            for s_idx, st in enumerate(slide_item.stats[:3]):
                pos_x = 0.68 + s_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, metric_h, r=12)
                end_v_y = _draw_wrapped_text(
                    draw, clean_slide_text(st.value),
                    int((pos_x + 0.20) * S), int((card_y + 0.15) * S),
                    int((card_w - 0.40) * S), int(0.48 * S),
                    font_stat_val, secondary_rgb, 38
                )
                _draw_wrapped_text(
                    draw, clean_slide_text(st.label),
                    int((pos_x + 0.20) * S), end_v_y + 6,
                    int((card_w - 0.40) * S), int((card_y + metric_h - 0.12) * S) - (end_v_y + 6),
                    font_small, text_muted_rgb, 20
                )
            if key_points:
                bottom_y = card_y + metric_h + 0.15
                bottom_h = max(1.25, 5.15 - bottom_y)
                draw_card(0.68, bottom_y, 8.64, bottom_h, r=12)
                _draw_bullets(
                    draw, key_points[:3],
                    int(0.92 * S), int((bottom_y + 0.16) * S),
                    int(8.16 * S), int((bottom_h - 0.30) * S),
                    font_small, accent_rgb, text_rgb, 21, item_gap=7
                )

        # 5. BIG TYPOGRAPHY / PHOTO MAGAZINE
        elif slide_item.type in ("big_typography", "photo_magazine") or slide_item.quote:
            card_y = draw_header(subtitle_text)
            card_h = max(2.9, 5.15 - card_y)
            raw_quote = slide_item.quote.text if (slide_item.quote and slide_item.quote.text) else content_text
            clean_quote = clean_slide_text(raw_quote).strip("«»\"'")

            if has_img:
                _paste_framed_photo(
                    img, draw, slide_item.image_bytes_b64,
                    int(0.72 * S), int((card_y + 0.04) * S), int(3.52 * S), int((card_h - 0.08) * S),
                    card_bg_rgb, secondary_rgb,
                )
                rx, rw = 4.46, 4.86
                draw_card(rx, card_y, rw, card_h, r=12)
                end_q_y = _draw_wrapped_text(
                    draw, clean_quote,
                    int((rx + 0.24) * S), int((card_y + 0.18) * S),
                    int((rw - 0.48) * S), int(1.45 * S),
                    font_body, heading_rgb, 22
                )
                if key_points:
                    b_y = end_q_y + 14
                    rem_px = max(80, int((card_y + card_h - 0.16) * S) - b_y)
                    _draw_bullets(
                        draw, key_points[:3],
                        int((rx + 0.24) * S), b_y,
                        int((rw - 0.48) * S), rem_px,
                        font_small, secondary_rgb, text_rgb, 21, item_gap=7
                    )
            else:
                q_h = 1.40
                draw_card(0.68, card_y, 8.64, q_h, r=12)
                _draw_wrapped_text(
                    draw, clean_quote,
                    int(0.94 * S), int((card_y + 0.18) * S),
                    int(8.12 * S), int((q_h - 0.32) * S),
                    font_quote, heading_rgb, 24
                )
                if key_points:
                    card_w, gap = 2.74, 0.21
                    pillar_y = card_y + q_h + 0.16
                    pillar_h = max(1.45, 5.15 - pillar_y)
                    for p_idx, item in enumerate(key_points[:3]):
                        pos_x = 0.68 + p_idx * (card_w + gap)
                        draw_card(pos_x, pillar_y, card_w, pillar_h, r=12)
                        draw.text(
                            (int((pos_x + 0.22) * S), int((pillar_y + 0.16) * S)),
                            f"0{p_idx + 1}", font=font_num_badge, fill=secondary_rgb,
                        )
                        _draw_wrapped_text(
                            draw, item,
                            int((pos_x + 0.22) * S), int((pillar_y + 0.44) * S),
                            int((card_w - 0.44) * S), int((pillar_h - 0.56) * S),
                            font_small, text_rgb, 21
                        )

        # 6. KEY TAKEAWAY / CONCLUSION
        elif slide_item.type in ("key_takeaway", "conclusion"):
            card_y = draw_header(content_text or subtitle_text)
            card_h = max(2.8, 5.15 - card_y)
            card_w, gap = 2.74, 0.21
            for k_idx, item in enumerate(key_points[:3]):
                pos_x = 0.68 + k_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, card_h, r=12)
                draw.text(
                    (int((pos_x + 0.22) * S), int((card_y + 0.18) * S)),
                    f"0{k_idx + 1}", font=font_step_num, fill=secondary_rgb,
                )
                _draw_wrapped_text(
                    draw, item,
                    int((pos_x + 0.22) * S), int((card_y + 0.52) * S),
                    int((card_w - 0.44) * S), int((card_h - 0.68) * S),
                    font_body, text_rgb, 23
                )

        # 7. SPLIT SCREEN / PHOTO SPLIT
        else:
            card_y = draw_header(subtitle_text)
            card_h = max(2.9, 5.15 - card_y)
            col_w, col_gap = 4.20, 0.24
            pos_xl = 0.68
            pos_xr = pos_xl + col_w + col_gap

            if has_img:
                draw_card(pos_xl, card_y, col_w, card_h, r=12)
                cur_left_y = int((card_y + 0.18) * S)
                if content_text:
                    cur_left_y = _draw_wrapped_text(
                        draw, content_text,
                        int((pos_xl + 0.24) * S), cur_left_y,
                        int((col_w - 0.48) * S), int(1.45 * S),
                        font_small, text_rgb, 21
                    )
                    cur_left_y += 12
                if key_points:
                    rem_px = max(70, int((card_y + card_h - 0.16) * S) - cur_left_y)
                    _draw_bullets(
                        draw, key_points[:3],
                        int((pos_xl + 0.24) * S), cur_left_y,
                        int((col_w - 0.48) * S), rem_px,
                        font_small, accent_rgb, text_rgb, 20, item_gap=7
                    )
                _paste_framed_photo(
                    img, draw, slide_item.image_bytes_b64,
                    int((pos_xr + 0.04) * S), int((card_y + 0.04) * S),
                    int((col_w - 0.08) * S), int((card_h - 0.08) * S),
                    card_bg_rgb, secondary_rgb,
                )
            else:
                draw_card(pos_xl, card_y, col_w, card_h, r=12)
                if content_text:
                    _draw_wrapped_text(
                        draw, content_text,
                        int((pos_xl + 0.26) * S), int((card_y + 0.22) * S),
                        int((col_w - 0.52) * S), int((card_h - 0.44) * S),
                        font_body, text_rgb, 23
                    )
                draw_card(pos_xr, card_y, col_w, card_h, r=12)
                if key_points:
                    _draw_bullets(
                        draw, key_points[:4],
                        int((pos_xr + 0.26) * S), int((card_y + 0.22) * S),
                        int((col_w - 0.52) * S), int((card_h - 0.44) * S),
                        font_small, accent_rgb, text_rgb, 22, item_gap=8
                    )

        images.append(img)

    buf = io.BytesIO()
    if images:
        images[0].save(
            buf,
            format="PDF",
            save_all=True,
            append_images=images[1:],
            resolution=150.0,
        )
    return buf.getvalue()


def convert_pptx_to_pdf_libreoffice(pptx_bytes: bytes) -> Optional[bytes]:
    """Converts PPTX bytes to vector-sharp PDF using headless LibreOffice if installed."""
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_path:
        win_paths = [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        for wp in win_paths:
            if os.path.exists(wp):
                soffice_path = wp
                break

    if not soffice_path:
        return None

    temp_dir = tempfile.mkdtemp(prefix="ai_pres_pdf_")
    try:
        input_pptx = os.path.join(temp_dir, "presentation.pptx")
        with open(input_pptx, "wb") as f:
            f.write(pptx_bytes)

        cmd = [soffice_path, "--headless", "--convert-to", "pdf", input_pptx, "--outdir", temp_dir]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)

        output_pdf = os.path.join(temp_dir, "presentation.pdf")
        if os.path.exists(output_pdf):
            with open(output_pdf, "rb") as f:
                return f.read()
    except Exception as e:
        logger.warning(f"LibreOffice conversion failed: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return None


def build_pdf_deck(presentation: PresentationData, pptx_bytes: Optional[bytes] = None) -> bytes:
    """
    Builds a 16:9 PDF deck.
    Tries LibreOffice first; falls back to the built-in Pillow HD Renderer
    (which renders embedded photos and Kazakh/Russian/English typography).
    """
    if pptx_bytes:
        pdf_data = convert_pptx_to_pdf_libreoffice(pptx_bytes)
        if pdf_data:
            return pdf_data

    logger.info("Generating 16:9 HD PDF via built-in Pillow engine (zero extra dependencies)...")
    return build_pdf_pillow(presentation)
