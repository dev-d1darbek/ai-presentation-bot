"""
DuckDuckGo сурет іздеу (тұрақты нұсқа) + OpenAI gpt-image-2 Low генерациялау модулі.
- Region rotation: us-en → de-de → uk-en → fr-fr → ca-en
- Retry: әр region-да 2 әрекет
- In-memory кэш: бір тақырыпты қайта іздемеу (24 сағат)
- OpenAI gpt-image-2 (quality="low") AI сурет генерациясы (тек VIP/Pro/Hit/500₸ OpenAI лимиті барларға!)
- AI шығындарын 'ai_usage_logs' кестесіне тіркеу
"""
import asyncio
import base64
import hashlib
import io
import logging
import os
import time
from typing import Optional, List, Dict, Any, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFont

import config
from app.core.types import PresentationData, SlideContent
from app.core.themes import THEMES_REGISTRY
from app.core.db import log_ai_usage, get_cached_slide_image, save_cached_slide_image

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

logger = logging.getLogger(__name__)

# Сыналған, сенімді аймақтар
REGIONS = ["us-en", "de-de", "uk-en", "fr-fr", "ca-en"]

# In-memory кэш: query → (timestamp, results)
_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_image_bytes_cache: Dict[str, bytes] = {}
CACHE_TTL = 3600 * 24  # 24 сағат


def _is_cache_valid(query: str) -> bool:
    if query not in _cache:
        return False
    ts, _ = _cache[query]
    return (time.time() - ts) < CACHE_TTL


async def search_images(
    query: str,
    max_results: int = 5,
    safe_search: str = "Moderate",   # "On" | "Moderate" | "Off"
    license_filter: Optional[str] = None,  # "ShareCommercially" | "Any"
) -> List[Dict[str, Any]]:
    """
    DuckDuckGo-дан сурет іздеу. Region rotation + retry.
    Қайтарады: [{"image": url, "thumbnail": url, "title": ..., "width": ..., "height": ...}, ...]
    """
    if not query or not query.strip():
        return []

    if _is_cache_valid(query):
        logger.info(f"DDG cache hit: {query}")
        return _cache[query][1]

    if DDGS is None:
        logger.warning("ddgs library is not installed; skipping live DDG image search")
        return []

    for region in REGIONS:
        for attempt in range(2):
            try:
                results = await asyncio.to_thread(
                    _search_sync,
                    query, region, max_results, safe_search, license_filter,
                )
                if results:
                    _cache[query] = (time.time(), results)
                    logger.info(f"DDG ok: query='{query}', region={region}, n={len(results)}")
                    return results
            except Exception as e:
                logger.warning(f"DDG failed (region={region}, attempt={attempt + 1}): {e}")
                await asyncio.sleep(1.5)

    logger.warning(f"DDG: all regions failed for '{query}'")
    return []


def _search_sync(
    query: str,
    region: str,
    max_results: int,
    safe_search: str,
    license_filter: Optional[str],
) -> List[Dict[str, Any]]:
    """Синхронды DDGS шақыру (to_thread ішінде)."""
    if DDGS is None:
        return []

    kwargs: Dict[str, Any] = {
        "query": query,
        "region": region,
        "max_results": max_results,
        "safesearch": safe_search,
    }
    if license_filter:
        kwargs["license_image"] = license_filter

    with DDGS() as ddgs:
        results = list(ddgs.images(**kwargs))

    cleaned = []
    for r in results:
        if r.get("image"):
            cleaned.append({
                "image": r["image"],
                "thumbnail": r.get("thumbnail"),
                "title": r.get("title", ""),
                "width": r.get("width"),
                "height": r.get("height"),
                "source": r.get("source", ""),
            })
    return cleaned



