"""
Document Text Extractor (PDF / DOCX / PPTX / TXT) and Multi-Language Speaker Defense Speech (.docx) Builder.
Supports Kazakh (қазақша), Russian (русский), and English (english).
"""
import io
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import zlib
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

import config
from app.core.types import PresentationData

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        paragraphs: List[str] = []
        for elem in tree.iter():
            if elem.tag.endswith("}p"):
                runs = [t.text for t in elem.iter() if t.tag.endswith("}t") and t.text]
                if runs:
                    line = "".join(runs).strip()
                    if line:
                        paragraphs.append(line)
        return "\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"DOCX extraction error: {e}")
        return ""


def extract_text_from_pptx(file_bytes: bytes) -> str:
    try:
        import pptx
        prs = pptx.Presentation(io.BytesIO(file_bytes))
        slides_text: List[str] = []
        for idx, slide in enumerate(prs.slides):
            parts: List[str] = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    txt = shape.text_frame.text.strip()
                    if txt:
                        parts.append(txt)
            if parts:
                slides_text.append(f"Слайд {idx + 1}: " + " | ".join(parts))
        return "\n".join(slides_text)
    except Exception as e:
        logger.warning(f"PPTX extraction error: {e}")
        return ""


def _extract_pdf_pure_python(file_bytes: bytes) -> str:
    extracted_chunks: List[str] = []
    try:
        stream_pattern = re.compile(rb"stream[\r\n]+(.*?)[\r\n]+endstream", re.DOTALL)
        for match in stream_pattern.finditer(file_bytes):
            raw_stream = match.group(1)
            decompressed = None
            try:
                decompressed = zlib.decompress(raw_stream)
            except Exception:
                try:
                    decompressed = zlib.decompress(raw_stream, -15)
                except Exception:
                    decompressed = raw_stream

            if not decompressed:
                continue

            for hex_match in re.finditer(rb"<([0-9A-Fa-f]{4,})>", decompressed):
                hex_str = hex_match.group(1)
                if len(hex_str) % 2 == 0:
                    try:
                        raw_b = bytes.fromhex(hex_str.decode("ascii"))
                        if raw_b.startswith(b"\xfe\xff"):
                            txt = raw_b[2:].decode("utf-16-be", errors="ignore").strip()
                            if len(txt) > 1:
                                extracted_chunks.append(txt)
                    except Exception:
                        pass

            for lit_match in re.finditer(rb"\(([^()]{2,})\)", decompressed):
                lit_bytes = lit_match.group(1)
                for enc in ("utf-8", "cp1251", "latin1"):
                    try:
                        decoded = lit_bytes.decode(enc)
                        if any(c.isalpha() for c in decoded):
                            extracted_chunks.append(decoded)
                            break
                    except Exception:
                        pass
    except Exception as e:
        logger.warning(f"Pure-Python PDF extraction error: {e}")

    return " ".join(extracted_chunks)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            mod = __import__(mod_name)
            reader = mod.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(p.strip() for p in pages if p.strip())
            if len(text) > 20:
                return text
        except Exception:
            pass

    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(file_bytes)
        pages = []
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            pages.append(textpage.get_text_range())
        text = "\n".join(p.strip() for p in pages if p.strip())
        if len(text) > 20:
            return text
    except Exception:
        pass

    pdftotext_bin = shutil.which("pdftotext")
    if pdftotext_bin:
        temp_dir = tempfile.mkdtemp(prefix="pdf_extract_")
        try:
            in_pdf = os.path.join(temp_dir, "doc.pdf")
            out_txt = os.path.join(temp_dir, "doc.txt")
            with open(in_pdf, "wb") as f:
                f.write(file_bytes)
            subprocess.run([pdftotext_bin, "-enc", "UTF-8", in_pdf, out_txt], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            if os.path.exists(out_txt):
                with open(out_txt, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                if len(text) > 20:
                    return text
        except Exception:
            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return _extract_pdf_pure_python(file_bytes)


def extract_text_from_uploaded_file(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    ext = os.path.splitext(filename.lower())[1]
    base_title = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").replace("-", " ").strip()
    if not base_title:
        base_title = "Құжат бойынша презентация"

    text = ""
    if ext == ".docx":
        text = extract_text_from_docx(file_bytes)
    elif ext == ".pdf":
        text = extract_text_from_pdf(file_bytes)
    elif ext == ".pptx":
        text = extract_text_from_pptx(file_bytes)
    elif ext in (".txt", ".md", ".csv", ".json"):
        for enc in ("utf-8", "utf-8-sig", "cp1251", "latin1"):
            try:
                text = file_bytes.decode(enc)
                break
            except Exception:
                pass

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return base_title, text


def generate_speaker_defense_text(presentation: PresentationData) -> str:
    """
    Generates a clean, natural Speaker Defense Script (Қорғау сөзі / Шпаргалка)
    without repetitive standard numbers.
    """
    lang = (presentation.language or "қазақша").lower().strip()
    tmpl = config.TEMPLATE_LIBRARY.get(presentation.template_id or "standard", config.TEMPLATE_LIBRARY["standard"])
    lines: List[str] = []

    if lang == "русский":
        lines.append("🎤 РЕЧЬ ДЛЯ ЗАЩИТЫ ПРЕЗЕНТАЦИИ (ШПАРГАЛКА СПИКЕРА)")
        lines.append(f"📌 Тема: «{presentation.topic}»")
        lines.append(f"📐 Шаблон: {tmpl['title']} • Слайдов: {len(presentation.slides)}")
    elif lang == "english":
        lines.append("🎤 SPEAKER DEFENSE SCRIPT (PRESENTATION NOTES)")
        lines.append(f"📌 Topic: «{presentation.topic}»")
        lines.append(f"📐 Template: {tmpl['title']} • Slides: {len(presentation.slides)}")
    else:
        lines.append("🎤 ПРЕЗЕНТАЦИЯНЫ ҚОРҒАУ СӨЗІ (СПИКЕР ШПАРГАЛКАСЫ)")
        lines.append(f"📌 Тақырып: «{presentation.topic}»")
        lines.append(f"📐 Құрылым үлгісі: {tmpl['title']} • Слайд саны: {len(presentation.slides)} бет")

    lines.append("━" * 38)
    lines.append("")

    total = len(presentation.slides)
    for idx, slide in enumerate(presentation.slides):
        num = idx + 1
        slide_lbl = "СЛАЙД" if lang in ("қазақша", "русский") else "SLIDE"
        lines.append(f"🔹 {num}-{slide_lbl}: {slide.title}")

        if idx == 0:
            lines.append("🗣 Сөйлеу мәтіні:" if lang == "қазақша" else ("🗣 Текст выступления:" if lang == "русский" else "🗣 Opening Speech:"))
            if lang == "русский":
                lines.append(
                    f"«Уважаемые члены комиссии, преподаватели и коллеги! "
                    f"Представляю вашему вниманию исследование на тему «{presentation.topic}». {slide.content}»"
                )
            elif lang == "english":
                lines.append(
                    f"«Distinguished committee members, faculty, and colleagues! "
                    f"I am pleased to present our analytical research on «{presentation.topic}». {slide.content}»"
                )
            else:
                lines.append(
                    f"«Құрметті комиссия мүшелері, оқытушылар және қатысушылар! "
                    f"Назарларыңызға «{presentation.topic}» тақырыбында дайындалған "
                    f"ғылыми-тәжірибелік презентацияны ұсынамын. {slide.content}»"
                )
        elif idx == total - 1:
            lines.append("🗣 Қорытынды сөз:" if lang == "қазақша" else ("🗣 Заключительное слово:" if lang == "русский" else "🗣 Closing Statement:"))
            if lang == "русский":
                lines.append(
                    f"«На заключительном слайде представлены основные выводы и практические рекомендации работы. {slide.content} "
                    + (" ".join(slide.key_points[:2]) if slide.key_points else "")
                    + " Благодарю за внимание! Готов ответить на ваши вопросы.»"
                )
            elif lang == "english":
                lines.append(
                    f"«On our final slide, we summarize our core findings and strategic conclusions. {slide.content} "
                    + (" ".join(slide.key_points[:2]) if slide.key_points else "")
                    + " Thank you for your attention! I welcome any questions.»"
                )
            else:
                lines.append(
                    f"«Соңғы слайдта зерттеудің қорытынды тұжырымдары мен негізгі қағидалары көрсетілген. {slide.content} "
                    + (" ".join(slide.key_points[:2]) if slide.key_points else "")
                    + " Назар қойып тыңдағандарыңызға көп рақмет! Сұрақтарыңызға жауап беруге дайынмын.»"
                )
        else:
            lines.append("🗣 Сөйлеу мәтіні:" if lang == "қазақша" else ("🗣 Текст выступления:" if lang == "русский" else "🗣 Speaker Notes:"))
            if lang == "русский":
                intro_phrases = [
                    "На следующем слайде мы подробно рассматриваем:",
                    "Обратите внимание на ключевые аспекты данного раздела:",
                    "Здесь приведены основные факты и причинно-следственные связи:",
                    "В ходе анализа были выявлены следующие важные показатели:",
                ]
            elif lang == "english":
                intro_phrases = [
                    "Moving to this slide, we examine:",
                    "Let us highlight the critical findings in this section:",
                    "Here we present the primary evidence and causal mechanisms:",
                    "Our analysis reveals the following strategic points:",
                ]
            else:
                intro_phrases = [
                    "Келесі слайдта біз мына мәселеге тоқталамыз:",
                    "Назарларыңызды мына маңызды бөлімге аударғым келеді:",
                    "Осы слайдта негізгі деректер мен себеп-салдарлық байланыстар берілген:",
                    "Талдау барысында келесі негізгі фактілер анықталды:",
                ]
            transition = intro_phrases[idx % len(intro_phrases)]
            speech_parts = [f"«{transition} {slide.content}"]

            if slide.stats:
                stat_strs = [f"{s.label} — {s.value}" for s in slide.stats[:3]]
                speech_parts.append(
                    ("Негізгі көрсеткіштерге назар аударсақ: " if lang == "қазақша" else ("Ключевые показатели: " if lang == "русский" else "Key metrics include: "))
                    + ", ".join(stat_strs) + "."
                )
            elif slide.timeline:
                tl_strs = [f"{t.title} ({t.desc})" for t in slide.timeline[:3]]
                speech_parts.append(
                    ("Даму кезеңдері ретімен: " if lang == "қазақша" else ("Этапы развития: " if lang == "русский" else "Key stages in order: "))
                    + "; ".join(tl_strs) + "."
                )
            elif slide.comparison:
                a_name = slide.comparison.entityA.name
                b_name = slide.comparison.entityB.name
                a_pts = ", ".join(slide.comparison.entityA.points[:2])
                b_pts = ", ".join(slide.comparison.entityB.points[:2])
                speech_parts.append(f"{a_name}: {a_pts}. {b_name}: {b_pts}.")
            elif slide.key_points:
                speech_parts.append(
                    ("Басты дәйектер ретінде мыналарды атап өтуге болады: " if lang == "қазақша" else ("Основные тезисы: " if lang == "русский" else "Key takeaways: "))
                    + " ".join(slide.key_points[:3])
                )

            speech_parts[-1] = speech_parts[-1].rstrip(".") + ".»"
            lines.append(" ".join(speech_parts))

        lines.append("")

    return "\n".join(lines)


def build_defense_speech_docx(presentation: PresentationData) -> bytes:
    speech_text = generate_speaker_defense_text(presentation)
    paragraphs = speech_text.split("\n")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""",
        )

        body_parts: List[str] = []
        for line in paragraphs:
            esc = (
                line.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            if line.startswith("🎤"):
                body_parts.append(
                    f'<w:p><w:pPr><w:spacing w:after="160"/></w:pPr>'
                    f'<w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>{esc}</w:t></w:r></w:p>'
                )
            elif line.startswith("🔹"):
                body_parts.append(
                    f'<w:p><w:pPr><w:spacing w:before="200" w:after="80"/></w:pPr>'
                    f'<w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>{esc}</w:t></w:r></w:p>'
                )
            elif line.startswith("🗣"):
                body_parts.append(
                    f'<w:p><w:pPr><w:spacing w:after="60"/></w:pPr>'
                    f'<w:r><w:rPr><w:b/><w:sz w:val="22"/></w:rPr><w:t>{esc}</w:t></w:r></w:p>'
                )
            else:
                body_parts.append(
                    f'<w:p><w:pPr><w:spacing w:after="100"/></w:pPr>'
                    f'<w:r><w:rPr><w:sz w:val="22"/></w:rPr><w:t>{esc}</w:t></w:r></w:p>'
                )

        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f'<w:body>{"".join(body_parts)}</w:body>'
            "</w:document>"
        )
        z.writestr("word/document.xml", doc_xml)

    return buf.getvalue()
