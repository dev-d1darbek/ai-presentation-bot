"""
Zero-Extra-Dependency PDF Export Engine for AI Presentation Bot.
1. Uses headless LibreOffice if available on the host.
2. Otherwise uses a built-in High-Resolution Pillow (PIL) 16:9 PDF Renderer
   (Pillow is already installed as a core dependency of python-pptx, so it NEVER
   throws ModuleNotFoundError: No module named 'reportlab' and supports full Kazakh Cyrillic).
"""
import io
import os
import shutil
import subprocess
import tempfile
import logging
from typing import Optional, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from app.core.types import PresentationData
from app.core.themes import THEMES_REGISTRY, get_theme_heading_color
from app.pptx_generator.engine import build_pptx_deck

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
    item_gap: int = 12,
):
    """Draws clean colored bullets with wrapped text."""
    cur_y = y
    for item in items:
        if cur_y + line_height > y + max_h:
            break
        # Draw bullet dot
        draw.ellipse([x, cur_y + 8, x + 7, cur_y + 15], fill=dot_color)
        lines = _wrap_text_lines(draw, str(item), font, max_w - 24)
        for line in lines:
            if cur_y + line_height > y + max_h:
                break
            draw.text((x + 22, cur_y), line, font=font, fill=text_color)
            cur_y += line_height
        cur_y += item_gap


