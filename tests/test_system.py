"""
Automated Test Suite for AI Presentation Bot (Python).
Tests 30 Themes, JSON Parsing, PPTX & PDF Engines, and Admin Database.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.themes import THEMES_REGISTRY, detect_best_theme_for_topic
from app.core.db import init_db, log_user, log_generation, get_admin_stats
from app.ai.parser import robust_parse_json
from app.ai.fallback import generate_intelligent_fallback
from app.pptx_generator.engine import build_pptx_deck
from app.pptx_generator.pdf_engine import build_pdf_deck
from app.bot.service import parse_user_input, reexport_deck_with_theme
from app.bot.session import get_telegram_session

def test_themes_registry():
    print("Testing Themes Registry...")
    assert len(THEMES_REGISTRY) == 30
    assert detect_best_theme_for_topic("Жасанды интеллект және IT").id == "futuristic_tech"
    assert detect_best_theme_for_topic("Қазақ хандығының тарихы").id == "cinematic_history"
    print("✓ Themes registry passed!")

def test_json_parser():
    print("Testing Robust JSON Parser...")
    normal = '{"slides": [{"slide_number": 1, "title": "Test"}]}'
    assert robust_parse_json(normal) is not None

    truncated = '{"title_presentation": "AI", "slides": [{"slide_number": 1, "title": "Intro"}, {"slide_number": 2, "title": "Unfinished"'
    salvaged = robust_parse_json(truncated)
    assert salvaged is not None
    assert len(salvaged["slides"]) == 1
    print("✓ JSON parser passed!")

def test_fallback_generator():
    print("Testing Kazakh Fallback Generator...")
    pres = generate_intelligent_fallback("Цифрлық Қазақстан", 15)
    assert pres.slide_count == 15
    assert len(pres.slides) == 15
    assert pres.slides[0].type == "cover"
    assert pres.slides[-1].type == "conclusion"
    print("✓ Fallback generator passed!")

def test_pptx_and_pdf_engines():
    print("Testing PPTX & PDF Engines (New Minimalist UI/UX)...")
    pres = generate_intelligent_fallback("Жасанды интеллект дамуы", 6)
    deck_bytes = build_pptx_deck(pres)
    assert len(deck_bytes) > 20000, f"PPTX too small: {len(deck_bytes)}"

    pdf_bytes = build_pdf_deck(pres, deck_bytes)
    assert len(pdf_bytes) > 10000, f"PDF too small: {len(pdf_bytes)}"
    print(f"✓ PPTX ({len(deck_bytes)} bytes) and PDF ({len(pdf_bytes)} bytes) generation passed!")

def test_database_and_admin():
    print("Testing SQLite Database & Admin Stats...")
    init_db()
    log_user(1001, "test_user", "Азамат")
    log_generation(1001, "Жасанды интеллект", 10, "futuristic_tech", "pptx")
    stats = get_admin_stats()
    assert stats["total_users"] >= 1
    assert stats["total_generations"] >= 1
    print("✓ Database & Admin stats passed!")

def test_input_parser():
    print("Testing User Input Parser...")
    topic, count, theme = parse_user_input("Жасанды интеллект 10 бет")
    assert topic == "Жасанды интеллект"
    assert count == 10
    print("✓ Input parser passed!")

if __name__ == "__main__":
    test_themes_registry()
    test_json_parser()
    test_fallback_generator()
    test_pptx_and_pdf_engines()
    test_database_and_admin()
    test_input_parser()
    print("\n🎉 ALL TESTS (PPTX, PDF, DB, ADMIN, AI) PASSED SUCCESSFULLY!")
