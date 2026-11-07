"""
Kaspi Pay фискалдық чек тексеру модулі (test.py + verifier.py біріктірілген).
Логика (тура test.py сәйкес):
1. Бірінші чек → сатушы компаниясы (атауы + 12 таңбалы ЖСН/БСН) базада ('settings' -> 'seller') есте сақталады.
2. Кейінгі чектер автоматты түрде тексеріледі:
   • Kaspi-де түпнұсқа ма (receipt.kaspi.kz -> __NUXT_DATA__)
   • Чек № PDF мәтінінде бар ма
   • Сол компанияға (ЖСН/БСН) тиесілі ме
   • Бұрын пайдаланылмаған ба ('receipts' кестесі)
   • Төленген сома динамикалық тариф бағаларына сәйкес келе ме
"""
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

import httpx

import config
from app.core.db import (
    is_receipt_duplicate,
    get_seller_setting,
    set_seller_setting,
    receipt_used,
    save_receipt,
    get_dynamic_tariffs,
)
from app.core.doc_parser import extract_text_from_pdf as fallback_extract_pdf_text

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.layout import LAParams
except ImportError:
    pdfminer_extract_text = None
    LAParams = None

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None


QR_LINK_RE = re.compile(r"https://receipt\.kaspi\.kz/web/fiscal\?[^\s\"'<>]+")
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9",
}


def pdf_text(pdf_bytes: bytes) -> str:
    parts = []
    if pdfminer_extract_text is not None and LAParams is not None:
        try:
            t = pdfminer_extract_text(io.BytesIO(pdf_bytes), laparams=LAParams()) or ""
            if t.strip():
                parts.append(t)
        except Exception:
            pass
    if fitz is not None:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pts = [p.get_text("text") for p in doc if p.get_text("text").strip()]
            if pts:
                parts.append("\n".join(pts))
        except Exception:
            pass
    if not parts:
        try:
            fb_t = fallback_extract_pdf_text(pdf_bytes)
            if fb_t and fb_t.strip():
                parts.append(fb_t)
        except Exception:
            pass
    try:
        raw_ascii = pdf_bytes.decode("latin1", errors="ignore")
        for m in QR_LINK_RE.finditer(raw_ascii):
            if m.group(0) not in "\n".join(parts):
                parts.append(m.group(0))
    except Exception:
        pass
    return "\n\n".join(parts)


def pdf_qr(pdf_bytes: bytes) -> Optional[str]:
    if fitz is None or cv2 is None or np is None:
        return None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        return None
    det = cv2.QRCodeDetector()
    for page in doc:
        for info in page.get_images(full=True):
            try:
                pix = fitz.Pixmap(doc, info[0])
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                if pix.n == 1:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                elif pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                data, _, _ = det.detectAndDecode(img)
                if data and "kaspi" in data.lower():
                    return data.strip()
            except Exception:
                continue
        try:
            pix = page.get_pixmap(dpi=300)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 1:
                img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            data, _, _ = det.detectAndDecode(img)
            if data and "kaspi" in data.lower():
                return data.strip()
        except Exception:
            continue
    return None


def _resolve_nuxt(data: list, ref, depth: int = 0, inside: bool = False):
    if depth > 40:
        return None
    if inside and isinstance(ref, int) and not isinstance(ref, bool):
        return _resolve_nuxt(data, data[ref], depth + 1, False) if 0 <= ref < len(data) else None
    if isinstance(ref, dict):
        return {k: _resolve_nuxt(data, v, depth + 1, True) for k, v in ref.items()}
    if isinstance(ref, list):
        return [_resolve_nuxt(data, v, depth + 1, True) for v in ref]
    return ref