async def analyze_child_photo_gpt4o_vision(
    image_bytes: bytes,
    openai_api_key: Optional[str] = None,
    user_id: Optional[int] = None,
) -> str:
    """
    Пайдаланушы жіберген баланың фотосын GPT-4o Vision-ға жібереді.
    System prompt: "Бұл баланың бет-әлпетін, шаш түсін, көзін, киімін егжей-тегжейлі мәтін түрінде
    сипаттап бер (DALL·E 3-ке промт дайындау үшін)."
    Қайтарады: тұрақты "цифрлық аватар" сипаттамасы (мысалы:
    "7-year-old Kazakh boy, round face, short dark hair, expressive brown eyes, small smile, wearing a blue hoodie").
    """
    default_avatar = (
        "7-year-old Kazakh child, round face, short dark hair, expressive brown eyes, "
        "warm joyful smile, wearing colorful cozy adventure clothes"
    )
    if not image_bytes or len(image_bytes) < 200:
        return default_avatar

    # Normalize image to compact JPEG for Vision API
    try:
        with Image.open(io.BytesIO(image_bytes)).convert("RGB") as im:
            im.thumbnail((768, 768), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85)
            norm_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        return default_avatar

    api_key = openai_api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if api_key and api_key.strip() and not config.DEBUG_MODE:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key.strip()}",
        }
        system_prompt = (
            "Бұл баланың бет-әлпетін, шаш түсін, көзін, киімін егжей-тегжейлі мәтін түрінде сипаттап бер "
            "(DALL·E 3-ке промт дайындау үшін). "
            "Write ONLY a concise, vivid English character description (20-35 words) describing the child's "
            "approximate age, facial structure, hair color and style, eye color, expression, and outfit so it can be "
            "used as a consistent character prompt prefix for DALL·E 3 / GPT-Image storybook illustrations "
            "(for example: '7-year-old Kazakh boy, round face, short dark hair, expressive brown eyes, small smile, wearing a red sweater'). "
            "Do NOT include any intro text or quotes — return only the English character description."
        )
        for model_name in ("gpt-4o", "gpt-4o-mini"):
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Бұл баланың бет-әлпетін, шаш түсін, көзін, киімін DALL·E 3 промты үшін сипаттап бер.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{norm_b64}", "detail": "low"},
                            },
                        ],
                    },
                ],
                "max_tokens": 120,
                "temperature": 0.3,
            }
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post(url, headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        desc = (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                            .strip("'\"")
                        )
                        if len(desc) >= 15:
                            log_ai_usage(user_id, "openai_vision", units=1, topic="gpt4o_child_avatar")
                            return desc
            except Exception as e:
                logger.warning(f"GPT-4o Vision ({model_name}) failed: {e}")

    return default_avatar


async def generate_image_gpt_image_2(
    prompt: str,
    openai_api_key: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[bytes]:
    """
    OpenAI gpt-image-2 (немесе gpt-image-1) арқылы Low сапада AI фото генерациялау (~$0.02/image).
    Тек VIP/Pro/Хит/500₸ OpenAI лимиті бар қолданушыларға рұқсат етіледі!
    """
    api_key = openai_api_key or config.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        return None

    cache_key = f"gpt_img2::{prompt.strip().lower()}"
    if cache_key in _image_bytes_cache:
        return _image_bytes_cache[cache_key]

    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key.strip()}",
    }

    is_story_prompt = "storybook" in prompt.lower() or "fairy-tale" in prompt.lower() or "pixar" in prompt.lower()
    full_img_prompt = (
        f"Pixar/Disney 3D children's fairy-tale book illustration, magical vibrant lighting, consistent character, no text or letters: {prompt}"
        if is_story_prompt
        else f"Editorial presentation photography, clean modern aesthetic, no text overlay: {prompt}"
    )
    models_to_try = ("dall-e-3", "gpt-image-2", "gpt-image-1") if is_story_prompt else ("gpt-image-2", "gpt-image-1", "dall-e-3")
    for model_name in models_to_try:
        payload: Dict[str, Any] = {
            "model": model_name,
            "prompt": full_img_prompt[:950],
            "n": 1,
            "size": "1024x1024",
        }
        if model_name != "dall-e-3":
            payload["quality"] = "low"
        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    item = (data.get("data") or [{}])[0]
                    if item.get("b64_json"):
                        img_bytes = base64.b64decode(item["b64_json"])
                        norm = _normalize_image_for_pptx(img_bytes)
                        if norm:
                            _image_bytes_cache[cache_key] = norm
                            log_ai_usage(user_id, "gpt-image-2", units=1, topic=prompt)
                            return norm
                    if item.get("url"):
                        dl = await download_image_bytes(item["url"])
                        if dl:
                            _image_bytes_cache[cache_key] = dl
                            log_ai_usage(user_id, "gpt-image-2", units=1, topic=prompt)
                            return dl
        except Exception as e:
            logger.warning(f"OpenAI {model_name} image generation failed: {e}")

    return None


