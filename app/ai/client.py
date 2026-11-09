"""
Cost-Optimized Multi-Provider AI Client:
- Primary AI: DeepSeek ('deepseek-chat')
- Free Users (is_paid_user=False): DeepSeek -> Intelligent Fallback ONLY (Zero OpenAI/Gemini spend on free tier!)
- Paid Users (is_paid_user=True): DeepSeek -> Gemini -> OpenAI -> Intelligent Fallback
- Automatically strips any accidental 'ГОСТ 7.32-2017' boilerplate from LLM responses.
- Logs every model invocation to 'ai_usage_logs' for Admin AI Cost Tracking (📈 AI шығындарын бақылау).
"""
import os
import re
import time
import logging
from typing import Optional, Dict, Any, List
import httpx

from app.core.types import PresentationData, SlideContent, QualityScore
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY
from app.core.db import log_ai_usage
from app.ai.prompts import build_system_prompt
from app.ai.parser import robust_parse_json
from app.ai.fallback import generate_intelligent_fallback

logger = logging.getLogger(__name__)


def clean_gost_boilerplate(text: Optional[str]) -> str:
    """Removes repetitive 'ГОСТ 7.32-2017' phrases from slide text while keeping sentences natural."""
    if not text:
        return ""
    s = str(text)
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
    # Capitalize first letter of sentence if a leading phrase was stripped
    if len(s) > 1 and s[0].islower():
        s = s[0].upper() + s[1:]
    s = re.sub(r"([.!?]\s+)([а-яәіңғүұқөһa-z])", lambda m: m.group(1) + m.group(2).upper(), s)
    return s


def sanitize_slide_content(slide: SlideContent) -> SlideContent:
    """Cleans GOST boilerplate across all fields of a SlideContent instance."""
    slide.title = clean_gost_boilerplate(slide.title)
    if slide.subtitle:
        slide.subtitle = clean_gost_boilerplate(slide.subtitle)
    slide.content = clean_gost_boilerplate(slide.content)
    if slide.key_points:
        slide.key_points = [clean_gost_boilerplate(p) for p in slide.key_points if clean_gost_boilerplate(p)]
    if slide.timeline:
        for item in slide.timeline:
            item.title = clean_gost_boilerplate(item.title)
            item.desc = clean_gost_boilerplate(item.desc)
    if slide.stats:
        for st in slide.stats:
            st.value = clean_gost_boilerplate(st.value)
            st.label = clean_gost_boilerplate(st.label)
    if slide.comparison:
        slide.comparison.entityA.name = clean_gost_boilerplate(slide.comparison.entityA.name)
        slide.comparison.entityA.points = [clean_gost_boilerplate(p) for p in slide.comparison.entityA.points]
        slide.comparison.entityB.name = clean_gost_boilerplate(slide.comparison.entityB.name)
        slide.comparison.entityB.points = [clean_gost_boilerplate(p) for p in slide.comparison.entityB.points]
    if slide.quote and slide.quote.text:
        slide.quote.text = clean_gost_boilerplate(slide.quote.text)
    return slide


