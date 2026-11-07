"""
Document Text Extractor (PDF / DOCX / PPTX / TXT) and Speaker Defense Speech (.docx) Builder.
Works with zero extra mandatory dependencies using standard library zipfile, xml, zlib, and python-pptx.
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

from app.core.types import PresentationData

logger = logging.getLogger(__name__)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extracts all text paragraphs and table cells from a .docx file using pure Python zipfile + XML.
    Requires zero external packages.
    """
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
    """Extracts text from an existing .pptx file using python-pptx."""
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
    """
    Fallback pure-Python PDF text stream extractor using zlib and regex.
    """
    extracted_chunks: List[str] = []
    try:
        # Find all stream ... endstream blocks
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

            # Look for UTF-16BE hex strings <FEFF...> or literal strings (...)
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

            # Literal strings inside parentheses
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
    """
    Extracts text from a PDF file using available libraries (pypdf, pypdfium2, fitz),
    pdftotext CLI, or pure-Python stream decompression.
    """
    # 1. Try pypdf / PyPDF2
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

    # 2. Try pypdfium2
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

    # 3. Try pdftotext CLI if available
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

    # 4. Pure-Python stream extractor
    return _extract_pdf_pure_python(file_bytes)


def extract_text_from_uploaded_file(filename: str, file_bytes: bytes) -> Tuple[str, str]:
    """
    Detects file extension (.docx, .pdf, .pptx, .txt, .md), extracts text,
    and returns (clean_title_guess, extracted_text).
    """
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

    # Clean whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return base_title, text


def generate_speaker_defense_text(presentation: PresentationData) -> str:
    """
    Generates a complete, natural Speaker Defense Script (Қорғау сөзі / Шпаргалка)
    in Kazakh for every slide of the presentation.
    """
    lines: List[str] = []
    lines.append(f"🎤 ПРЕЗЕНТАЦИЯНЫ ҚОРҒАУ СӨЗІ (ШПАРГАЛКА)")
    lines.append(f"📌 Тақырып: «{presentation.topic}»")
    lines.append(f"📄 Слайд саны: {len(presentation.slides)} бет")
    lines.append("━" * 38)
    lines.append("")

    total = len(presentation.slides)
    for idx, slide in enumerate(presentation.slides):
        num = idx + 1
        lines.append(f"🔹 {num}-СЛАЙД: {slide.title}")

        if idx == 0:
            lines.append("🗣 Сөйлеу мәтіні:")
            lines.append(
                f"«Құрметті комиссия мүшелері, оқытушылар және қатысушылар! "
                f"Назарларыңызға «{presentation.topic}» тақырыбында дайындалған "
                f"ғылыми-тәжірибелік презентацияны ұсынамын. {slide.content}»"
            )
        elif idx == total - 1:
            lines.append("🗣 Қорытынды сөз:")
            lines.append(
                f"«Соңғы слайдта зерттеудің қорытынды тұжырымдары көрсетілген. {slide.content} "
                + (" ".join(slide.key_points[:2]) if slide.key_points else "")
                + " Назар қойып тыңдағандарыңызға көп рақмет! Сұрақтарыңыз болса, жауап беруге дайынмын.»"
            )
        else:
            lines.append("🗣 Сөйлеу мәтіні:")
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
                speech_parts.append("Негізгі көрсеткіштерге назар аударсақ: " + ", ".join(stat_strs) + ".")
            elif slide.timeline:
                tl_strs = [f"{t.title} ({t.desc})" for t in slide.timeline[:3]]
                speech_parts.append("Даму кезеңдері ретімен: " + "; ".join(tl_strs) + ".")
            elif slide.comparison:
                a_name = slide.comparison.entityA.name
                b_name = slide.comparison.entityB.name
                a_pts = ", ".join(slide.comparison.entityA.points[:2])
                b_pts = ", ".join(slide.comparison.entityB.points[:2])
                speech_parts.append(f"Салыстырмалы түрде қарасақ, {a_name} бойынша: {a_pts}. Ал {b_name} бойынша: {b_pts}.")
            elif slide.key_points:
                speech_parts.append("Басты дәйектер ретінде мыналарды атап өтуге болады: " + " ".join(slide.key_points[:3]))

            speech_parts[-1] = speech_parts[-1].rstrip(".") + ".»"
            lines.append(" ".join(speech_parts))

        lines.append("")

    return "\n".join(lines)


def build_defense_speech_docx(presentation: PresentationData) -> bytes:
    """
    Builds a clean, formatted Microsoft Word (.docx) document containing the full
    Speaker Defense Script (Қорғау сөзі) using pure Python zipfile + WordprocessingML.
    """
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