def _normalize_image_for_pptx(raw_bytes: bytes, target_w: int = 960, target_h: int = 640) -> Optional[bytes]:
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        src_w, src_h = img.size
        if src_w < 80 or src_h < 80:
            return None

        target_ratio = target_w / target_h
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            new_w = int(src_h * target_ratio)
            offset = (src_w - new_w) // 2
            img = img.crop((offset, 0, offset + new_w, src_h))
        else:
            new_h = int(src_w / target_ratio)
            offset = (src_h - new_h) // 2
            img = img.crop((0, offset, src_w, offset + new_h))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=88)
        return out.getvalue()
    except Exception:
        return None


async def download_image_bytes(url: str) -> Optional[bytes]:
    if not url or not url.startswith("http"):
        return None
    if url in _image_bytes_cache:
        return _image_bytes_cache[url]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1500:
                norm = _normalize_image_for_pptx(resp.content)
                if norm:
                    _image_bytes_cache[url] = norm
                    return norm
    except Exception:
        pass
    return None


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    c = h.strip().lstrip("#")
    if len(c) != 6:
        return (30, 41, 59)
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def render_editorial_visual_card(
    title: str,
    subtitle: str,
    theme_id: str,
    slide_number: int = 1,
    width: int = 960,
    height: int = 640,
) -> bytes:
    """Renders a sleek, high-resolution modern abstract editorial visual illustration when offline."""
    theme = THEMES_REGISTRY.get(theme_id, THEMES_REGISTRY["swiss_minimalism"])
    bg = _hex_to_rgb(theme.bgColor if theme.isDark else theme.primaryColor)
    sec = _hex_to_rgb(theme.secondaryColor)
    acc = _hex_to_rgb(theme.accentColor)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img, "RGBA")

    seed = int(hashlib.md5(f"{title}_{slide_number}".encode("utf-8")).hexdigest()[:6], 16)
    for y in range(0, height, 4):
        t = y / height
        r = int(bg[0] * (1 - 0.35 * t) + sec[0] * (0.35 * t))
        g = int(bg[1] * (1 - 0.35 * t) + sec[1] * (0.35 * t))
        b = int(bg[2] * (1 - 0.35 * t) + sec[2] * (0.35 * t))
        draw.rectangle([0, y, width, y + 4], fill=(r, g, b, 255))

    cx1 = int(width * (0.65 + (seed % 20) * 0.01))
    cy1 = int(height * (0.35 + ((seed >> 4) % 20) * 0.01))
    for rad in range(320, 40, -28):
        alpha = int(22 + (320 - rad) * 0.22)
        draw.ellipse(
            [cx1 - rad, cy1 - rad, cx1 + rad, cy1 + rad],
            fill=(sec[0], sec[1], sec[2], min(110, alpha)),
            outline=(acc[0], acc[1], acc[2], 70),
            width=2,
        )

    cx2 = int(width * 0.25)
    cy2 = int(height * 0.72)
    for rad in range(220, 30, -35):
        draw.ellipse(
            [cx2 - rad, cy2 - rad, cx2 + rad, cy2 + rad],
            outline=(acc[0], acc[1], acc[2], 95),
            width=2,
        )

    for gx in range(80, width, 120):
        draw.line([(gx, 0), (gx, height)], fill=(255, 255, 255, 18), width=1)
    for gy in range(80, height, 120):
        draw.line([(0, gy), (width, gy)], fill=(255, 255, 255, 18), width=1)

    pad_x, pad_y = 64, height - 190
    draw.rounded_rectangle(
        [pad_x, pad_y, width - pad_x, height - 48],
        radius=18,
        fill=(15, 23, 42, 165),
        outline=(255, 255, 255, 65),
        width=2,
    )

    try:
        from app.pptx_generator.pdf_engine import _load_font
        f_num = _load_font(22, bold=True)
        f_tit = _load_font(26, bold=True)
    except Exception:
        f_num = ImageFont.load_default()
        f_tit = ImageFont.load_default()

    draw.text((pad_x + 28, pad_y + 22), f"VISUAL INSIGHT • 0{slide_number}", font=f_num, fill=(sec[0], sec[1], sec[2], 255))
    short_t = (title or "Visual Concept")[:42]
    draw.text((pad_x + 28, pad_y + 62), short_t, font=f_tit, fill=(255, 255, 255, 245))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


