"""
Robust JSON parser with automatic salvage for truncated LLM responses.
"""
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def robust_parse_json(raw: str) -> Optional[Dict[str, Any]]:
    """
    Parses JSON from raw LLM output, stripping markdown codeblocks and
    salvaging valid slide objects if the output was truncated.
    """
    if not raw or not isinstance(raw, str):
        return None
    
    clean = raw.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()

    # Try standard parse
    try:
        data = json.loads(clean)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Salvage truncated JSON inside slides array
    try:
        slides_key = clean.find('"slides"')
        if slides_key != -1:
            array_start = clean.find('[', slides_key)
            if array_start != -1:
                last_closing = clean.rfind('}')
                while last_closing > array_start:
                    candidate = clean[:last_closing + 1] + ']}'
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and isinstance(parsed.get('slides'), list) and len(parsed['slides']) > 0:
                            logger.info(f"Salvaged {len(parsed['slides'])} slides from truncated LLM response")
                            return parsed
                    except Exception:
                        pass
                    last_closing = clean.rfind('}', 0, last_closing)
    except Exception as e:
        logger.error(f"Error during JSON salvage: {e}")

    return None
