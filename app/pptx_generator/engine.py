"""
Minimalist & Photo-Editorial 16:9 Presentation Engine using python-pptx.
Features Zero-Overlap Dynamic Flow Architecture:
- All vertically stacked texts inside headers and cards share a single TextFrame (impossible to collide)
- Never truncates titles or card headings; auto-scales font sizes and flows paragraphs sequentially
- Automatic stripping of repetitive 'ГОСТ 7.32-2017' boilerplate phrases
- Aspect-ratio-preserving Lanczos center-crop for embedded photos
"""
import base64
import io
import re
from typing import Optional, List
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from PIL import Image, ImageOps

from app.core.types import PresentationData
from app.core.themes import THEMES_REGISTRY, get_theme_heading_color


def clean_slide_text(text: Optional[str]) -> str:
    """Strips repetitive 'ГОСТ 7.32-2017' boilerplate and normalizes whitespace."""
    if not text:
        return ""
    s = str(text).strip()
    patterns = [
        r"(?i)\bҚР\s+ЖОО\s+және\s+ГОСТ\s*7\.32[-–—]?2017\s+(?:талаптарына\s+сәйкес|бойынша|стандартына\s+сәйкес)\s*,?\s*",
        r"(?i)\bГОСТ\s*7\.32[-–—]?2017\s+(?:талаптарына\s+сәйкес|бойынша|стандартына\s+сәйкес|стандартымен)\s*,?\s*",
        r"(?i)\bв\s+соответствии\s+с\s+(?:требованиями\s+)?ГОСТ\s*7\.32[-–—]?2017\s*,?\s*",
        r"(?i)\bпо\s+(?:стандарту\s+)?ГОСТ\s*7\.32[-–—]?2017\s*,?\s*",
        r"(?i)\(\s*(?:ҚР\s+ЖОО\s*/\s*)?ГОСТ\s*7\.32[-–—]?2017\s*\)",
        r"(?i)\bГОСТ\s*7\.32[-–—]?2017\b\s*",
    ]
    for pat in patterns:
        s = re.sub(pat, "", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    if len(s) > 1 and s[0].islower():
        s = s[0].upper() + s[1:]
    s = re.sub(r"([.!?]\s+)([а-яәіңғүұқөһa-z])", lambda m: m.group(1) + m.group(2).upper(), s)
    return s


def hex_to_rgb(hex_code: str) -> RGBColor:
    """Convert 6-character hex string to RGBColor."""
    clean = hex_code.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join([c * 2 for c in clean])
    if len(clean) != 6:
        clean = "000000"
    try:
        return RGBColor(int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    except Exception:
        return RGBColor(0, 0, 0)


def disable_shape_shadow(shape):
    """Completely removes PowerPoint's default theme drop shadow from a shape."""
    try:
        shape.shadow.inherit = False
        for elem in shape._element.iter():
            if elem.tag.endswith("effectRef"):
                elem.set("idx", "0")
    except Exception:
        pass


def estimate_chars_per_line(width_in: float, font_pt: float, bold: bool = False) -> int:
    """
    Calibrated character-per-line estimate for Kazakh/Russian Cyrillic in Arial/LiberationSans.
    """
    char_w_em = 0.54 if bold else 0.49
    rag_factor = 0.90
    cpl = int((width_in * 72.0) / (font_pt * char_w_em) * rag_factor)
    return max(10, cpl)


def estimate_wrapped_lines(text: str, width_in: float, font_pt: float, bold: bool = False) -> int:
    """Simulates word-by-word wrapping to accurately count rendered lines."""
    if not text or not text.strip():
        return 0
    cpl = estimate_chars_per_line(width_in, font_pt, bold=bold)
    words = text.strip().split()
    lines = 1
    cur_len = 0
    for w in words:
        wlen = len(w)
        if cur_len == 0:
            cur_len = wlen
            if wlen > cpl:
                lines += wlen // cpl
                cur_len = wlen % cpl
        elif cur_len + 1 + wlen <= cpl:
            cur_len += 1 + wlen
        else:
            lines += 1
            cur_len = wlen
            if wlen > cpl:
                lines += wlen // cpl
                cur_len = wlen % cpl
    return max(1, lines)


def estimate_block_height_in(
    text: str,
    width_in: float,
    font_pt: float,
    line_spacing: float = 1.20,
    bold: bool = False,
    space_after_pt: float = 0.0,
) -> float:
    """Returns estimated vertical height in inches for a paragraph block."""
    if not text or not text.strip():
        return 0.0
    n_lines = estimate_wrapped_lines(text, width_in, font_pt, bold=bold)
    line_h_in = (font_pt * line_spacing) / 72.0
    return n_lines * line_h_in + (space_after_pt / 72.0)


def fit_text_to_lines(
    text: str,
    width_in: float,
    font_pt: float,
    max_lines: int,
    bold: bool = False,
) -> str:
    """
    Ensures body `text` fits within `max_lines` at `font_pt` in `width_in`.
    Prefers keeping complete sentences; only trims if text genuinely exceeds max_lines.
    """
    clean = clean_slide_text(text)
    if not clean:
        return ""
    if estimate_wrapped_lines(clean, width_in, font_pt, bold=bold) <= max_lines:
        return clean

    # Try keeping complete sentences first
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    if len(sentences) > 1:
        acc = []
        for s in sentences:
            candidate = " ".join(acc + [s])
            if estimate_wrapped_lines(candidate, width_in, font_pt, bold=bold) <= max_lines:
                acc.append(s)
            else:
                break
        if acc and len(" ".join(acc)) >= 45:
            return " ".join(acc)

    # Word-by-word trim to fit max_lines
    words = clean.split()
    lo, hi = 1, len(words)
    best = words[0] if words else ""
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = " ".join(words[:mid]).rstrip(",;:-—.") + "."
        if estimate_wrapped_lines(cand, width_in, font_pt, bold=bold) <= max_lines:
            best = cand
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def add_minimal_card(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill_rgb: RGBColor,
    border_rgb: RGBColor,
    radius: float = 0.02,
    border_pt: float = 0.75,
):
    """Creates a flat, minimalist card with a subtle corner radius and zero drop shadow."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    disable_shape_shadow(shape)
    if len(shape.adjustments) > 0:
        shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    if border_pt > 0:
        shape.line.color.rgb = border_rgb
        shape.line.width = Pt(border_pt)
    else:
        shape.line.fill.background()
    return shape


def add_framed_photo(
    slide,
    image_b64: str,
    x: float,
    y: float,
    w: float,
    h: float,
    frame_rgb: RGBColor,
    accent_rgb: RGBColor,
) -> bool:
    """
    Adds a luxury editorial framed picture with aspect-preserving center-crop (no stretching!).
    """
    try:
        raw_bytes = base64.b64decode(image_b64)
        target_w_px = max(200, int(round(w * 240)))
        target_h_px = max(150, int(round(h * 240)))
        with Image.open(io.BytesIO(raw_bytes)).convert("RGB") as img:
            fitted = ImageOps.fit(img, (target_w_px, target_h_px), method=Image.Resampling.LANCZOS)
            out_buf = io.BytesIO()
            fitted.save(out_buf, format="JPEG", quality=92)
            cropped_bytes = out_buf.getvalue()

        add_minimal_card(
            slide, x - 0.04, y - 0.04, w + 0.08, h + 0.08,
            frame_rgb, accent_rgb, radius=0.02, border_pt=1.1,
        )
        slide.shapes.add_picture(io.BytesIO(cropped_bytes), Inches(x), Inches(y), width=Inches(w), height=Inches(h))
        return True
    except Exception:
        return False


def add_flat_line(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill_rgb: RGBColor,
):
    """Creates a flat rectangle line/bar with zero shadow."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    disable_shape_shadow(shape)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_rgb
    shape.line.fill.background()
    return shape


def create_flow_textbox(slide, x: float, y: float, w: float, h: float):
    """Creates a zero-margin top-anchored text frame for sequential multi-paragraph flow."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    return tf


def append_flow_paragraph(
    tf,
    text: str,
    font_size: float,
    color_rgb: RGBColor,
    bold: bool = False,
    italic: bool = False,
    align=PP_ALIGN.LEFT,
    font_name: str = "Arial",
    line_spacing: float = 1.20,
    space_before_pt: float = 0.0,
    space_after_pt: float = 0.0,
):
    """Appends a styled paragraph to an existing TextFrame so stacked texts never overlap."""
    if not text:
        return None
    p = tf.paragraphs[0] if (len(tf.paragraphs) == 1 and len(tf.paragraphs[0].text) == 0) else tf.add_paragraph()
    p.alignment = align
    p.line_spacing = line_spacing
    if space_before_pt > 0:
        p.space_before = Pt(space_before_pt)
    if space_after_pt > 0:
        p.space_after = Pt(space_after_pt)
    run = p.add_run()
    run.text = text
    run.font.name = font_name
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color_rgb
    return p


def append_colored_bullets(
    tf,
    items: List[str],
    dot_rgb: RGBColor,
    text_rgb: RGBColor,
    font_size_pt: float = 9.4,
    space_after_pt: float = 5.0,
    font_name: str = "Arial",
    line_spacing: float = 1.18,
):
    """Appends colored bullet points into an existing TextFrame."""
    for item in items:
        clean_item = clean_slide_text(item)
        if not clean_item:
            continue
        p = (
            tf.paragraphs[0]
            if (len(tf.paragraphs) == 1 and len(tf.paragraphs[0].text) == 0)
            else tf.add_paragraph()
        )
        p.space_after = Pt(space_after_pt)
        p.line_spacing = line_spacing

        r_dot = p.add_run()
        r_dot.text = "•  "
        r_dot.font.bold = True
        r_dot.font.size = Pt(font_size_pt)
        r_dot.font.name = font_name
        r_dot.font.color.rgb = dot_rgb

        r_text = p.add_run()
        r_text.text = clean_item
        r_text.font.size = Pt(font_size_pt)
        r_text.font.name = font_name
        r_text.font.color.rgb = text_rgb


def add_numbered_card(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    badge_str: str,
    body_text: str,
    card_bg_rgb: RGBColor,
    border_rgb: RGBColor,
    badge_rgb: RGBColor,
    text_rgb: RGBColor,
    font_face: str = "Arial",
    title_text: Optional[str] = None,
    heading_rgb: Optional[RGBColor] = None,
):
    """
    Renders a numbered card ('01', full title_text without truncation, and body_text)
    inside a SINGLE TextFrame with auto-scaled font size so text NEVER overlaps or spills out.
    """
    add_minimal_card(slide, x, y, w, h, card_bg_rgb, border_rgb, radius=0.02)
    pad_x = 0.22
    pad_y = 0.16
    inner_w = max(1.0, w - 2 * pad_x)
    inner_h = max(0.6, h - 2 * pad_y)

    clean_title = clean_slide_text(title_text) if title_text else ""
    clean_body = clean_slide_text(body_text)

    badge_pt = 11.5 if h >= 1.65 else 10.5
    body_pt = 9.4 if h >= 1.65 else 9.0
    title_pt = 10.0

    for candidate_body_pt in (9.5, 9.0, 8.6, 8.2):
        candidate_title_pt = candidate_body_pt + 0.6 if len(clean_title) <= 45 else candidate_body_pt + 0.3
        used_h = estimate_block_height_in(badge_str, inner_w, badge_pt, 1.1, bold=True, space_after_pt=4)
        if clean_title:
            used_h += estimate_block_height_in(clean_title, inner_w, candidate_title_pt, 1.14, bold=True, space_after_pt=6)
        avail_for_body = max(0.35, inner_h - used_h)
        max_body_lines = max(2, int((avail_for_body * 72.0) / (candidate_body_pt * 1.20)))
        if estimate_wrapped_lines(clean_body, inner_w, candidate_body_pt, bold=False) <= max_body_lines:
            body_pt = candidate_body_pt
            title_pt = candidate_title_pt
            break
    else:
        body_pt = 8.4
        title_pt = 9.0

    used_top_h = estimate_block_height_in(badge_str, inner_w, badge_pt, 1.1, bold=True, space_after_pt=4)
    if clean_title:
        used_top_h += estimate_block_height_in(clean_title, inner_w, title_pt, 1.14, bold=True, space_after_pt=6)

    avail_body_h = max(0.35, inner_h - used_top_h)
    max_body_lines = max(2, int((avail_body_h * 72.0) / (body_pt * 1.20)))
    fitted_body = fit_text_to_lines(clean_body, inner_w, body_pt, max_lines=max_body_lines, bold=False)

    tf = create_flow_textbox(slide, x + pad_x, y + pad_y, inner_w, inner_h)
    append_flow_paragraph(
        tf, badge_str, font_size=badge_pt, color_rgb=badge_rgb,
        bold=True, font_name=font_face, line_spacing=1.1, space_after_pt=4,
    )
    if clean_title:
        append_flow_paragraph(
            tf, clean_title, font_size=title_pt, color_rgb=heading_rgb or text_rgb,
            bold=True, font_name=font_face, line_spacing=1.14, space_after_pt=6,
        )
    if fitted_body:
        append_flow_paragraph(
            tf, fitted_body, font_size=body_pt, color_rgb=text_rgb,
            bold=False, font_name=font_face, line_spacing=1.18,
        )


def build_pptx_deck(presentation: PresentationData) -> bytes:
    """
    Generates a clean, minimalist or luxury photo-editorial 16:9 widescreen presentation deck
    with guaranteed zero text overlap.
    """
    theme = THEMES_REGISTRY.get(presentation.design_id, THEMES_REGISTRY["swiss_minimalism"])
    heading_color_hex = get_theme_heading_color(theme)
    font_face = "Arial"

    prs = pptx.Presentation()
    prs.slide_width = Inches(10.0)
    prs.slide_height = Inches(5.625)
    blank_layout = prs.slide_layouts[6]

    bg_rgb = hex_to_rgb(theme.bgColor)
    card_bg_rgb = hex_to_rgb(theme.cardBg)
    border_rgb = hex_to_rgb(theme.borderColor)
    accent_rgb = hex_to_rgb(theme.accentColor)
    secondary_rgb = hex_to_rgb(theme.secondaryColor)
    text_rgb = hex_to_rgb(theme.textColor)
    text_muted_rgb = hex_to_rgb(theme.textMuted)
    heading_rgb = hex_to_rgb(heading_color_hex)

    total_slides = len(presentation.slides)

    for idx, slide_item in enumerate(presentation.slides):
        slide = prs.slides.add_slide(blank_layout)

        bg_fill = slide.background.fill
        bg_fill.solid()
        bg_fill.fore_color.rgb = bg_rgb

        slide_title = clean_slide_text(slide_item.title) or f"Слайд {idx + 1}"
        subtitle_text = clean_slide_text(slide_item.subtitle)
        content_text = clean_slide_text(slide_item.content)
        key_points = [clean_slide_text(p) for p in (slide_item.key_points or []) if clean_slide_text(p)]
        has_img = bool(slide_item.image_bytes_b64)

        def add_minimal_header(lead_text: Optional[str] = None) -> float:
            """
            Places full slide_title and lead_text inside ONE unified header TextFrame so they can NEVER overlap,
            and returns the exact dynamic Y coordinate where body cards should start.
            """
            tf_cnt = create_flow_textbox(slide, x=8.52, y=0.40, w=0.80, h=0.28)
            append_flow_paragraph(
                tf_cnt, f"{idx + 1:02d} / {total_slides:02d}",
                font_size=8.8, color_rgb=text_muted_rgb, align=PP_ALIGN.RIGHT, font_name=font_face,
            )

            header_w = 7.78
            if len(slide_title) <= 48:
                t_pt = 17.5
            elif len(slide_title) <= 72:
                t_pt = 15.5
            else:
                t_pt = 14.0

            t_lines = estimate_wrapped_lines(slide_title, header_w, t_pt, bold=True)
            t_h = estimate_block_height_in(slide_title, header_w, t_pt, line_spacing=1.12, bold=True, space_after_pt=5 if lead_text else 0)

            clean_lead = clean_slide_text(lead_text)
            l_h = 0.0
            fitted_lead = ""
            l_pt = 9.3
            if clean_lead:
                l_pt = 9.0 if len(clean_lead) > 210 else 9.4
                max_lead_lines = 2 if t_lines >= 2 else 3
                fitted_lead = fit_text_to_lines(clean_lead, header_w, l_pt, max_lines=max_lead_lines, bold=False)
                l_h = estimate_block_height_in(fitted_lead, header_w, l_pt, line_spacing=1.18, bold=False)

            total_header_h = t_h + l_h + 0.08
            tf_hdr = create_flow_textbox(slide, x=0.68, y=0.38, w=header_w, h=max(0.45, total_header_h))
            append_flow_paragraph(
                tf_hdr, slide_title, font_size=t_pt, color_rgb=heading_rgb,
                bold=True, font_name=font_face, line_spacing=1.12,
                space_after_pt=5.0 if fitted_lead else 0.0,
            )
            if fitted_lead:
                append_flow_paragraph(
                    tf_hdr, fitted_lead, font_size=l_pt, color_rgb=text_muted_rgb,
                    bold=False, font_name=font_face, line_spacing=1.18,
                )

            card_start_y = max(1.06, min(1.92, 0.38 + total_header_h + 0.14))
            return card_start_y

        # =====================================================================
        # 1. COVER SLIDE (Hero Photo Split OR Pure Swiss Minimalism)
        # =====================================================================
        if idx == 0 or slide_item.type in ("cover", "photo_hero"):
            add_flat_line(slide, x=0.68, y=0.52, w=0.65, h=0.05, fill_rgb=secondary_rgb)

            if has_img:
                # Left column (x=0.68, w=4.88, y=0.68..3.32) — Full Title + Overview in ONE TextFrame!
                left_w = 4.88
                avail_top_h = 2.62
                if len(slide_title) <= 45:
                    cov_t_pt = 19.0
                elif len(slide_title) <= 72:
                    cov_t_pt = 16.5
                else:
                    cov_t_pt = 15.0

                cov_t_h = estimate_block_height_in(slide_title, left_w, cov_t_pt, 1.12, bold=True, space_after_pt=8)

                overview_raw = content_text or subtitle_text
                rem_ov_h = max(0.65, avail_top_h - cov_t_h)
                ov_pt = 9.2 if len(overview_raw) > 220 else 9.6
                max_ov_lines = max(3, int((rem_ov_h * 72.0) / (ov_pt * 1.20)))
                fitted_overview = fit_text_to_lines(overview_raw, left_w, ov_pt, max_lines=max_ov_lines, bold=False)

                tf_cov = create_flow_textbox(slide, x=0.68, y=0.68, w=left_w, h=avail_top_h)
                append_flow_paragraph(
                    tf_cov, slide_title, font_size=cov_t_pt, color_rgb=heading_rgb,
                    bold=True, font_name=font_face, line_spacing=1.12, space_after_pt=8.0,
                )
                if fitted_overview:
                    append_flow_paragraph(
                        tf_cov, fitted_overview, font_size=ov_pt, color_rgb=text_muted_rgb,
                        bold=False, font_name=font_face, line_spacing=1.20,
                    )

                add_framed_photo(
                    slide,
                    slide_item.image_bytes_b64,
                    x=5.80,
                    y=0.66,
                    w=3.50,
                    h=2.52,
                    frame_rgb=card_bg_rgb,
                    accent_rgb=secondary_rgb,
                )

                if key_points:
                    card_w, gap, card_y, card_h = 2.74, 0.21, 3.42, 1.72
                    for k_idx, pt_text in enumerate(key_points[:3]):
                        pos_x = 0.68 + k_idx * (card_w + gap)
                        add_numbered_card(
                            slide, pos_x, card_y, card_w, card_h,
                            f"0{k_idx + 1}", pt_text,
                            card_bg_rgb, border_rgb, secondary_rgb, text_rgb, font_face,
                        )
            else:
                full_w = 8.64
                avail_top_h = 2.45
                if len(slide_title) <= 50:
                    cov_t_pt = 22.0
                elif len(slide_title) <= 78:
                    cov_t_pt = 19.0
                else:
                    cov_t_pt = 17.0

                cov_t_h = estimate_block_height_in(slide_title, full_w, cov_t_pt, 1.12, bold=True, space_after_pt=9)

                sub_parts = [p for p in (subtitle_text, content_text) if p]
                combined_overview = " — ".join(sub_parts) if len(sub_parts) > 1 else (sub_parts[0] if sub_parts else "")
                rem_ov_h = max(0.65, avail_top_h - cov_t_h)
                ov_pt = 9.8 if len(combined_overview) > 240 else 10.2
                max_ov_lines = max(3, int((rem_ov_h * 72.0) / (ov_pt * 1.22)))
                fitted_overview = fit_text_to_lines(combined_overview, full_w, ov_pt, max_lines=max_ov_lines, bold=False)

                tf_cov = create_flow_textbox(slide, x=0.68, y=0.72, w=full_w, h=avail_top_h)
                append_flow_paragraph(
                    tf_cov, slide_title, font_size=cov_t_pt, color_rgb=heading_rgb,
                    bold=True, font_name=font_face, line_spacing=1.12, space_after_pt=9.0,
                )
                if fitted_overview:
                    append_flow_paragraph(
                        tf_cov, fitted_overview, font_size=ov_pt, color_rgb=text_muted_rgb,
                        bold=False, font_name=font_face, line_spacing=1.22,
                    )

                if key_points:
                    card_w, gap, card_y, card_h = 2.74, 0.21, 3.35, 1.78
                    for k_idx, pt_text in enumerate(key_points[:3]):
                        pos_x = 0.68 + k_idx * (card_w + gap)
                        add_numbered_card(
                            slide, pos_x, card_y, card_w, card_h,
                            f"0{k_idx + 1}", pt_text,
                            card_bg_rgb, border_rgb, secondary_rgb, text_rgb, font_face,
                        )

        # =====================================================================
        # 2. TWO-PERSON / TWO-ENTITY COMPARISON SLIDE
        # =====================================================================
        elif slide_item.type == "two_person_comparison" and slide_item.comparison:
            lead = subtitle_text or content_text
            card_y = add_minimal_header(lead)
            card_h = max(2.8, 5.15 - card_y)
            col_w = 4.20
            col_gap = 0.24

            for c_idx, entity in enumerate([slide_item.comparison.entityA, slide_item.comparison.entityB]):
                pos_x = 0.68 + c_idx * (col_w + col_gap)
                dot_rgb = secondary_rgb if c_idx == 0 else accent_rgb

                add_minimal_card(slide, pos_x, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018)
                inner_w = col_w - 0.48
                inner_h = card_h - 0.36
                ent_name = clean_slide_text(entity.name) or f"Бағыт {c_idx + 1}"
                ent_pts = [clean_slide_text(p) for p in (entity.points or [])[:4] if clean_slide_text(p)]

                tf_cmp = create_flow_textbox(slide, pos_x + 0.24, card_y + 0.18, inner_w, inner_h)
                append_flow_paragraph(
                    tf_cmp, ent_name,
                    font_size=11.0, color_rgb=heading_rgb, bold=True, font_name=font_face,
                    line_spacing=1.15, space_after_pt=8.0,
                )

                name_h = estimate_block_height_in(ent_name, inner_w, 11.0, 1.15, bold=True, space_after_pt=8.0)
                rem_h = max(1.2, inner_h - name_h)
                b_pt = 9.2 if sum(len(x) for x in ent_pts) > 260 else 9.5
                max_lines_per_bullet = max(2, int((rem_h * 72.0) / (max(1, len(ent_pts)) * b_pt * 1.25)))
                fitted_pts = [fit_text_to_lines(p, inner_w - 0.20, b_pt, max_lines=min(3, max_lines_per_bullet)) for p in ent_pts]
                append_colored_bullets(tf_cmp, fitted_pts, dot_rgb, text_rgb, b_pt, 5.0, font_face)

        # =====================================================================
        # 3. TIMELINE SLIDE (3 Clean Cards with Unified Flow)
        # =====================================================================
        elif slide_item.type == "timeline" and slide_item.timeline and len(slide_item.timeline) > 0:
            lead = content_text or subtitle_text
            card_y = add_minimal_header(lead)
            card_h = max(2.8, 5.15 - card_y)
            card_w = 2.74
            gap = 0.21

            for t_idx, item in enumerate(slide_item.timeline[:3]):
                pos_x = 0.68 + t_idx * (card_w + gap)
                step_num = clean_slide_text(item.step) or f"0{t_idx + 1}"
                add_numbered_card(
                    slide, pos_x, card_y, card_w, card_h,
                    step_num, item.desc,
                    card_bg_rgb, border_rgb, secondary_rgb, text_muted_rgb, font_face,
                    title_text=item.title, heading_rgb=heading_rgb,
                )

        # =====================================================================
        # 4. STATISTICS SLIDE (3 Clean Metric Cards + Summary List)
        # =====================================================================
        elif slide_item.type == "statistics" and slide_item.stats and len(slide_item.stats) > 0:
            lead = content_text or subtitle_text
            card_y = add_minimal_header(lead)
            metric_h = 1.32
            card_w = 2.74
            gap = 0.21

            for s_idx, st in enumerate(slide_item.stats[:3]):
                pos_x = 0.68 + s_idx * (card_w + gap)
                add_minimal_card(slide, pos_x, card_y, card_w, metric_h, card_bg_rgb, border_rgb, radius=0.02)
                inner_w = card_w - 0.40
                inner_h = metric_h - 0.28
                val_str = clean_slide_text(st.value)
                lbl_str = clean_slide_text(st.label)

                val_pt = 19.0 if len(val_str) <= 10 else (16.5 if len(val_str) <= 15 else 14.5)
                fitted_lbl = fit_text_to_lines(lbl_str, inner_w, 8.8, max_lines=3, bold=False)

                tf_st = create_flow_textbox(slide, pos_x + 0.20, card_y + 0.14, inner_w, inner_h)
                append_flow_paragraph(
                    tf_st, val_str, font_size=val_pt, color_rgb=secondary_rgb,
                    bold=True, font_name=font_face, line_spacing=1.08, space_after_pt=4.0,
                )
                append_flow_paragraph(
                    tf_st, fitted_lbl, font_size=8.8, color_rgb=text_muted_rgb,
                    bold=False, font_name=font_face, line_spacing=1.15,
                )

            if key_points:
                bottom_y = card_y + metric_h + 0.15
                bottom_h = max(1.25, 5.15 - bottom_y)
                add_minimal_card(slide, 0.68, bottom_y, 8.64, bottom_h, card_bg_rgb, border_rgb, radius=0.018)
                inner_w = 8.16
                inner_h = bottom_h - 0.30
                tf_bp = create_flow_textbox(slide, 0.92, bottom_y + 0.15, inner_w, inner_h)
                fitted_kps = [fit_text_to_lines(p, inner_w - 0.25, 9.3, max_lines=2) for p in key_points[:3]]
                append_colored_bullets(tf_bp, fitted_kps, accent_rgb, text_rgb, 9.3, 4.5, font_face)

        # =====================================================================
        # 5. PHOTO MAGAZINE / BIG TYPOGRAPHY SLIDE
        # =====================================================================
        elif slide_item.type in ("big_typography", "photo_magazine") or slide_item.quote:
            card_y = add_minimal_header(subtitle_text)
            card_h = max(2.9, 5.15 - card_y)
            raw_quote = slide_item.quote.text if (slide_item.quote and slide_item.quote.text) else content_text
            clean_quote = clean_slide_text(raw_quote).strip("«»\"'")

            if has_img:
                add_framed_photo(
                    slide,
                    slide_item.image_bytes_b64,
                    x=0.72,
                    y=card_y + 0.04,
                    w=3.52,
                    h=card_h - 0.08,
                    frame_rgb=card_bg_rgb,
                    accent_rgb=secondary_rgb,
                )
                rx = 4.46
                rw = 4.86
                add_minimal_card(slide, rx, card_y, rw, card_h, card_bg_rgb, border_rgb, radius=0.018)
                inner_w = rw - 0.48
                inner_h = card_h - 0.36

                body_pt = 9.2 if (len(clean_quote) + sum(len(k) for k in key_points[:3])) > 420 else 9.6
                max_q_lines = 6 if key_points else 10
                fitted_q = fit_text_to_lines(clean_quote, inner_w, body_pt, max_lines=max_q_lines, bold=False)
                q_h = estimate_block_height_in(fitted_q, inner_w, body_pt, 1.20, bold=False, space_after_pt=9.0)

                tf_mag = create_flow_textbox(slide, rx + 0.24, card_y + 0.18, inner_w, inner_h)
                if fitted_q:
                    append_flow_paragraph(
                        tf_mag, fitted_q, font_size=body_pt, color_rgb=heading_rgb,
                        bold=False, font_name=font_face, line_spacing=1.20, space_after_pt=9.0,
                    )
                if key_points:
                    rem_h = max(0.9, inner_h - q_h)
                    max_kp_lines = max(2, int((rem_h * 72.0) / (min(3, len(key_points)) * body_pt * 1.24)))
                    fitted_kps = [fit_text_to_lines(p, inner_w - 0.20, body_pt - 0.2, max_lines=min(3, max_kp_lines)) for p in key_points[:3]]
                    append_colored_bullets(tf_mag, fitted_kps, secondary_rgb, text_rgb, body_pt - 0.2, 5.0, font_face)
            else:
                q_pt = 10.2 if len(clean_quote) <= 280 else 9.5
                fitted_q = fit_text_to_lines(clean_quote, 8.12, q_pt, max_lines=4, bold=False)
                q_lines = estimate_wrapped_lines(fitted_q, 8.12, q_pt, bold=False)
                q_h = max(1.15, min(1.52, q_lines * (q_pt * 1.24 / 72.0) + 0.36))

                add_minimal_card(slide, 0.68, card_y, 8.64, q_h, card_bg_rgb, border_rgb, radius=0.018)
                tf_q = create_flow_textbox(slide, 0.94, card_y + 0.18, 8.12, q_h - 0.32)
                append_flow_paragraph(
                    tf_q, fitted_q, font_size=q_pt, color_rgb=heading_rgb,
                    bold=False, font_name=font_face, line_spacing=1.22,
                )

                if key_points:
                    card_w, gap = 2.74, 0.21
                    pillar_y = card_y + q_h + 0.16
                    pillar_h = max(1.45, 5.15 - pillar_y)
                    for p_idx, item in enumerate(key_points[:3]):
                        pos_x = 0.68 + p_idx * (card_w + gap)
                        add_numbered_card(
                            slide, pos_x, pillar_y, card_w, pillar_h,
                            f"0{p_idx + 1}", item,
                            card_bg_rgb, border_rgb, secondary_rgb, text_rgb, font_face,
                        )

        # =====================================================================
        # 6. KEY TAKEAWAYS / CONCLUSION SLIDE
        # =====================================================================
        elif slide_item.type in ("key_takeaway", "conclusion"):
            lead = content_text or subtitle_text
            card_y = add_minimal_header(lead)
            card_h = max(2.8, 5.15 - card_y)
            card_w = 2.74
            gap = 0.21

            for k_idx, item in enumerate(key_points[:3]):
                pos_x = 0.68 + k_idx * (card_w + gap)
                add_numbered_card(
                    slide, pos_x, card_y, card_w, card_h,
                    f"0{k_idx + 1}", item,
                    card_bg_rgb, border_rgb, secondary_rgb, text_rgb, font_face,
                )

        # =====================================================================
        # 7. SPLIT SCREEN & PHOTO SPLIT (Unified Single-Frame Card + Framed Photo)
        # =====================================================================
        else:
            card_y = add_minimal_header(subtitle_text)
            card_h = max(2.9, 5.15 - card_y)
            col_w = 4.20
            col_gap = 0.24
            pos_xl = 0.68
            pos_xr = pos_xl + col_w + col_gap

            if has_img:
                add_minimal_card(slide, pos_xl, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018)
                inner_w = col_w - 0.48
                inner_h = card_h - 0.36

                total_chars = len(content_text) + sum(len(k) for k in key_points[:3])
                body_pt = 9.0 if total_chars > 430 else (9.3 if total_chars > 320 else 9.6)

                max_c_lines = 7 if key_points else 12
                fitted_c = fit_text_to_lines(content_text, inner_w, body_pt, max_lines=max_c_lines, bold=False)
                c_h = estimate_block_height_in(fitted_c, inner_w, body_pt, 1.20, bold=False, space_after_pt=8.0)

                tf_lc = create_flow_textbox(slide, pos_xl + 0.24, card_y + 0.18, inner_w, inner_h)
                if fitted_c:
                    append_flow_paragraph(
                        tf_lc, fitted_c, font_size=body_pt, color_rgb=text_rgb,
                        bold=False, font_name=font_face, line_spacing=1.20,
                        space_after_pt=8.0 if key_points else 0.0,
                    )
                if key_points:
                    rem_h = max(0.85, inner_h - c_h)
                    b_pt = max(8.6, body_pt - 0.2)
                    max_kp_lines = max(2, int((rem_h * 72.0) / (min(3, len(key_points)) * b_pt * 1.22)))
                    fitted_kps = [fit_text_to_lines(p, inner_w - 0.20, b_pt, max_lines=min(3, max_kp_lines)) for p in key_points[:3]]
                    append_colored_bullets(tf_lc, fitted_kps, accent_rgb, text_rgb, b_pt, 4.5, font_face)

                add_framed_photo(
                    slide,
                    slide_item.image_bytes_b64,
                    x=pos_xr + 0.04,
                    y=card_y + 0.04,
                    w=col_w - 0.08,
                    h=card_h - 0.08,
                    frame_rgb=card_bg_rgb,
                    accent_rgb=secondary_rgb,
                )
            else:
                add_minimal_card(slide, pos_xl, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018)
                inner_w = col_w - 0.52
                inner_h = card_h - 0.44
                if content_text:
                    c_pt = 9.5 if len(content_text) > 320 else 10.0
                    max_c_lines = max(4, int((inner_h * 72.0) / (c_pt * 1.25)))
                    fitted_c = fit_text_to_lines(content_text, inner_w, c_pt, max_lines=max_c_lines, bold=False)
                    tf_l = create_flow_textbox(slide, pos_xl + 0.26, card_y + 0.22, inner_w, inner_h)
                    append_flow_paragraph(
                        tf_l, fitted_c, font_size=c_pt, color_rgb=text_rgb,
                        bold=False, font_name=font_face, line_spacing=1.25,
                    )

                add_minimal_card(slide, pos_xr, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018)
                if key_points:
                    b_pt = 9.3 if sum(len(k) for k in key_points[:4]) > 280 else 9.7
                    max_kp_lines = max(2, int((inner_h * 72.0) / (min(4, len(key_points)) * b_pt * 1.24)))
                    fitted_kps = [fit_text_to_lines(p, inner_w - 0.20, b_pt, max_lines=min(3, max_kp_lines)) for p in key_points[:4]]
                    tf_r = create_flow_textbox(slide, pos_xr + 0.26, card_y + 0.22, inner_w, inner_h)
                    append_colored_bullets(tf_r, fitted_kps, accent_rgb, text_rgb, b_pt, 6.0, font_face)

    output_stream = io.BytesIO()
    prs.save(output_stream)
    return output_stream.getvalue()