class AIClient:
    def __init__(
        self,
        deepseek_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.deepseek_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        self.gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    async def call_deepseek(self, user_prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Primary AI: Call DeepSeek API using deepseek-chat model with json_object format."""
        if not self.deepseek_key or not self.deepseek_key.strip():
            return None

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_key.strip()}",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                    or "You are a professional presentation architect and researcher. Always output strictly valid, compact JSON without mentioning standard codes like GOST inside slide text.",
                },
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.5,
            "max_tokens": 16384,
        }

        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return robust_parse_json(content)
                else:
                    logger.warning(f"DeepSeek API error: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"DeepSeek call failed: {e}")
        return None

    async def call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call Google Gemini API using REST endpoint (Paid users backup)."""
        if not self.gemini_key or not self.gemini_key.strip():
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key.strip()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.5,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            return robust_parse_json(text)
                else:
                    logger.warning(f"Gemini API error: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
        return None

    async def call_openai(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Call OpenAI API using gpt-4o-mini with json_object (Paid users ONLY)."""
        if not self.openai_key or not self.openai_key.strip():
            return None

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key.strip()}",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional presentation architect. Output strictly valid, compact JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.5,
            "max_tokens": 16384,
        }

        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return robust_parse_json(content)
                else:
                    logger.warning(f"OpenAI API error: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
        return None

    def _finalize_presentation(
        self,
        parsed: Dict[str, Any],
        topic: str,
        count: int,
        theme_id: str,
        total_score: int = 98,
        document_text: Optional[str] = None,
        language: str = "қазақша",
        template_id: str = "standard",
        with_photos: bool = False,
        persona_style: str = "academic_universal",
        is_storybook: bool = False,
        child_name: Optional[str] = None,
        child_avatar_desc: Optional[str] = None,
    ) -> PresentationData:
        raw_slides = parsed.get("slides", [])
        slides: List[SlideContent] = []

        for idx, s in enumerate(raw_slides):
            try:
                s["slide_number"] = s.get("slide_number") or (idx + 1)
                slide_obj = sanitize_slide_content(SlideContent(**s))
                slides.append(slide_obj)
            except Exception as e:
                logger.warning(f"Failed to parse slide {idx + 1}: {e}")

        if len(slides) < count:
            fb = generate_intelligent_fallback(
                topic, count, theme_id,
                document_text=document_text,
                language=language,
                template_id=template_id,
                with_photos=with_photos,
            )
            needed = count - len(slides)
            for i in range(needed):
                extra_idx = len(slides) + i
                extra_slide = (
                    fb.slides[extra_idx]
                    if extra_idx < len(fb.slides)
                    else (fb.slides[-1].model_copy(deep=True) if hasattr(fb.slides[-1], "model_copy") else fb.slides[-1].copy(deep=True))
                )
                extra_slide.slide_number = len(slides) + 1
                slides.append(sanitize_slide_content(extra_slide))

        plan_summary = [f"{s.slide_number}-слайд: {s.title}" for s in slides]

        return PresentationData(
            id=f"pres_{int(time.time())}_{len(slides)}",
            topic=topic,
            title_presentation=clean_gost_boilerplate(parsed.get("title_presentation")) or f"{topic}: Аналитикалық презентация",
            design_id=parsed.get("design_id") or theme_id,
            language=language,
            template_id=template_id,
            persona_style=persona_style,
            is_storybook=is_storybook,
            child_name=child_name,
            child_avatar_desc=child_avatar_desc,
            with_photos=with_photos,
            slide_count=len(slides),
            slides=slides,
            plan_summary=plan_summary,
            quality_score=QualityScore(total=total_score),
            createdAt=str(time.time()),
        )

    async def generate_presentation(
        self,
        topic: str,
        slide_count: int = 15,
        design_id: Optional[str] = None,
        language: str = "қазақша",
        document_text: Optional[str] = None,
        template_id: str = "standard",
        with_photos: bool = False,
        is_paid_user: bool = False,
        user_id: Optional[int] = None,
        persona_style: str = "academic_universal",
        is_storybook: bool = False,
        child_name: Optional[str] = None,
        child_avatar_desc: Optional[str] = None,
    ) -> PresentationData:
        """
        AI Cost Optimization Routing:
        - Primary model for everyone: DeepSeek
        - Free users (is_paid_user=False): DeepSeek -> Fallback (never calls OpenAI/Gemini!)
        - Paid users (is_paid_user=True): DeepSeek -> Gemini -> OpenAI -> Fallback
        """
        count = max(3, min(slide_count, 30))
        selected_theme = (
            THEMES_REGISTRY[design_id]
            if design_id and design_id in THEMES_REGISTRY
            else detect_best_theme_for_topic(topic, with_photos=with_photos)
        )

        prompt = build_system_prompt(
            topic, count, language, selected_theme,
            document_text=document_text,
            template_id=template_id,
            with_photos=with_photos,
            persona_style=persona_style,
            is_storybook=is_storybook,
            child_name=child_name,
            child_avatar_desc=child_avatar_desc,
        )

        # 1. Primary AI: DeepSeek (used for both free and paid users)
        if self.deepseek_key:
            logger.info("Attempting generation via DeepSeek (Primary AI)...")
            parsed = await self.call_deepseek(prompt)
            if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                log_ai_usage(user_id, "deepseek", units=1, topic=topic)
                return self._finalize_presentation(
                    parsed, topic, count, selected_theme.id, 98,
                    document_text=document_text, language=language,
                    template_id=template_id, with_photos=with_photos,
                    persona_style=persona_style, is_storybook=is_storybook, child_name=child_name, child_avatar_desc=child_avatar_desc,
                )

        # 2. Expensive backup models (Gemini & OpenAI): ONLY for paid users!
        if is_paid_user:
            if self.gemini_key:
                logger.info("Paid user backup: Attempting generation via Gemini...")
                parsed = await self.call_gemini(prompt)
                if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                    log_ai_usage(user_id, "gemini", units=1, topic=topic)
                    return self._finalize_presentation(
                        parsed, topic, count, selected_theme.id, 96,
                        document_text=document_text, language=language,
                        template_id=template_id, with_photos=with_photos,
                    )

            if self.openai_key:
                logger.info("Paid user backup: Attempting generation via OpenAI...")
                parsed = await self.call_openai(prompt)
                if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                    log_ai_usage(user_id, "openai_text", units=1, topic=topic)
                    return self._finalize_presentation(
                        parsed, topic, count, selected_theme.id, 97,
                        document_text=document_text, language=language,
                        template_id=template_id, with_photos=with_photos,
                    )

        # 3. Intelligent Fallback Generator (Zero API Cost)
        logger.info("Using Intelligent Multi-Language Fallback generator...")
        log_ai_usage(user_id, "fallback", units=1, topic=topic)
        return generate_intelligent_fallback(
            topic, count, selected_theme.id,
            document_text=document_text,
            language=language,
            template_id=template_id,
            with_photos=with_photos,
            persona_style=persona_style,
            is_storybook=is_storybook,
            child_name=child_name,
            child_avatar_desc=child_avatar_desc,
        )
