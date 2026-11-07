"""
Multi-provider AI client supporting DeepSeek, Gemini, OpenAI, and Intelligent Fallback.
"""
import os
import json
import time
import logging
from typing import Optional, Dict, Any, List
import httpx

from app.core.types import PresentationData, SlideContent, QualityScore
from app.core.themes import detect_best_theme_for_topic, THEMES_REGISTRY
from app.ai.prompts import build_system_prompt
from app.ai.parser import robust_parse_json
from app.ai.fallback import generate_intelligent_fallback

logger = logging.getLogger(__name__)

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
        """Call DeepSeek API using deepseek-chat model with json_object format."""
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
                    "content": system_prompt or "You are a professional presentation architect and visual designer. Always output strictly valid, compact JSON.",
                },
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.5,
            "max_tokens": 8192,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
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
        """Call Google Gemini API using REST endpoint."""
        if not self.gemini_key or not self.gemini_key.strip():
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key.strip()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.5,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
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
        """Call OpenAI API using gpt-4o-mini / gpt-4o with json_object."""
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
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
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
        total_score: int = 98
    ) -> PresentationData:
        """Pads and converts raw dictionary slides to PresentationData."""
        raw_slides = parsed.get("slides", [])
        slides: List[SlideContent] = []

        for idx, s in enumerate(raw_slides):
            try:
                # Normalize slide_number
                s["slide_number"] = s.get("slide_number") or (idx + 1)
                slides.append(SlideContent(**s))
            except Exception as e:
                logger.warning(f"Failed to parse slide {idx + 1}: {e}")

        # Pad with fallback if LLM generated fewer slides than requested
        if len(slides) < count:
            fb = generate_intelligent_fallback(topic, count, theme_id)
            needed = count - len(slides)
            for i in range(needed):
                extra_idx = len(slides) + i
                extra_slide = (
                    fb.slides[extra_idx]
                    if extra_idx < len(fb.slides)
                    else fb.slides[-1].model_copy(deep=True)
                )
                extra_slide.slide_number = len(slides) + 1
                slides.append(extra_slide)

        plan_summary = [f"{s.slide_number}-слайд: {s.title}" for s in slides]

        return PresentationData(
            id=f"pres_{int(time.time())}_{len(slides)}",
            topic=topic,
            title_presentation=parsed.get("title_presentation") or f"{topic}: Аналитикалық презентация",
            design_id=parsed.get("design_id") or theme_id,
            language="қазақша",
            slide_count=len(slides),
            slides=slides,
            plan_summary=plan_summary,
            quality_score=QualityScore(total=total_score),
        )

    async def generate_presentation(
        self,
        topic: str,
        slide_count: int = 15,
        design_id: Optional[str] = None,
        language: str = "қазақша",
    ) -> PresentationData:
        """
        Generates full presentation: tries DeepSeek -> Gemini -> OpenAI -> Fallback.
        """
        count = max(3, min(slide_count, 30))
        selected_theme = (
            THEMES_REGISTRY[design_id]
            if design_id and design_id in THEMES_REGISTRY
            else detect_best_theme_for_topic(topic)
        )

        prompt = build_system_prompt(topic, count, language, selected_theme)

        # 1. DeepSeek
        if self.deepseek_key:
            logger.info("Attempting generation via DeepSeek...")
            parsed = await self.call_deepseek(prompt)
            if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                logger.info(f"Successfully generated presentation via DeepSeek ({len(parsed['slides'])} slides)")
                return self._finalize_presentation(parsed, topic, count, selected_theme.id, 98)

        # 2. Gemini
        if self.gemini_key:
            logger.info("Attempting generation via Gemini...")
            parsed = await self.call_gemini(prompt)
            if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                logger.info(f"Successfully generated presentation via Gemini ({len(parsed['slides'])} slides)")
                return self._finalize_presentation(parsed, topic, count, selected_theme.id, 96)

        # 3. OpenAI
        if self.openai_key:
            logger.info("Attempting generation via OpenAI...")
            parsed = await self.call_openai(prompt)
            if parsed and isinstance(parsed.get("slides"), list) and len(parsed["slides"]) > 0:
                logger.info(f"Successfully generated presentation via OpenAI ({len(parsed['slides'])} slides)")
                return self._finalize_presentation(parsed, topic, count, selected_theme.id, 97)

        # 4. Fallback generator
        logger.info("Using Intelligent Kazakh fallback generator...")
        return generate_intelligent_fallback(topic, count, selected_theme.id)
