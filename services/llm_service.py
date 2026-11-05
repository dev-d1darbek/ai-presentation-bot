import json
import openai
from config import DEEPSEEK_API_KEY
from loguru import logger

class LLMService:
    @staticmethod
    async def generate_presentation_structure(topic: str, slide_count: int, language: str, style: str) -> dict:
        prompt = f"""
You are a professional presentation architect and content writer. Create a complete presentation structure in JSON format based on the following parameters:
- Topic: {topic}
- Slide count: {slide_count}
- Language: {language}
- Design style: {style}

Requirements:
1. Output ONLY valid JSON without markdown code blocks.
2. Structure format:
{{
  "title_presentation": "...",
  "slides": [
    {{
      "slide_number": 1,
      "title": "...",
      "layout": "title | bullets | two_columns",
      "content": ["Thesis 1", "Thesis 2", "Thesis 3"],
      "image_query": "English search query for stock photo related to this slide",
      "speaker_notes": "Short 1-3 sentence explanation for speech."
    }}
  ],
  "plan_summary": [
    "1-слайд. Кіріспе...",
    "2-слайд. ..."
  ]
}}
Must have exactly {slide_count} slides. Facts must be accurate and reliable.
"""
        try:
            # DeepSeek OpenAI-компитибелді клиенті
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional presentation planner and content writer. Always output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"DeepSeek generation error: {e}")
            raise e