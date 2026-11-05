import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from loguru import logger
from services.image_service import ImageService

class PPTXService:
    @staticmethod
    def create_presentation(data: dict, output_path: str, need_images: bool = True) -> str:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        slides_data = data.get("slides", [])
        
        primary_color = RGBColor(26, 43, 76)
        accent_color = RGBColor(74, 119, 122)
        text_color = RGBColor(40, 40, 40)
        bg_color = RGBColor(248, 249, 250)

        for idx, slide_info in enumerate(slides_data):
            blank_slide_layout = prs.slide_layouts[6]
            slide = prs.slides.add_slide(blank_slide_layout)

            background = slide.background
            fill = background.fill
            fill.solid()
            fill.fore_color.rgb = bg_color

            slide_title = slide_info.get("title", f"Слайд {idx+1}")
            content_items = slide_info.get("content", [])

            if idx == 0:
                txBox = slide.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.333), Inches(3.5))
                tf = txBox.text_frame
                tf.word_wrap = True

                p = tf.paragraphs[0]
                p.text = slide_title
                p.font.size = Pt(44)
                p.font.bold = True
                p.font.color.rgb = primary_color
                p.alignment = PP_ALIGN.CENTER

                if content_items:
                    p2 = tf.add_paragraph()
                    p2.text = "\n".join(content_items)
                    p2.font.size = Pt(22)
                    p2.font.color.rgb = accent_color
                    p2.alignment = PP_ALIGN.CENTER
            else:
                title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(11.7), Inches(1.0))
                tf_title = title_box.text_frame
                tf_title.word_wrap = True
                p_title = tf_title.paragraphs[0]
                p_title.text = slide_title
                p_title.font.size = Pt(28)
                p_title.font.bold = True
                p_title.font.color.rgb = primary_color

                has_image = False
                img_path = f"temp/img_{idx}.jpg"
                if need_images:
                    img_query = slide_info.get("image_query", slide_title)
                    has_image = ImageService.fetch_image(img_query, img_path)

                content_width = Inches(7.0) if has_image else Inches(11.7)
                content_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), content_width, Inches(4.5))
                tf_content = content_box.text_frame
                tf_content.word_wrap = True

                for i, item in enumerate(content_items):
                    p = tf_content.paragraphs[0] if i == 0 else tf_content.add_paragraph()
                    p.text = f"• {item}"
                    p.font.size = Pt(18)
                    p.font.color.rgb = text_color
                    p.space_after = Pt(14)

                if has_image and os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(8.2), Inches(2.0), width=Inches(4.3))
                    except Exception as e:
                        logger.warning(f"Image add error: {e}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        prs.save(output_path)
        return output_path
