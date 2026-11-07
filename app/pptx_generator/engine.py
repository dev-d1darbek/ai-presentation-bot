"""
Minimalist 16:9 Presentation Engine using python-pptx.
Designed with pure Swiss / Apple Keynote minimalism:
- Subtle, crisp corner radius (adjustments[0] = 0.022) instead of bloated bubbles
- 100% flat cards (zero drop shadows via XML effectRef idx="0")
- Zero overlapping side-bars or sticking-out lines
- Zero noisy boilerplate labels or emojis
"""
import io
from typing import Optional, List
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

from app.core.types import PresentationData, SlideContent
from app.core.themes import THEMES_REGISTRY, get_theme_heading_color


def hex_to_rgb(hex_code: str) -> RGBColor:
    """Convert 6-character hex string to RGBColor."""
    clean = hex_code.strip().lstrip('#')
    if len(clean) == 3:
        clean = ''.join([c * 2 for c in clean])
    if len(clean) != 6:
        clean = '000000'
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
    """
    Creates a flat, minimalist card with a subtle corner radius and zero drop shadow.
    """
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


def add_text_block(
    slide,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    font_size: float,
    color_rgb: RGBColor,
    bold: bool = False,
    italic: bool = False,
    align=PP_ALIGN.LEFT,
    font_name: str = "Arial",
    line_spacing: float = 1.25,
):
    """Adds a clean, zero-margin text block."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.italic = italic
    p.font.color.rgb = color_rgb
    p.alignment = align
    p.line_spacing = line_spacing
    return tb


def add_colored_bullets(
    text_frame,
    items: List[str],
    dot_color_hex: str,
    text_color_hex: str,
    font_size_pt: float = 10.0,
    space_after_pt: float = 8.0,
    font_name: str = "Arial",
):
    """Adds minimalist bullet points with colored dots and comfortable line spacing."""
    dot_rgb = hex_to_rgb(dot_color_hex)
    text_rgb = hex_to_rgb(text_color_hex)

    for idx, item in enumerate(items):
        p = (
            text_frame.paragraphs[0]
            if (idx == 0 and len(text_frame.paragraphs[0].text) == 0)
            else text_frame.add_paragraph()
        )
        p.space_after = Pt(space_after_pt)
        p.line_spacing = 1.22

        r_dot = p.add_run()
        r_dot.text = "•   "
        r_dot.font.bold = True
        r_dot.font.size = Pt(font_size_pt)
        r_dot.font.name = font_name
        r_dot.font.color.rgb = dot_rgb

        r_text = p.add_run()
        r_text.text = str(item)
        r_text.font.size = Pt(font_size_pt)
        r_text.font.name = font_name
        r_text.font.color.rgb = text_rgb


def build_pptx_deck(presentation: PresentationData) -> bytes:
    """
    Generates a clean, minimalist 16:9 widescreen presentation deck.
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

        # Slide Background
        bg_fill = slide.background.fill
        bg_fill.solid()
        bg_fill.fore_color.rgb = bg_rgb

        slide_title = slide_item.title or f"Слайд {idx + 1}"
        content_text = slide_item.content or ""
        key_points = slide_item.key_points or []

        def add_minimal_header(lead_text: Optional[str] = None) -> float:
            """
            Renders a quiet, minimalist header:
            - Slide title on the left
            - Subtle slide number on the top right (e.g. 02 / 15)
            - Optional lead paragraph below title
            """
            add_text_block(
                slide,
                slide_title,
                x=0.70,
                y=0.48,
                w=7.70,
                h=0.45,
                font_size=19,
                color_rgb=heading_rgb,
                bold=True,
                font_name=font_face,
                line_spacing=1.1,
            )

            add_text_block(
                slide,
                f"{idx + 1:02d} / {total_slides:02d}",
                x=8.45,
                y=0.54,
                w=0.85,
                h=0.28,
                font_size=9.0,
                color_rgb=text_muted_rgb,
                align=PP_ALIGN.RIGHT,
                font_name=font_face,
            )

            if lead_text:
                is_long = len(lead_text) > 110
                para_h = 0.68 if is_long else 0.36
                add_text_block(
                    slide,
                    lead_text,
                    x=0.70,
                    y=1.00,
                    w=8.60,
                    h=para_h,
                    font_size=10.0,
                    color_rgb=text_muted_rgb,
                    font_name=font_face,
                    line_spacing=1.22,
                )
                return 1.00 + para_h + 0.16
            return 1.12

        # =====================================================================
        # 1. COVER SLIDE (Pure Swiss / Apple Editorial Minimalism)
        # =====================================================================
        if idx == 0 or slide_item.type == "cover":
            add_flat_line(slide, x=0.70, y=0.72, w=0.55, h=0.04, fill_rgb=secondary_rgb)

            add_text_block(
                slide,
                slide_title,
                x=0.70,
                y=0.92,
                w=8.60,
                h=1.15,
                font_size=26,
                color_rgb=heading_rgb,
                bold=True,
                font_name=font_face,
                line_spacing=1.12,
            )

            sub_parts = []
            if slide_item.subtitle:
                sub_parts.append(slide_item.subtitle.strip())
            if content_text:
                sub_parts.append(content_text.strip())
            combined_overview = " — ".join(sub_parts) if len(sub_parts) > 1 else (sub_parts[0] if sub_parts else "")

            if combined_overview:
                add_text_block(
                    slide,
                    combined_overview,
                    x=0.70,
                    y=2.15,
                    w=8.20,
                    h=0.95,
                    font_size=10.5,
                    color_rgb=text_muted_rgb,
                    font_name=font_face,
                    line_spacing=1.28,
                )

            if key_points:
                card_w = 2.72
                gap = 0.22
                card_y = 3.35
                card_h = 1.62
                for k_idx, pt_text in enumerate(key_points[:3]):
                    pos_x = 0.70 + k_idx * (card_w + gap)
                    add_minimal_card(
                        slide, pos_x, card_y, card_w, card_h, card_bg_rgb, border_rgb, radius=0.02
                    )

                    add_text_block(
                        slide,
                        f"0{k_idx + 1}",
                        x=pos_x + 0.24,
                        y=card_y + 0.20,
                        w=0.60,
                        h=0.28,
                        font_size=11,
                        color_rgb=secondary_rgb,
                        bold=True,
                        font_name=font_face,
                    )

                    add_text_block(
                        slide,
                        pt_text,
                        x=pos_x + 0.24,
                        y=card_y + 0.52,
                        w=card_w - 0.48,
                        h=card_h - 0.68,
                        font_size=9.5,
                        color_rgb=text_rgb,
                        font_name=font_face,
                        line_spacing=1.22,
                    )

        # =====================================================================
        # 2. TWO-PERSON / TWO-ENTITY COMPARISON SLIDE
        # =====================================================================
        elif slide_item.type == "two_person_comparison" and slide_item.comparison:
            card_y = add_minimal_header(content_text)
            card_h = 5.05 - card_y
            col_w = 4.18
            col_gap = 0.24

            for c_idx, entity in enumerate([slide_item.comparison.entityA, slide_item.comparison.entityB]):
                pos_x = 0.70 + c_idx * (col_w + col_gap)
                dot_hex = theme.secondaryColor if c_idx == 0 else theme.accentColor

                add_minimal_card(
                    slide, pos_x, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018
                )

                add_text_block(
                    slide,
                    entity.name,
                    x=pos_x + 0.28,
                    y=card_y + 0.22,
                    w=col_w - 0.56,
                    h=0.34,
                    font_size=12,
                    color_rgb=heading_rgb,
                    bold=True,
                    font_name=font_face,
                )

                add_flat_line(
                    slide,
                    x=pos_x + 0.28,
                    y=card_y + 0.62,
                    w=col_w - 0.56,
                    h=0.01,
                    fill_rgb=border_rgb,
                )

                if entity.points:
                    tb = slide.shapes.add_textbox(
                        Inches(pos_x + 0.28),
                        Inches(card_y + 0.76),
                        Inches(col_w - 0.56),
                        Inches(card_h - 0.92),
                    )
                    tf = tb.text_frame
                    tf.word_wrap = True
                    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
                    add_colored_bullets(tf, entity.points, dot_hex, theme.textColor, 9.5, 6.0, font_face)

        # =====================================================================
        # 3. TIMELINE SLIDE (3 Clean Cards)
        # =====================================================================
        elif slide_item.type == "timeline" and slide_item.timeline and len(slide_item.timeline) > 0:
            card_y = add_minimal_header(content_text)
            card_h = 5.05 - card_y
            card_w = 2.72
            gap = 0.22

            for t_idx, item in enumerate(slide_item.timeline[:3]):
                pos_x = 0.70 + t_idx * (card_w + gap)
                add_minimal_card(
                    slide, pos_x, card_y, card_w, card_h, card_bg_rgb, border_rgb, radius=0.02
                )

                step_num = item.step.strip() if item.step else f"0{t_idx + 1}"
                add_text_block(
                    slide,
                    step_num,
                    x=pos_x + 0.24,
                    y=card_y + 0.22,
                    w=card_w - 0.48,
                    h=0.34,
                    font_size=14,
                    color_rgb=secondary_rgb,
                    bold=True,
                    font_name=font_face,
                )

                add_text_block(
                    slide,
                    item.title,
                    x=pos_x + 0.24,
                    y=card_y + 0.62,
                    w=card_w - 0.48,
                    h=0.45,
                    font_size=10.5,
                    color_rgb=heading_rgb,
                    bold=True,
                    font_name=font_face,
                    line_spacing=1.15,
                )

                add_text_block(
                    slide,
                    item.desc,
                    x=pos_x + 0.24,
                    y=card_y + 1.14,
                    w=card_w - 0.48,
                    h=card_h - 1.30,
                    font_size=9.5,
                    color_rgb=text_muted_rgb,
                    font_name=font_face,
                    line_spacing=1.22,
                )

        # =====================================================================
        # 4. STATISTICS SLIDE (3 Clean Metric Cards + Summary List)
        # =====================================================================
        elif slide_item.type == "statistics" and slide_item.stats and len(slide_item.stats) > 0:
            card_y = add_minimal_header(content_text)
            metric_h = 1.38
            card_w = 2.72
            gap = 0.22

            for s_idx, st in enumerate(slide_item.stats[:3]):
                pos_x = 0.70 + s_idx * (card_w + gap)
                add_minimal_card(
                    slide, pos_x, card_y, card_w, metric_h, card_bg_rgb, border_rgb, radius=0.02
                )

                add_text_block(
                    slide,
                    st.value,
                    x=pos_x + 0.22,
                    y=card_y + 0.18,
                    w=card_w - 0.44,
                    h=0.55,
                    font_size=22,
                    color_rgb=secondary_rgb,
                    bold=True,
                    font_name=font_face,
                )

                add_text_block(
                    slide,
                    st.label,
                    x=pos_x + 0.22,
                    y=card_y + 0.76,
                    w=card_w - 0.44,
                    h=0.48,
                    font_size=9.0,
                    color_rgb=text_muted_rgb,
                    font_name=font_face,
                    line_spacing=1.15,
                )

            if key_points:
                bottom_y = card_y + metric_h + 0.18
                bottom_h = 5.05 - bottom_y
                add_minimal_card(
                    slide, 0.70, bottom_y, 8.60, bottom_h, card_bg_rgb, border_rgb, radius=0.018
                )

                tb_bp = slide.shapes.add_textbox(
                    Inches(0.98), Inches(bottom_y + 0.20), Inches(8.04), Inches(bottom_h - 0.36)
                )
                tf_bp = tb_bp.text_frame
                tf_bp.word_wrap = True
                tf_bp.margin_left = tf_bp.margin_top = tf_bp.margin_right = tf_bp.margin_bottom = 0
                add_colored_bullets(tf_bp, key_points[:3], theme.accentColor, theme.textColor, 9.5, 5.0, font_face)

        # =====================================================================
        # 5. BIG TYPOGRAPHY / STATEMENT SLIDE
        # =====================================================================
        elif slide_item.type == "big_typography" or slide_item.quote:
            card_y = add_minimal_header(slide_item.subtitle)
            q_h = 1.65

            add_minimal_card(
                slide, 0.70, card_y, 8.60, q_h, card_bg_rgb, border_rgb, radius=0.018
            )

            quote_text = slide_item.quote.text if slide_item.quote else content_text
            clean_quote = quote_text.strip().strip("«»\"'")

            add_text_block(
                slide,
                clean_quote,
                x=1.00,
                y=card_y + 0.24,
                w=8.00,
                h=q_h - 0.48,
                font_size=12.0,
                color_rgb=heading_rgb,
                bold=True,
                font_name=font_face,
                line_spacing=1.28,
            )

            if key_points:
                card_w = 2.72
                gap = 0.22
                pillar_y = card_y + q_h + 0.20
                pillar_h = 5.05 - pillar_y
                for p_idx, item in enumerate(key_points[:3]):
                    pos_x = 0.70 + p_idx * (card_w + gap)
                    add_minimal_card(
                        slide, pos_x, pillar_y, card_w, pillar_h, card_bg_rgb, border_rgb, radius=0.02
                    )

                    add_text_block(
                        slide,
                        f"0{p_idx + 1}",
                        x=pos_x + 0.24,
                        y=pillar_y + 0.18,
                        w=0.60,
                        h=0.26,
                        font_size=11.0,
                        color_rgb=secondary_rgb,
                        bold=True,
                        font_name=font_face,
                    )

                    add_text_block(
                        slide,
                        item,
                        x=pos_x + 0.24,
                        y=pillar_y + 0.48,
                        w=card_w - 0.48,
                        h=pillar_h - 0.64,
                        font_size=9.5,
                        color_rgb=text_rgb,
                        font_name=font_face,
                        line_spacing=1.22,
                    )

        # =====================================================================
        # 6. KEY TAKEAWAYS / CONCLUSION SLIDE
        # =====================================================================
        elif slide_item.type in ("key_takeaway", "conclusion"):
            card_y = add_minimal_header(content_text)
            card_h = 5.05 - card_y
            card_w = 2.72
            gap = 0.22

            for k_idx, item in enumerate(key_points[:3]):
                pos_x = 0.70 + k_idx * (card_w + gap)
                add_minimal_card(
                    slide, pos_x, card_y, card_w, card_h, card_bg_rgb, border_rgb, radius=0.02
                )

                add_text_block(
                    slide,
                    f"0{k_idx + 1}",
                    x=pos_x + 0.24,
                    y=card_y + 0.22,
                    w=0.60,
                    h=0.32,
                    font_size=13,
                    color_rgb=secondary_rgb,
                    bold=True,
                    font_name=font_face,
                )

                add_text_block(
                    slide,
                    item,
                    x=pos_x + 0.24,
                    y=card_y + 0.62,
                    w=card_w - 0.48,
                    h=card_h - 0.80,
                    font_size=10.0,
                    color_rgb=text_rgb,
                    font_name=font_face,
                    line_spacing=1.25,
                )

        # =====================================================================
        # 7. SPLIT SCREEN (Clean Two-Column Layout, Zero Redundant Labels)
        # =====================================================================
        else:
            card_y = add_minimal_header(slide_item.subtitle)
            card_h = 5.05 - card_y
            col_w = 4.18
            col_gap = 0.24

            pos_xl = 0.70
            add_minimal_card(
                slide, pos_xl, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018
            )

            if content_text:
                add_text_block(
                    slide,
                    content_text,
                    x=pos_xl + 0.28,
                    y=card_y + 0.26,
                    w=col_w - 0.56,
                    h=card_h - 0.52,
                    font_size=10.0,
                    color_rgb=text_rgb,
                    font_name=font_face,
                    line_spacing=1.30,
                )

            pos_xr = pos_xl + col_w + col_gap
            add_minimal_card(
                slide, pos_xr, card_y, col_w, card_h, card_bg_rgb, border_rgb, radius=0.018
            )

            if key_points:
                tb_rc = slide.shapes.add_textbox(
                    Inches(pos_xr + 0.28),
                    Inches(card_y + 0.26),
                    Inches(col_w - 0.56),
                    Inches(card_h - 0.52),
                )
                tf_rc = tb_rc.text_frame
                tf_rc.word_wrap = True
                tf_rc.margin_left = tf_rc.margin_top = tf_rc.margin_right = tf_rc.margin_bottom = 0
                add_colored_bullets(tf_rc, key_points, theme.accentColor, theme.textColor, 9.8, 8.0, font_face)

    output_stream = io.BytesIO()
    prs.save(output_stream)
    return output_stream.getvalue()