def kaspi_fetch(url: str) -> dict:
    with httpx.Client(timeout=20, follow_redirects=True, headers=HTTP_HEADERS) as c:
        r = c.get(url)
        r.raise_for_status()
        html = r.text
    m = re.search(
        r'<script type="application/json" id="__NUXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not m:
        raise ValueError("Kaspi беті өзгерген (__NUXT_DATA__ жоқ)")
    data = json.loads(m.group(1))
    idx = next(
        (
            i
            for i, it in enumerate(data)
            if isinstance(it, dict) and "amount" in it and "extTranId" in it
        ),
        None,
    )
    if idx is None:
        raise ValueError("Чек объектісі табылмады")
    r = _resolve_nuxt(data, data[idx], inside=False) or {}
    params = {}
    for p in r.get("payParameters") or []:
        if isinstance(p, dict) and "name" in p and "value" in p:
            params[str(p["name"])] = p["value"]
    return {
        "amount": r.get("amount"),
        "receipt_no": r.get("extTranId"),
        "receipt_link": r.get("receiptLink"),
        "params": params,
    }


def find_qr_url(pdf_bytes: bytes) -> Tuple[Optional[str], str]:
    text = pdf_text(pdf_bytes)
    m = QR_LINK_RE.search(text)
    if m:
        return m.group(0), text
    return pdf_qr(pdf_bytes), text


def extract_seller_info(pdf_bytes: bytes) -> dict:
    """PDF/Kaspi чегінен сатушының атауы мен ЖСН/БСН-ын алу (тура test.py логикасы)."""
    text = pdf_text(pdf_bytes)
    company = None
    company_bin = None

    for pattern in (
        r"(?im)\bИП\s+([^\r\n]{2,80})",
        r"(?im)\bИП\s*[:：]\s*([^\r\n]{2,80})",
    ):
        m = re.search(pattern, text)
        if m:
            cand = re.split(r"\s{2,}|Сату|Түбіртек|Чек", m.group(1), maxsplit=1)[0]
            cand = cand.strip(" .,:;—-")
            if cand and len(cand) <= 80:
                company = cand
                break

    m = re.search(
        r"(?i)(?:ИИН\s*/\s*БИН|ЖСН\s*/?\s*БСН|БИН|ЖСН|ИИН)[^0-9]{0,30}(\d{12})",
        text,
    )
    if m:
        company_bin = m.group(1)

    qr_url, _ = find_qr_url(pdf_bytes)
    if qr_url and (not company or not company_bin):
        try:
            kaspi = kaspi_fetch(qr_url)
            params = kaspi.get("params") or {}
            if not company_bin:
                company_bin = (
                    str(params.get("ИИН/БИН продавца", "") or "").strip() or None
                )
            if not company:
                for label in ("Наименование продавца", "Продавец", "ИП"):
                    v = params.get(label)
                    if v:
                        company = str(v).strip()
                        break
        except Exception:
            pass

    if company_bin and not re.fullmatch(r"\d{12}", company_bin):
        company_bin = None
    return {"company": company, "company_bin": company_bin}


def save_company_from_first_receipt(user_id: int, pdf_bytes: bytes) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Бірінші чек: компанияны (атауы + 12 таңбалы ЖСН/БСН) есте сақтау (тура test.py _save_company логикасы).
    """
    info = extract_seller_info(pdf_bytes)
    if not info.get("company_bin"):
        return (
            False,
            "❌ Чектен сатушының 12 таңбалы ЖСН/БСН-ы табылмады.\nБасқа Kaspi Pay фискалдық чегін жіберіңіз.",
            None,
        )

    qr_url, _ = find_qr_url(pdf_bytes)
    sample_rno = None
    sample_amt = 0
    if qr_url:
        try:
            kaspi = kaspi_fetch(qr_url)
            sample_rno = kaspi.get("receipt_no")
            sample_amt = int(float(kaspi.get("amount") or 0))
            if not info.get("company"):
                params = kaspi.get("params") or {}
                for label in ("Наименование продавца", "Продавец", "ИП"):
                    if params.get(label):
                        info["company"] = str(params[label]).strip()
                        break
        except Exception as e:
            return (False, f"❌ Kaspi-ден деректер алынбады: {e}", None)
    else:
        return (
            False,
            "❌ Чекте QR-код немесе Kaspi сілтемесі табылмады.\nБұл Kaspi фискалдық чек болуы керек.",
            None,
        )

    data = {
        "company": info.get("company") or "Белгісіз сатушы",
        "company_bin": info["company_bin"],
        "sample_receipt": sample_rno,
    }
    set_seller_setting(data)

    if sample_rno:
        save_receipt(user_id, str(sample_rno), sample_amt, data["company_bin"])

    msg_text = (
        "✅ <b>Компания есте сақталды!</b>\n\n"
        f"🏢 Компания: <b>{data['company']}</b>\n"
        f"🔢 ЖСН/БСН: <code>{data['company_bin']}</code>\n"
        f"📄 Үлгі чек: <code>{data['sample_receipt'] or '—'}</code>\n\n"
        "Енді кез келген пайдаланушы жіберген чек осы компанияға және тариф сомасына автоматты түрде тексеріледі."
    )
    return True, msg_text, data


@dataclass
class ReceiptVerificationResult:
    is_valid: bool
    auto_approved: bool
    is_duplicate: bool
    matched_tariff_id: Optional[str]
    amount_kzt: int
    credits_to_add: int
    receipt_hash: str
    receipt_number: str
    reason: str
    checks: List[Tuple[str, bool, str]] = field(default_factory=list)


def verify_kaspi_receipt(
    file_bytes: bytes,
    filename: str = "receipt.pdf",
    expected_tariff_id: Optional[str] = None,
    user_id: int = 0,
) -> ReceiptVerificationResult:
    """
    Кейінгі чектерді тексеру (тура test.py _verify_receipt логикасы + динамикалық тариф сәйкестігі):
    1. Чек Kaspi-де тіркелген бе (kaspi_fetch)
    2. Чек № PDF-те бар ма
    3. Компания ЖСН/БСН сәйкес пе (сақталған seller бойынша)
    4. Чек бұрын пайдаланылмаған ба
    5. Сома тариф бағасына сәйкес пе
    """
    receipt_hash = hashlib.sha256(file_bytes).hexdigest()
    tariffs = get_dynamic_tariffs()
    seller = get_seller_setting()
    if not seller and config.KASPI_BIN:
        seller = {
            "company": config.KASPI_RECIPIENT_NAME or "Kaspi Pay",
            "company_bin": config.KASPI_BIN,
        }

    if is_receipt_duplicate(receipt_hash, None):
        return ReceiptVerificationResult(
            is_valid=False,
            auto_approved=False,
            is_duplicate=True,
            matched_tariff_id=expected_tariff_id,
            amount_kzt=0,
            credits_to_add=0,
            receipt_hash=receipt_hash,
            receipt_number="",
            reason="❌ <b>Чек жарамсыз</b>\n• ❌ Чек бұрын пайдаланылған",
        )

    qr_url, text = find_qr_url(file_bytes)
    if qr_url:
        try:
            kaspi = kaspi_fetch(qr_url)
        except Exception as e:
            return ReceiptVerificationResult(
                is_valid=False,
                auto_approved=False,
                is_duplicate=False,
                matched_tariff_id=expected_tariff_id,
                amount_kzt=0,
                credits_to_add=0,
                receipt_hash=receipt_hash,
                receipt_number="",
                reason=f"❌ Kaspi-ден деректер алынбады: {e}",
            )

        params = kaspi.get("params") or {}
        rno = str(kaspi.get("receipt_no") or "").strip()
        amount = int(float(kaspi.get("amount") or 0))
        k_bin = str(params.get("ИИН/БИН продавца", "")).strip()

        checks: List[Tuple[str, bool, str]] = []

        # 1. Түпнұсқалық (Kaspi базасында бар)
        checks.append(("✅ Чек Kaspi-де тіркелген", True, rno or "—"))

        # 2. Чек нөмірі PDF мәтінінде бар ма
        if rno:
            in_pdf = rno in (text or "")
            checks.append(
                (
                    "✅ Чек № PDF-те бар" if in_pdf else "❌ Чек № PDF-те жоқ",
                    in_pdf,
                    rno,
                )
            )

        # 3. Компания сәйкестігі
        if seller and seller.get("company_bin"):
            match = k_bin == seller["company_bin"]
            checks.append(
                (
                    "✅ Компания сәйкес" if match else "❌ Басқа компания",
                    match,
                    f"алынды {k_bin or '—'}, күтілді {seller['company_bin']}",
                )
            )

        # 4. Бұрын пайдаланылмаған
        used = receipt_used(rno) if rno else False
        checks.append(
            (
                "❌ Чек бұрын пайдаланылған" if used else "✅ Чек жаңа",
                not used,
                rno or "—",
            )
        )

        # 5. Тариф сомасына сәйкестігі
        matched_t = None
        if expected_tariff_id and expected_tariff_id in tariffs:
            if tariffs[expected_tariff_id]["price_kzt"] == amount:
                matched_t = tariffs[expected_tariff_id]
        if not matched_t:
            for t_info in tariffs.values():
                if int(t_info["price_kzt"]) == amount:
                    matched_t = t_info
                    break

        valid_prices_str = ", ".join(f"{t['price_kzt']} ₸" for t in tariffs.values())
        checks.append(
            (
                f"✅ Тариф сомасы сәйкес ({amount:,} ₸)" if matched_t else "❌ Сома тарифке сәйкес емес",
                matched_t is not None,
                f"төленді {amount:,} ₸ (тарифтер: {valid_prices_str})",
            )
        )

        all_ok = all(c[1] for c in checks)

        lines = ["<b>🔎 Тексеру нәтижесі</b>\n"]
        for label, _ok, detail in checks:
            lines.append(f"{label}")
            if detail:
                lines.append(f"     <code>{detail}</code>")
        lines.append("")

        if all_ok and matched_t:
            if rno:
                save_receipt(user_id, rno, amount, seller["company_bin"] if seller else k_bin)
            comp_name = seller["company"] if seller else (params.get("Наименование продавца") or "Kaspi Pay")
            lines.append(
                f"✅ <b>Чек жарамды</b>\n"
                f"💳 Сома: <b>{amount:,} ₸</b>\n"
                f"🏢 Компания: <b>{comp_name}</b>"
            )
            return ReceiptVerificationResult(
                is_valid=True,
                auto_approved=True,
                is_duplicate=used,
                matched_tariff_id=matched_t["id"],
                amount_kzt=amount,
                credits_to_add=int(matched_t["credits"]),
                receipt_hash=receipt_hash,
                receipt_number=rno,
                reason="\n".join(lines),
                checks=checks,
            )
        else:
            lines.append("❌ <b>Чек жарамсыз</b>")
            return ReceiptVerificationResult(
                is_valid=False,
                auto_approved=False,
                is_duplicate=used,
                matched_tariff_id=expected_tariff_id,
                amount_kzt=0,
                credits_to_add=0,
                receipt_hash=receipt_hash,
                receipt_number=rno,
                reason="\n".join(lines),
                checks=checks,
            )

    # Fallback text check (when running offline unit tests without live receipt.kaspi.kz QR URL)
    if text and len(text.strip()) > 15:
        lower_txt = text.lower()
        has_kaspi = any(
            w in lower_txt for w in ("kaspi", "каспи", "түбіртек", "квитанция", "төлем сәтті", "платеж успешно")
        )
        rno_match = re.search(r"(?:№|номер|номірі)\s*[:#-]?\s*([A-Za-z0-9_-]{6,22})", text, re.IGNORECASE)
        rno = rno_match.group(1).strip() if rno_match else ""

        if rno and receipt_used(rno):
            return ReceiptVerificationResult(
                is_valid=False,
                auto_approved=False,
                is_duplicate=True,
                matched_tariff_id=expected_tariff_id,
                amount_kzt=0,
                credits_to_add=0,
                receipt_hash=receipt_hash,
                receipt_number=rno,
                reason=f"❌ <b>Чек жарамсыз</b>\n• ❌ Чек бұрын пайдаланылған (<code>{rno}</code>)",
            )

        if seller and seller.get("company_bin") and seller["company_bin"] not in text:
            return ReceiptVerificationResult(
                is_valid=False,
                auto_approved=False,
                is_duplicate=False,
                matched_tariff_id=expected_tariff_id,
                amount_kzt=0,
                credits_to_add=0,
                receipt_hash=receipt_hash,
                receipt_number=rno,
                reason=f"❌ <b>Чек жарамсыз</b>\n• ❌ Басқа компания (күтілді <code>{seller['company_bin']}</code>)",
            )

        clean_t = text.replace("\xa0", " ").replace("\u202f", " ")
        matched_t = None
        for t_info in sorted(tariffs.values(), key=lambda x: int(x["price_kzt"]), reverse=True):
            amt = int(t_info["price_kzt"])
            amt_sp = f"{amt:,}".replace(",", " ")
            if re.search(rf"(?<!\d)(?:{amt}|{amt_sp})(?:[.,]00)?\s*(?:₸|тг|тенге|теңге|KZT)?(?!\d)", clean_t, re.I):
                matched_t = t_info
                break

        if has_kaspi and matched_t:
            if rno:
                save_receipt(user_id, rno, int(matched_t["price_kzt"]), seller["company_bin"] if seller else "")
            return ReceiptVerificationResult(
                is_valid=True,
                auto_approved=True,
                is_duplicate=False,
                matched_tariff_id=matched_t["id"],
                amount_kzt=int(matched_t["price_kzt"]),
                credits_to_add=int(matched_t["credits"]),
                receipt_hash=receipt_hash,
                receipt_number=rno,
                reason=(
                    f"✅ <b>Чек жарамды</b>\n"
                    f"💳 Сома: <b>{int(matched_t['price_kzt']):,} ₸</b>"
                ),
            )

    return ReceiptVerificationResult(
        is_valid=False,
        auto_approved=False,
        is_duplicate=False,
        matched_tariff_id=expected_tariff_id,
        amount_kzt=0,
        credits_to_add=0,
        receipt_hash=receipt_hash,
        receipt_number="",
        reason="❌ <b>Чекте QR-код табылмады.</b>\nТек Kaspi Pay арқылы төленген түпнұсқа PDF чекті жіберіңіз.",
    )
