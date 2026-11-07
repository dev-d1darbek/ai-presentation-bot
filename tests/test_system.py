"""
Automated Test Suite for AI Presentation Bot (Full Commercial Edition + test.py Integration).
Tests:
1. 30 Themes Registry & Keyword Detection
2. Robust JSON Parser & Salvage
3. Minimalist PPTX & Zero-Dependency Pillow PDF Engines
4. Document-to-Slide (.DOCX) & Speaker Defense Speech (.DOCX)
5. Smart Cross-User Cache & Saved User Projects
6. Dynamic Tariff Price Editor, Kaspi Pay URL Editor & First-Receipt Seller Memorization (test.py logic)
7. Referrals, 2,000₸ Partner Withdrawal Flow & Admin Panel
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
from app.core.themes import THEMES_REGISTRY, detect_best_theme_for_topic
from app.core.db import (
    DB_PATH,
    init_db,
    log_user,
    get_user_profile,
    find_user_by_query,
    get_user_credits,
    consume_user_credit,
    add_user_credits,
    get_seller_setting,
    set_seller_setting,
    reset_seller_setting,
    get_kaspi_pay_url,
    set_kaspi_pay_url,
    get_dynamic_tariffs,
    update_tariff_setting,
    create_payment_record,
    approve_payment,
    create_withdrawal_request,
    approve_withdrawal_request,
    get_pending_withdrawals,
    get_user_projects,
)
from app.core.verifier import verify_kaspi_receipt, _resolve_nuxt, extract_seller_info
from app.core.doc_parser import (
    extract_text_from_uploaded_file,
    generate_speaker_defense_text,
    build_defense_speech_docx,
)
from app.ai.parser import robust_parse_json
from app.ai.fallback import generate_intelligent_fallback
from app.pptx_generator.engine import build_pptx_deck
from app.pptx_generator.pdf_engine import build_pdf_deck
from app.bot.service import (
    generate_deck_for_session,
    load_saved_project_for_session,
    format_user_admin_card,
    format_admin_dashboard_text,
)
from app.bot.session import get_telegram_session


def test_themes_registry():
    print("1. Testing Themes Registry...")
    assert len(THEMES_REGISTRY) == 30
    assert detect_best_theme_for_topic("Жасанды интеллект және IT").id == "futuristic_tech"
    assert detect_best_theme_for_topic("Қазақ хандығының тарихы").id == "cinematic_history"
    print("   ✓ Themes registry passed!")


def test_json_parser():
    print("2. Testing Robust JSON Parser...")
    normal = '{"slides": [{"slide_number": 1, "title": "Test"}]}'
    assert robust_parse_json(normal) is not None

    truncated = '{"title_presentation": "AI", "slides": [{"slide_number": 1, "title": "Intro"}, {"slide_number": 2, "title": "Unfinished"'
    salvaged = robust_parse_json(truncated)
    assert salvaged is not None
    assert len(salvaged["slides"]) == 1
    print("   ✓ JSON parser passed!")


def test_pptx_and_pdf_engines():
    print("3. Testing Minimalist PPTX & Zero-Dependency PDF Engines...")
    pres = generate_intelligent_fallback("Жасанды интеллект дамуы", 6)
    deck_bytes = build_pptx_deck(pres)
    assert len(deck_bytes) > 20000

    pdf_bytes = build_pdf_deck(pres, pptx_bytes=None)
    assert len(pdf_bytes) > 20000
    print(f"   ✓ PPTX ({len(deck_bytes)} bytes) & Pillow PDF ({len(pdf_bytes)} bytes) passed!")


def test_document_to_slide_and_defense_speech():
    print("4. Testing Document-to-Slide (.DOCX) & Speaker Defense Speech (.DOCX)...")
    pres = generate_intelligent_fallback("Қазақстан тарихы", 8)
    speech_text = generate_speaker_defense_text(pres)
    assert "Құрметті комиссия мүшелері" in speech_text
    assert "8-СЛАЙД" in speech_text

    docx_bytes = build_defense_speech_docx(pres)
    assert len(docx_bytes) > 1000

    doc_title, extracted = extract_text_from_uploaded_file("Қазақстан_тарихы_мақала.docx", docx_bytes)
    assert "Құрметті комиссия мүшелері" in extracted
    doc_pres = generate_intelligent_fallback(doc_title, 6, document_text=extracted)
    assert len(doc_pres.slides) == 6
    print("   ✓ Document extraction (.DOCX) & Speaker Defense Speech (.DOCX) passed!")


async def test_smart_cache_and_saved_projects():
    print("5. Testing Smart Cross-User Cache & Saved User Projects...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()

    user1_id = 10001
    user2_id = 20002
    log_user(user1_id, "user1", "Бірінші")
    log_user(user2_id, "user2", "Екінші")

    s1 = get_telegram_session(user1_id)
    s1.pendingTopic = "Жасыл экономика негіздері"
    s1.slideCount = 8
    s1.designId = "swiss_minimalism"

    pptx1, fname1, pres1, from_cache1 = await generate_deck_for_session(s1, user_id=user1_id, slide_count=8)
    assert len(pptx1) > 20000
    assert pres1.design_id == "swiss_minimalism"

    s2 = get_telegram_session(user2_id)
    s2.pendingTopic = "Жасыл экономика негіздері!"
    s2.slideCount = 8
    s2.designId = "apple_keynote"

    pptx2, fname2, pres2, from_cache2 = await generate_deck_for_session(s2, user_id=user2_id, slide_count=8)
    assert from_cache2 is True, "Expected Smart Cross-User Cache HIT for user2!"
    assert pres2.design_id == "apple_keynote", "Expected user2's chosen design to be applied!"

    u2_projects, total2 = get_user_projects(user2_id)
    assert total2 >= 1

    loaded = load_saved_project_for_session(s2, u2_projects[0]["id"], user_id=user2_id)
    assert loaded is not None
    print("   ✓ Smart Cross-User Cache & Saved User Projects passed!")


def test_dynamic_prices_seller_memorization_and_withdrawals():
    print("6. Testing Seller Auto-Memorization (test.py), Dynamic Prices, Kaspi Verifier & Withdrawals...")
    # 1. Test Nuxt resolver & Seller Info extractor from test.py
    sample_nuxt = [{"amount": 1, "extTranId": 2}, 2000, "QR123456789"]
    resolved = _resolve_nuxt(sample_nuxt, sample_nuxt[0], inside=False)
    assert resolved["amount"] == 2000
    assert resolved["extTranId"] == "QR123456789"

    sample_seller_pdf = (
        b"%PDF-1.4\n1 0 obj\n<<>>\nstream\n"
        + ("(ИП ДИДАРБЕК ИИН/БИН: 010203405060 Квитанция №QR555666777)").encode("utf-8")
        + b"\nendstream\nendobj\n"
    )
    s_info = extract_seller_info(sample_seller_pdf)
    assert s_info["company_bin"] == "010203405060"
    assert "ДИДАРБЕК" in (s_info["company"] or "")

    # Save memorized seller (as when Admin sends 1st PDF receipt)
    set_seller_setting({
        "company": s_info["company"],
        "company_bin": s_info["company_bin"],
        "sample_receipt": "QR555666777",
    })
    assert get_seller_setting()["company_bin"] == "010203405060"

    # 2. Test Dynamic Kaspi Pay URL & Dynamic Tariff Price Editing in Bot
    set_kaspi_pay_url("https://pay.kaspi.kz/pay/NEW_ADMIN_LINK")
    assert get_kaspi_pay_url() == "https://pay.kaspi.kz/pay/NEW_ADMIN_LINK"

    # Admin changes 'single' tariff price from 200 ₸ to 350 ₸
    update_tariff_setting("single", price_kzt=350, credits=2)
    dyn_tariffs = get_dynamic_tariffs()
    assert dyn_tariffs["single"]["price_kzt"] == 350
    assert dyn_tariffs["single"]["credits"] == 2

    # 3. Verify receipt matching memorized seller BIN (010203405060) and dynamic price (350 ₸)
    valid_custom_pdf = (
        b"%PDF-1.4\n1 0 obj\n<<>>\nstream\n"
        + ("(Kaspi Bank Төлем сәтті өтті ИИН/БИН: 010203405060 Квитанция №QR777888999 Сомасы 350 ₸)").encode("utf-8")
        + b"\nendstream\nendobj\n"
    )
    v_custom = verify_kaspi_receipt(valid_custom_pdf, "receipt.pdf", user_id=10001)
    assert v_custom.is_valid is True
    assert v_custom.amount_kzt == 350
    assert v_custom.credits_to_add == 2

    # Receipt from a DIFFERENT seller BIN (999999999999) MUST be rejected!
    wrong_bin_pdf = (
        b"%PDF-1.4\n1 0 obj\n<<>>\nstream\n"
        + ("(Kaspi Bank Төлем сәтті өтті ИИН/БИН: 999999999999 Квитанция №QR111222333 Сомасы 350 ₸)").encode("utf-8")
        + b"\nendstream\nendobj\n"
    )
    v_wrong_bin = verify_kaspi_receipt(wrong_bin_pdf, "receipt.pdf", user_id=10001)
    assert v_wrong_bin.is_valid is False

    # Reset seller setting (as when Admin clicks /reset)
    reset_seller_setting()
    assert get_seller_setting() is None

    # 4. Test Referrals & 2,000 ₸ Partner Withdrawal Flow
    student_id = 777000
    reg = log_user(student_id, "student_leader", "Айдос")
    assert reg["is_new"] is True
    assert get_user_credits(student_id) == 1

    for i in range(1, 21):
        friend_id = 800000 + i
        log_user(friend_id, f"friend_{i}", f"Дос {i}", referrer_id=student_id)

    f1_id = 800001
    f2_id = 800002
    pay1_id = create_payment_record(f1_id, "vip", 5000, 40, receipt_hash="h1", receipt_number="QR9988776655")
    approve_payment(pay1_id)
    pay2_id = create_payment_record(f2_id, "vip", 5000, 40, receipt_hash="h2", receipt_number="QR1122334455")
    app2 = approve_payment(pay2_id)
    assert app2["partner_reward_kzt"] == 2000

    w_id, err_ok = create_withdrawal_request(student_id, 2000, "+7 777 111 22 33 Айдос С.")
    assert w_id is not None and err_ok == ""

    w_approved = approve_withdrawal_request(w_id)
    assert w_approved is not None
    assert w_approved["new_balance"] == 0

    print("   ✓ Seller Auto-Memorization, Dynamic Tariff Prices, Kaspi Verifier & Partner Withdrawals passed!")


if __name__ == "__main__":
    test_themes_registry()
    test_json_parser()
    test_pptx_and_pdf_engines()
    test_document_to_slide_and_defense_speech()
    asyncio.run(test_smart_cache_and_saved_projects())
    test_dynamic_prices_seller_memorization_and_withdrawals()
    print("\n🎉 ALL COMMERCIAL, KASPI AUTO-SETUP, DYNAMIC PRICE & SYSTEM TESTS PASSED SUCCESSFULLY!")