def build_pdf_pillow(presentation: PresentationData) -> bytes:
    """
    Renders a crisp, minimalist 16:9 widescreen PDF (1600x900 per slide) using Pillow.
    Works on every OS (Windows/Linux/macOS) with zero extra libraries beyond python-pptx.
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

    # Scale: 10.0" x 5.625" -> 1600 x 900 px (1 inch = 160 px)
    W, H = 1600, 900
    S = 160.0  # px per inch

    font_cover_title = _load_font(46, bold=True)
    font_slide_title = _load_font(34, bold=True)
    font_stat_val = _load_font(40, bold=True)
    font_step_num = _load_font(24, bold=True)
    font_card_title = _load_font(21, bold=True)
    font_quote = _load_font(22, bold=True)
    font_num_badge = _load_font(20, bold=True)
    font_body_lg = _load_font(19, bold=False)
    font_body = _load_font(18, bold=False)
    font_small = _load_font(16, bold=False)

    images: List[Image.Image] = []
    total_slides = len(presentation.slides)

    for idx, slide_item in enumerate(presentation.slides):
        img = Image.new("RGB", (W, H), bg_rgb)
        draw = ImageDraw.Draw(img)

        slide_title = slide_item.title or f"Слайд {idx + 1}"
        content_text = slide_item.content or ""
        key_points = slide_item.key_points or []

        def draw_card(cx: float, cy: float, cw: float, ch: float, r: int = 12):
            x0, y0 = int(cx * S), int(cy * S)
            x1, y1 = int((cx + cw) * S), int((cy + ch) * S)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=card_bg_rgb, outline=border_rgb, width=2)

        def draw_header(lead_text: Optional[str] = None) -> float:
            # Title
            _draw_wrapped_text(
                draw, slide_title, int(0.70 * S), int(0.48 * S), int(7.70 * S), int(0.50 * S),
                font_slide_title, heading_rgb, 40
            )
            # Counter
            counter_str = f"{idx + 1:02d} / {total_slides:02d}"
            bbox = draw.textbbox((0, 0), counter_str, font=font_small)
            cw = bbox[2] - bbox[0]
            draw.text((int(9.30 * S) - cw, int(0.56 * S)), counter_str, font=font_small, fill=text_muted_rgb)

            if lead_text:
                is_long = len(lead_text) > 110
                para_h = 0.68 if is_long else 0.36
                _draw_wrapped_text(
                    draw, lead_text, int(0.70 * S), int(1.02 * S), int(8.60 * S), int(para_h * S),
                    font_body, text_muted_rgb, 25
                )
                return 1.02 + para_h + 0.16
            return 1.12

        # 1. COVER SLIDE
        if idx == 0 or slide_item.type == "cover":
            draw.rectangle(
                [int(0.70 * S), int(0.72 * S), int(1.25 * S), int(0.76 * S)],
                fill=secondary_rgb
            )
            _draw_wrapped_text(
                draw, slide_title, int(0.70 * S), int(0.92 * S), int(8.60 * S), int(1.15 * S),
                font_cover_title, heading_rgb, 54
            )
            sub_parts = []
            if slide_item.subtitle:
                sub_parts.append(slide_item.subtitle.strip())
            if content_text:
                sub_parts.append(content_text.strip())
            combined_overview = " — ".join(sub_parts) if len(sub_parts) > 1 else (sub_parts[0] if sub_parts else "")
            if combined_overview:
                _draw_wrapped_text(
                    draw, combined_overview, int(0.70 * S), int(2.15 * S), int(8.20 * S), int(0.95 * S),
                    font_body_lg, text_muted_rgb, 27
                )
            if key_points:
                card_w, gap, card_y, card_h = 2.72, 0.22, 3.35, 1.62
                for k_idx, pt_text in enumerate(key_points[:3]):
                    pos_x = 0.70 + k_idx * (card_w + gap)
                    draw_card(pos_x, card_y, card_w, card_h, r=12)
                    draw.text(
                        (int((pos_x + 0.24) * S), int((card_y + 0.20) * S)),
                        f"0{k_idx + 1}",
                        font=font_num_badge,
                        fill=secondary_rgb,
                    )
                    _draw_wrapped_text(
                        draw, pt_text,
                        int((pos_x + 0.24) * S), int((card_y + 0.52) * S),
                        int((card_w - 0.48) * S), int((card_h - 0.68) * S),
                        font_body, text_rgb, 24
                    )

        # 2. TWO PERSON COMPARISON
        elif slide_item.type == "two_person_comparison" and slide_item.comparison:
            card_y = draw_header(content_text)
            card_h = 5.05 - card_y
            col_w, col_gap = 4.18, 0.24
            for c_idx, entity in enumerate([slide_item.comparison.entityA, slide_item.comparison.entityB]):
                pos_x = 0.70 + c_idx * (col_w + col_gap)
                dot_rgb = secondary_rgb if c_idx == 0 else accent_rgb
                draw_card(pos_x, card_y, col_w, card_h, r=12)
                draw.text(
                    (int((pos_x + 0.28) * S), int((card_y + 0.22) * S)),
                    entity.name,
                    font=font_card_title,
                    fill=heading_rgb,
                )
                draw.rectangle(
                    [int((pos_x + 0.28) * S), int((card_y + 0.62) * S), int((pos_x + col_w - 0.28) * S), int((card_y + 0.63) * S)],
                    fill=border_rgb
                )
                if entity.points:
                    _draw_bullets(
                        draw, entity.points,
                        int((pos_x + 0.28) * S), int((card_y + 0.76) * S),
                        int((col_w - 0.56) * S), int((card_h - 0.92) * S),
                        font_body, dot_rgb, text_rgb, 24
                    )

        # 3. TIMELINE
        elif slide_item.type == "timeline" and slide_item.timeline and len(slide_item.timeline) > 0:
            card_y = draw_header(content_text)
            card_h = 5.05 - card_y
            card_w, gap = 2.72, 0.22
            for t_idx, item in enumerate(slide_item.timeline[:3]):
                pos_x = 0.70 + t_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, card_h, r=12)
                step_num = item.step.strip() if item.step else f"0{t_idx + 1}"
                draw.text(
                    (int((pos_x + 0.24) * S), int((card_y + 0.22) * S)),
                    step_num,
                    font=font_step_num,
                    fill=secondary_rgb,
                )
                _draw_wrapped_text(
                    draw, item.title,
                    int((pos_x + 0.24) * S), int((card_y + 0.62) * S),
                    int((card_w - 0.48) * S), int(0.45 * S),
                    font_card_title, heading_rgb, 25
                )
                _draw_wrapped_text(
                    draw, item.desc,
                    int((pos_x + 0.24) * S), int((card_y + 1.14) * S),
                    int((card_w - 0.48) * S), int((card_h - 1.30) * S),
                    font_body, text_muted_rgb, 24
                )

        # 4. STATISTICS
        elif slide_item.type == "statistics" and slide_item.stats and len(slide_item.stats) > 0:
            card_y = draw_header(content_text)
            metric_h, card_w, gap = 1.38, 2.72, 0.22
            for s_idx, st in enumerate(slide_item.stats[:3]):
                pos_x = 0.70 + s_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, metric_h, r=12)
                draw.text(
                    (int((pos_x + 0.22) * S), int((card_y + 0.18) * S)),
                    st.value,
                    font=font_stat_val,
                    fill=secondary_rgb,
                )
                _draw_wrapped_text(
                    draw, st.label,
                    int((pos_x + 0.22) * S), int((card_y + 0.76) * S),
                    int((card_w - 0.44) * S), int(0.48 * S),
                    font_small, text_muted_rgb, 22
                )
            if key_points:
                bottom_y = card_y + metric_h + 0.18
                bottom_h = 5.05 - bottom_y
                draw_card(0.70, bottom_y, 8.60, bottom_h, r=12)
                _draw_bullets(
                    draw, key_points[:3],
                    int(0.98 * S), int((bottom_y + 0.20) * S),
                    int(8.04 * S), int((bottom_h - 0.36) * S),
                    font_body, accent_rgb, text_rgb, 24, item_gap=8
                )

        # 5. BIG TYPOGRAPHY / STATEMENT
        elif slide_item.type == "big_typography" or slide_item.quote:
            card_y = draw_header(slide_item.subtitle)
            q_h = 1.65
            draw_card(0.70, card_y, 8.60, q_h, r=12)
            quote_text = slide_item.quote.text if slide_item.quote else content_text
            clean_quote = quote_text.strip().strip("«»\"'")
            _draw_wrapped_text(
                draw, clean_quote,
                int(1.00 * S), int((card_y + 0.24) * S),
                int(8.00 * S), int((q_h - 0.48) * S),
                font_quote, heading_rgb, 30
            )
            if key_points:
                card_w, gap = 2.72, 0.22
                pillar_y = card_y + q_h + 0.20
                pillar_h = 5.05 - pillar_y
                for p_idx, item in enumerate(key_points[:3]):
                    pos_x = 0.70 + p_idx * (card_w + gap)
                    draw_card(pos_x, pillar_y, card_w, pillar_h, r=12)
                    draw.text(
                        (int((pos_x + 0.24) * S), int((pillar_y + 0.18) * S)),
                        f"0{p_idx + 1}",
                        font=font_num_badge,
                        fill=secondary_rgb,
                    )
                    _draw_wrapped_text(
                        draw, item,
                        int((pos_x + 0.24) * S), int((pillar_y + 0.48) * S),
                        int((card_w - 0.48) * S), int((pillar_h - 0.64) * S),
                        font_body, text_rgb, 24
                    )

        # 6. KEY TAKEAWAY / CONCLUSION
        elif slide_item.type in ("key_takeaway", "conclusion"):
            card_y = draw_header(content_text)
            card_h = 5.05 - card_y
            card_w, gap = 2.72, 0.22
            for k_idx, item in enumerate(key_points[:3]):
                pos_x = 0.70 + k_idx * (card_w + gap)
                draw_card(pos_x, card_y, card_w, card_h, r=12)
                draw.text(
                    (int((pos_x + 0.24) * S), int((card_y + 0.22) * S)),
                    f"0{k_idx + 1}",
                    font=font_step_num,
                    fill=secondary_rgb,
                )
                _draw_wrapped_text(
                    draw, item,
                    int((pos_x + 0.24) * S), int((card_y + 0.62) * S),
                    int((card_w - 0.48) * S), int((card_h - 0.80) * S),
                    font_body, text_rgb, 25
                )

        # 7. SPLIT SCREEN
        else:
            card_y = draw_header(slide_item.subtitle)
            card_h = 5.05 - card_y
            col_w, col_gap = 4.18, 0.24
            pos_xl = 0.70
            draw_card(pos_xl, card_y, col_w, card_h, r=12)
            if content_text:
                _draw_wrapped_text(
                    draw, content_text,
                    int((pos_xl + 0.28) * S), int((card_y + 0.26) * S),
                    int((col_w - 0.56) * S), int((card_h - 0.52) * S),
                    font_body, text_rgb, 26
                )
            pos_xr = pos_xl + col_w + col_gap
            draw_card(pos_xr, card_y, col_w, card_h, r=12)
            if key_points:
                _draw_bullets(
                    draw, key_points,
                    int((pos_xr + 0.28) * S), int((card_y + 0.26) * S),
                    int((col_w - 0.56) * S), int((card_h - 0.52) * S),
                    font_body, accent_rgb, text_rgb, 25
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
    """
    Converts PPTX bytes to vector-sharp PDF using headless LibreOffice if installed.
    """
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
    (zero extra dependencies, works out-of-the-box on Windows/Linux/macOS).
    """
    if pptx_bytes:
        pdf_data = convert_pptx_to_pdf_libreoffice(pptx_bytes)
        if pdf_data:
            return pdf_data

    logger.info("Generating 16:9 HD PDF via built-in Pillow engine (zero extra dependencies)...")
    return build_pdf_pillow(presentation)
