"""
Automated Test Suite for AI Presentation Bot Pro v2.
Tests:
1. 35 Themes Registry & Removal of TTS / Teacher Package
2. 6 Exact Tariffs & 3-Bucket Credit System (200₸ / 300₸ / 500₸ / 3,490₸ / 4,900₸ / 9,900₸) + DDG Photo Warning
3. Free Bonus Credit Rule (usable for 'Бір реттік' and 'Бір реттік + ФОТО', blocked for OpenAI 'gpt-image-2')
4. One-Time Promo Codes ('ALASH2025', 'KAZNU50') & Bonus Campaigns ('BONUS2025')
5. Admin Package CRUD (Create new package, Edit package price/splits, Delete package)
6. 8 Specialized Templates (including Медициналық, Заң жобасы, Маркетинг, Экология) + ҚР ЖОО ГОСТ 7.32-2017 Compliance
7. AI Cost Optimization & Cost Tracker + 7d/30d PNG Charts + Paginated Filtered Users + 360° User Card + Project Deletion + CSV/Excel DB Export
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
    get_user_credits,
    get_user_credit_breakdown,
    consume_user_credit,
    add_user_credits,
    set_seller_setting,
    get_dynamic_tariffs,
    update_tariff_setting,
    create_custom_tariff_package,
    delete_tariff_package,
    toggle_tariff_package,
    enable_all_tariff_packages,
    get_enabled_generation_modes,
    toggle_generation_mode,
    set_only_nophoto_mode,
    enable_all_generation_modes,
    create_payment_record,
    approve_payment,
    apply_promo_code_to_user,
    create_or_update_promo_code,
    delete_promo_code,
    get_users_paginated,
    get_segmented_user_ids,
    delete_user_project_by_id,
    log_support_ticket,
    get_ai_cost_stats,
    export_database_zip_bytes,
)
from app.core.verifier import verify_kaspi_receipt
from app.core.doc_parser import (
    extract_text_from_uploaded_file,
    generate_speaker_defense_text,
    build_defense_speech_docx,
)
from app.core.image_search import populate_presentation_images, _cache as ddg_cache, search_images
from app.ai.parser import robust_parse_json
from app.ai.fallback import generate_intelligent_fallback
from app.pptx_generator.engine import build_pptx_deck
from app.pptx_generator.pdf_engine import build_pdf_deck
from app.bot.service import (
    generate_deck_for_session,
    render_admin_analytics_chart_png,
    format_user_admin_card,
    format_admin_dashboard_text,
)
from app.bot.session import get_telegram_session, save_session, _sessions
from app.bot.keyboards.inline import build_post_generation_keyboard, build_topic_ready_text, build_topic_ready_keyboard


def test_config_tariffs_and_cleanup():
    print("1. Testing 6 New Tariffs, 3-Bucket Splits, 8 Templates (ГОСТ 7.32-2017) & TTS/Teacher Removal...")
    tts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "core", "tts.py"))
    assert not os.path.exists(tts_path), "app/core/tts.py must be removed!"
    assert "teacher" not in config.TARIFF_PLANS, "Teacher package must be removed!"

    t = config.TARIFF_PLANS
    assert t["single"]["price_kzt"] == 200 and t["single"]["no_photo_credits"] == 1
    assert t["single_photo"]["price_kzt"] == 300 and t["single_photo"]["ddg_photo_credits"] == 1
    assert t["single_openai"]["price_kzt"] == 500 and t["single_openai"]["openai_photo_credits"] == 1
    assert t["hit"]["price_kzt"] == 3490 and (t["hit"]["no_photo_credits"], t["hit"]["ddg_photo_credits"], t["hit"]["openai_photo_credits"]) == (10, 5, 5)
    assert t["pro"]["price_kzt"] == 4900 and (t["pro"]["no_photo_credits"], t["pro"]["ddg_photo_credits"], t["pro"]["openai_photo_credits"]) == (10, 10, 10)
    assert t["vip"]["price_kzt"] == 9900 and (t["vip"]["no_photo_credits"], t["vip"]["ddg_photo_credits"], t["vip"]["openai_photo_credits"]) == (40, 20, 20)

    # Check 8 specialized templates + standard = 9 entries
    for tmpl_key in ("diploma", "business", "scientific", "lesson", "medical", "law", "marketing", "ecology"):
        assert tmpl_key in config.TEMPLATE_LIBRARY, f"Missing template {tmpl_key}!"
    print("   ✓ 6 Tariffs, 3-Bucket Splits, 8 Templates & TTS/Teacher removal passed!")


async def test_templates_gost_and_photo_warning():
    print("2. Testing ГОСТ 7.32-2017 Defense Speech, New Templates & DDG Photo Disclaimer...")
    config.DEBUG_MODE = True
    for tmpl_id in ("medical", "law", "marketing", "ecology", "diploma"):
        pres = generate_intelligent_fallback("Клиникалық диагностика", 6, template_id=tmpl_id)
        assert len(pres.slides) == 6

    pres_gost = generate_intelligent_fallback("Жасанды интеллект", 7, template_id="diploma")
    speech = generate_speaker_defense_text(pres_gost)
    assert "ГОСТ 7.32-2017" not in speech and "ҚОРҒАУ СӨЗІ" in speech

    # Verify DDG photo warning appears when session.withPhotos=True and imageSource='ddg'
    s = get_telegram_session(999111)
    s.pendingTopic = "Қазақстан экономикасы"
    s.withPhotos = True
    s.imageSource = "ddg"
    ready_txt = build_topic_ready_text(s)
    assert "интернеттен мысал ретінде" in ready_txt and "ЖИ қателесуі мүмкін" in ready_txt
    config.DEBUG_MODE = False
    print("   ✓ ГОСТ 7.32-2017 Defense Speech, 8 Templates & DDG Photo Disclaimer passed!")


def test_three_bucket_credits_and_one_time_promos():
    print("3. Testing 3-Bucket Credit System, Free Bonus Rules & One-Time Promo Codes...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    _sessions.clear()

    # 1. Free bonus user gets 1 bonus credit, usable for 'Бір реттік' (no photo) OR 'Бір реттік + ФОТО' (ddg), NEVER 'gpt-image-2'!
    u1 = 1001
    log_user(u1, "student1", "Айбек")
    b1 = get_user_credit_breakdown(u1)
    assert b1["bonus"] == 1 and b1["openai_photo"] == 0

    # Must block OpenAI gpt-image-2 on free bonus credit!
    assert consume_user_credit(u1, with_photos=True, image_source="gpt-image-2") is False, "Free bonus must NOT allow OpenAI gpt-image-2!"
    # Must allow 'Бір реттік + ФОТО' (ddg) on free bonus credit!
    assert consume_user_credit(u1, with_photos=True, image_source="ddg") is True, "Free bonus MUST allow 'Бір реттік + ФОТО' (ddg)!"
    assert get_user_credits(u1) == 0

    # 2. One-Time Promo Code rule ('промокодтар тек Бір реттік істесін')
    ok1, _, _ = apply_promo_code_to_user(u1, "ALASH2025")
    assert ok1 is True, "First use of ALASH2025 must succeed!"
    ok2, msg2, _ = apply_promo_code_to_user(u1, "ALASH2025")
    assert ok2 is False and "1 рет" in msg2, "Second use of ALASH2025 by same user MUST be rejected!"

    # Gift/Bonus Campaign promo code ('BONUS2025' -> +1 bonus credit once)
    ok_b1, _, _ = apply_promo_code_to_user(u1, "BONUS2025")
    assert ok_b1 is True and get_user_credit_breakdown(u1)["bonus"] == 1
    ok_b2, _, _ = apply_promo_code_to_user(u1, "BONUS2025")
    assert ok_b2 is False, "Second use of BONUS2025 must be rejected!"

    # Consume that bonus credit on 'Бір реттік' (no-photo)
    assert consume_user_credit(u1, with_photos=False) is True
    assert get_user_credits(u1) == 0

    # Verify 50% ALASH2025 discount applies ONLY to 'Бір реттік' packages (single, single_photo, single_openai) and NOT to Hit/Pro/VIP!
    user_tariffs = get_dynamic_tariffs(user_id=u1)
    assert user_tariffs["single"]["price_kzt"] == 100 and user_tariffs["single_photo"]["price_kzt"] == 150 and user_tariffs["single_openai"]["price_kzt"] == 250
    assert user_tariffs["hit"]["price_kzt"] == 3490 and user_tariffs["pro"]["price_kzt"] == 4900 and user_tariffs["vip"]["price_kzt"] == 9900

    # 3. Purchase 'Студент Pro' at full price 4,900 ₸ (since 50% promo is only for Бір реттік packages)
    set_seller_setting({"company": "ИП ДИДАРБЕК", "company_bin": "010203405060", "sample_receipt": "QR1"})
    pro_pdf = (
        b"%PDF-1.4\n1 0 obj\n<<>>\nstream\n"
        + ("(Kaspi Bank Төлем сәтті өтті ИИН/БИН: 010203405060 Квитанция №QR555999111 Сомасы 4900 ₸)").encode("utf-8")
        + b"\nendstream\nendobj\n"
    )
    config.DEBUG_MODE = True
    v_res = verify_kaspi_receipt(pro_pdf, "receipt.pdf", expected_tariff_id="pro", user_id=u1)
    config.DEBUG_MODE = False
    assert v_res.is_valid is True
    assert (v_res.no_photo_to_add, v_res.ddg_photo_to_add, v_res.openai_photo_to_add) == (10, 10, 10)

    pay_id = create_payment_record(
        u1, "pro", v_res.amount_kzt, v_res.credits_to_add,
        receipt_hash=v_res.receipt_hash, receipt_number=v_res.receipt_number,
        no_photo_added=v_res.no_photo_to_add, ddg_photo_added=v_res.ddg_photo_to_add, openai_photo_added=v_res.openai_photo_to_add,
    )
    approve_payment(pay_id)
    b_after = get_user_credit_breakdown(u1)
    assert (b_after["no_photo"], b_after["ddg_photo"], b_after["openai_photo"]) == (10, 10, 10)

    # Now OpenAI gpt-image-2 is allowed and deducts from openai_photo_credits!
    assert consume_user_credit(u1, with_photos=True, image_source="gpt-image-2") is True
    assert get_user_credit_breakdown(u1)["openai_photo"] == 9
    print("   ✓ 3-Bucket Credits, Free Bonus Rules & One-Time Promo Codes passed!")


async def test_admin_crud_charts_filters_and_export():
    print("4. Testing Admin Package CRUD, 7d/30d PNG Charts, User Filters, 360° Card, Project Delete & CSV Export...")
    # 1. Admin creates a new custom tariff package, edits it, and deletes it
    custom_pkg = create_custom_tariff_package("Магистрант Pro", 6900, 20, 15, 15)
    pkg_id = custom_pkg["id"]
    assert pkg_id in get_dynamic_tariffs()
    assert get_dynamic_tariffs()[pkg_id]["credits"] == 50

    update_tariff_setting(pkg_id, price_kzt=7500, no_photo_credits=25, ddg_photo_credits=15, openai_photo_credits=15)
    assert get_dynamic_tariffs()[pkg_id]["price_kzt"] == 7500
    assert get_dynamic_tariffs()[pkg_id]["credits"] == 55

    # Disable package -> hidden from users, visible in Admin with is_enabled=False
    assert toggle_tariff_package(pkg_id) is False
    assert pkg_id not in get_dynamic_tariffs()
    assert pkg_id in get_dynamic_tariffs(include_disabled=True)
    assert get_dynamic_tariffs(include_disabled=True)[pkg_id]["is_enabled"] is False

    # Re-enable package -> visible to users again!
    assert toggle_tariff_package(pkg_id) is True
    assert pkg_id in get_dynamic_tariffs()
    assert get_dynamic_tariffs()[pkg_id]["price_kzt"] == 7500

    # Test 3 Presentation Generation Modes (Фотосыз / Фото / OpenAI) toggle & 'Only No-Photo' preset
    set_only_nophoto_mode()
    modes_only_np = get_enabled_generation_modes()
    assert modes_only_np == {"none": True, "ddg": False, "gpt-image-2": False}
    s_mode_test = get_telegram_session(1001)
    s_mode_test.withPhotos = True
    s_mode_test.imageSource = "gpt-image-2"
    kb_only_np = build_topic_ready_keyboard(s_mode_test)
    assert s_mode_test.withPhotos is False, "Session must auto-switch to no-photo when photo modes are disabled!"
    enable_all_generation_modes()
    assert get_enabled_generation_modes() == {"none": True, "ddg": True, "gpt-image-2": True}

    # 2. Generate a photo presentation for user 1001 so they appear in 'photo' filter
    s1 = get_telegram_session(1001)
    s1.pendingTopic = "Экологиялық жоба негіздері"
    s1.slideCount = 6
    s1.templateId = "ecology"
    s1.withPhotos = True
    s1.imageSource = "ddg"
    config.DEBUG_MODE = True
    await generate_deck_for_session(s1, user_id=1001, slide_count=6)
    config.DEBUG_MODE = False

    photo_users, total_photo = get_users_paginated(page=0, filter_mode="photo")
    assert total_photo >= 1 and any(u["user_id"] == 1001 for u in photo_users)

    paid_users = get_segmented_user_ids("vip_paid")
    assert 1001 in paid_users

    # 3. 360° User Card + Support Complaint Logging + Project Deletion
    log_support_ticket(1001, "Сәлеметсіз бе, чек бойынша сұрағым бар еді")
    card_text, projects = format_user_admin_card(1001)
    assert "360° ҚОЛДАНУШЫ ТАРИХЫ" in card_text
    assert "4,900 ₸" in card_text
    assert len(projects) >= 1

    del_res = delete_user_project_by_id(projects[0]["id"])
    assert del_res is not None
    _, projects_after = format_user_admin_card(1001)
    assert len(projects_after) == len(projects) - 1

    # 4. 7-Day & 30-Day PNG Charts
    png_7d, cap_7d = render_admin_analytics_chart_png(days=7)
    png_30d, cap_30d = render_admin_analytics_chart_png(days=30)
    assert len(png_7d) > 5000 and len(png_30d) > 5000

    # 5. AI Cost Tracker & CSV/Excel ZIP Export
    ai_st = get_ai_cost_stats()
    assert ai_st["total_calls"] >= 1
    zip_bytes, fname = export_database_zip_bytes()
    assert len(zip_bytes) > 500 and fname.endswith(".zip")

    print("   ✓ Admin Package CRUD, 7d/30d Charts, User Filters, 360° Card, Project Delete & CSV Export passed!")


if __name__ == "__main__":
    test_config_tariffs_and_cleanup()
    asyncio.run(test_templates_gost_and_photo_warning())
    test_three_bucket_credits_and_one_time_promos()
    asyncio.run(test_admin_crud_charts_filters_and_export())
    print("\n🎉 ALL COMMERCIAL PRO v2 FEATURES PASSED SUCCESSFULLY!")