async def fetch_image_for_slide(
    topic: str,
    slide: SlideContent,
    theme_id: str,
    image_source: str = "ddg",
    user_id: Optional[int] = None,
    child_avatar_desc: Optional[str] = None,
    is_storybook: bool = False,
) -> bytes:
    raw_scene = (slide.image_query or f"{topic} {slide.title}").strip()
    if is_storybook:
        if child_avatar_desc:
            query = f"Pixar 3D fairy-tale illustration, main character ({child_avatar_desc}), scene: {raw_scene}"
        else:
            query = f"Pixar 3D children fairy-tale storybook illustration, scene: {raw_scene}"
    else:
        query = raw_scene

    # 1. Check Redis + SQLite Image Cache first (100 users ask same topic -> 0 duplicate image downloads/generations!)
    cached_img = get_cached_slide_image(query, source=image_source)
    if cached_img:
        return cached_img

    if image_source == "gpt-image-2" and config.OPENAI_API_KEY and not config.DEBUG_MODE:
        img_bytes = await generate_image_gpt_image_2(query, user_id=user_id)
        if img_bytes:
            save_cached_slide_image(query, img_bytes, source="gpt-image-2")
            return img_bytes

    if not config.DEBUG_MODE:
        results = await search_images(query, max_results=4)
        if results:
            log_ai_usage(user_id, "ddg_images", units=1, topic=query)
        for r in results:
            for url_key in ("image", "thumbnail"):
                u = r.get(url_key)
                if u:
                    dl = await download_image_bytes(u)
                    if dl:
                        slide.image_url = u
                        save_cached_slide_image(query, dl, source="ddg")
                        return dl

    fallback_img = render_editorial_visual_card(
        title=slide.title,
        subtitle=slide.subtitle or topic,
        theme_id=theme_id,
        slide_number=slide.slide_number,
    )
    save_cached_slide_image(query, fallback_img, source=image_source)
    return fallback_img


async def populate_presentation_images(
    presentation: PresentationData,
    image_source: str = "ddg",
    user_id: Optional[int] = None,
) -> PresentationData:
    presentation.with_photos = True
    presentation.image_source = image_source

    tasks = []
    target_slides: List[SlideContent] = []

    is_story = bool(getattr(presentation, "is_storybook", False) or presentation.template_id == "storybook")
    for idx, slide in enumerate(presentation.slides):
        if is_story:
            slide.type = "storybook_full_photo"
        if slide.image_bytes_b64 and len(slide.image_bytes_b64) > 500:
            # Already cached inside presentation_cache!
            continue
        if is_story or idx == 0 or slide.type in ("cover", "split_screen", "photo_hero", "photo_split", "photo_magazine", "key_takeaway", "conclusion", "storybook_full_photo"):
            target_slides.append(slide)
            tasks.append(
                fetch_image_for_slide(
                    topic=presentation.topic,
                    slide=slide,
                    theme_id=presentation.design_id,
                    image_source=image_source,
                    user_id=user_id,
                    child_avatar_desc=getattr(presentation, "child_avatar_desc", None),
                    is_storybook=is_story,
                )
            )

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for slide, res in zip(target_slides, results):
            if isinstance(res, bytes) and len(res) > 500:
                slide.image_bytes_b64 = base64.b64encode(res).decode("ascii")

    return presentation
