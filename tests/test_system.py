"""
Automated Test Suite for AI Presentation Bot (Python).
Tests:
1. 30 Themes Registry & Keyword Detection
2. Robust JSON Parser & Salvage
3. Kazakh Fallback Generator & Document-to-Slide Generator
4. Minimalist PPTX & Zero-Dependency Pillow PDF Engines
5. Speaker Defense Script ("🎤 Қорғау сөзі / Шпаргалка" as .DOCX & text)
6. Saved User Projects ("📂 Менің жобаларым")
7. Smart Cross-User Cache (user1 -> user2 instant cache hit with theme swap)
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.themes import THEMES_REGISTRY, detect_best_theme_for_topic
from app.core.db import (
    init_db,
    log_user,
    get_admin_stats,
    get_user_projects,
)
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
    parse_user_input,
    generate_deck_for_session,
    build_speech_for_session,
    load_saved_project_for_session,
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

    pdf_bytes = build_pdf_deck(pres, pptx_bytes=None)  # Force pure Pillow renderer test
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

    # Now test extracting text back from that .docx file and building a presentation from it!
    doc_title, extracted = extract_text_from_uploaded_file("Қазақстан_тарихы_мақала.docx", docx_bytes)
    assert "Құрметті комиссия мүшелері" in extracted
    doc_pres = generate_intelligent_fallback(doc_title, 6, document_text=extracted)
    assert len(doc_pres.slides) == 6
    print("   ✓ Document extraction (.DOCX) & Speaker Defense Speech (.DOCX) passed!")


async def test_smart_cache_and_saved_projects():
    print("5. Testing Smart Cross-User Cache & Saved User Projects...")
    init_db()
    user1_id = 10001
    user2_id = 20002
    log_user(user1_id, "user1", "Бірінші")
    log_user(user2_id, "user2", "Екінші")

    # User 1 creates a presentation on topic "Жасыл экономика негіздері" (8 slides, swiss_minimalism)
    s1 = get_telegram_session(user1_id)
    s1.pendingTopic = "Жасыл экономика негіздері"
    s1.slideCount = 8
    s1.designId = "swiss_minimalism"

    pptx1, fname1, pres1, from_cache1 = await generate_deck_for_session(s1, user_id=user1_id, slide_count=8)
    assert len(pptx1) > 20000
    assert pres1.design_id == "swiss_minimalism"

    # User 2 requests the SAME topic and slide count ("Жасыл экономика негіздері!", 8 slides),
    # but with a DIFFERENT design ("apple_keynote")!
    s2 = get_telegram_session(user2_id)
    s2.pendingTopic = "Жасыл экономика негіздері!"
    s2.slideCount = 8
    s2.designId = "apple_keynote"

    pptx2, fname2, pres2, from_cache2 = await generate_deck_for_session(s2, user_id=user2_id, slide_count=8)
    assert from_cache2 is True, "Expected Smart Cross-User Cache HIT for user2!"
    assert pres2.design_id == "apple_keynote", "Expected user2's chosen design to be applied!"
    assert len(pptx2) > 20000

    # Verify both user1 and user2 have the project saved in their "📂 Менің жобаларым"
    u1_projects, total1 = get_user_projects(user1_id)
    u2_projects, total2 = get_user_projects(user2_id)
    assert total1 >= 1 and total2 >= 1

    # Test loading saved project by ID for user2
    loaded = load_saved_project_for_session(s2, u2_projects[0]["id"], user_id=user2_id)
    assert loaded is not None
    loaded_pptx, loaded_fname, loaded_pres, theme_kz = loaded
    assert len(loaded_pptx) > 20000

    # Test building speaker defense speech for session
    speech_res = build_speech_for_session(s2)
    assert speech_res is not None
    print("   ✓ Smart Cross-User Cache & Saved User Projects passed!")


if __name__ == "__main__":
    test_themes_registry()
    test_json_parser()
    test_pptx_and_pdf_engines()
    test_document_to_slide_and_defense_speech()
    asyncio.run(test_smart_cache_and_saved_projects())
    print("\n🎉 ALL SYSTEM TESTS PASSED SUCCESSFULLY!")
