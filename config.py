"""
Configuration settings for AI Presentation Bot (Commercial Pro v2 Edition).
Loads from environment variables or .env file.
"""
import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY", "").strip() or None
GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "").strip() or None
OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", "").strip() or None

# Database & Redis & Analytics (Production Scaling)
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "").strip() or None
REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "").strip() or None
MIXPANEL_TOKEN: Optional[str] = os.getenv("MIXPANEL_TOKEN", "").strip() or None
POSTHOG_API_KEY: Optional[str] = os.getenv("POSTHOG_API_KEY", "").strip() or None
POSTHOG_HOST: str = os.getenv("POSTHOG_HOST", "https://app.posthog.com").strip()
SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN", "").strip() or None
PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "0") or "0")
REFERAT_BOT_URL: str = os.getenv("REFERAT_BOT_URL", "https://t.me/referat_kz_bot").strip()

DEFAULT_SLIDE_COUNT: int = int(os.getenv("DEFAULT_SLIDE_COUNT", "15"))
DEFAULT_THEME_ID: str = os.getenv("DEFAULT_THEME_ID", "swiss_minimalism")
MAX_SLIDE_COUNT: int = 30
MIN_SLIDE_COUNT: int = 3

# Welcome, Referral & 3-Day Daily Login Streak Rules
# Ереже: Тегін бонус презентацияларда тек «Бір реттік» (фотосыз) және «Бір реттік + ФОТО» (DDG) қолданылады!
WELCOME_FREE_CREDITS: int = int(os.getenv("WELCOME_FREE_CREDITS", "1"))
REFERRAL_FRIENDS_FOR_FREE_SLIDE: int = 2
STREAK_DAYS_FOR_FREE_SLIDE: int = 3
PARTNER_MIN_INVITED_USERS: int = 20
PARTNER_SALES_THRESHOLD_KZT: int = 10000
PARTNER_REWARD_KZT: int = 2000
MIN_WITHDRAWAL_KZT: int = int(os.getenv("MIN_WITHDRAWAL_KZT", "2000"))

# Kaspi Pay Fiscal Verifier Settings
KASPI_PAY_URL: str = os.getenv("KASPI_PAY_URL", "https://pay.kaspi.kz/pay/YOUR_KASPI_LINK").strip()
KASPI_BIN: str = os.getenv("KASPI_BIN", "").strip()
KASPI_PHONE: str = os.getenv("KASPI_PHONE", "+7 777 000 00 00").strip()
KASPI_RECIPIENT_NAME: str = os.getenv("KASPI_RECIPIENT_NAME", "").strip()

# .env-те DEBUG=1 болса ғана offline чек тексеру рұқсат етіледі
DEBUG_MODE: bool = os.getenv("DEBUG", "0").strip() in ("1", "true", "True", "yes")

# Admin Support Contact (@username)
ADMIN_CONTACT: str = os.getenv("ADMIN_CONTACT", "").strip()

# DuckDuckGo Фото ескертуі (Міндетті дисклеймер)
DDG_PHOTO_WARNING_TEXT: str = (
    "⚠️ <i>Ескерту: «Фотомен (Интернет/ЖИ)» режиміндегі суреттер интернеттен мысал ретінде "
    "автоматты түрде алынады (ЖИ қателесуі мүмкін). Егер кейбір фото ұнамаса, дайын .PPTX "
    "файлының ішінде өзіңіз қалаған суретке оңай ауыстырып ала аласыз!</i>"
)

# Estimated AI unit costs (USD) for Admin AI Cost Tracker (📈 AI шығындарын бақылау)
AI_COST_RATES_USD: Dict[str, float] = {
    "deepseek": 0.0015,       # ~$0.0015 per presentation (primary model)
    "gemini": 0.0020,         # ~$0.0020 per presentation
    "openai_text": 0.0080,    # ~$0.0080 per presentation (paid users only)
    "gpt-image-2": 0.0200,
    "openai_vision": 0.0050,  # ~$0.005 per GPT-4o Vision child avatar analysis    # ~$0.02 per generated image (VIP/Pro/Hit/500₸ only)
    "ddg_images": 0.0000,     # Free DuckDuckGo image search
    "fallback": 0.0000,       # Free local intelligent generator
}
USD_TO_KZT_RATE: int = 500

# Tariff Plans (Admin can also create, edit, or delete packages dynamically in DB!)
TARIFF_PLANS: Dict[str, Dict[str, Any]] = {
    "single": {
        "id": "single",
        "title": "«Бір реттік»",
        "price_kzt": 200,
        "credits": 1,
        "no_photo_credits": 1,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 0,
        "with_photos": False,
        "description": "1 презентация (фотосыз)",
    },
    "single_photo": {
        "id": "single_photo",
        "title": "«Бір реттік + ФОТО»",
        "price_kzt": 300,
        "credits": 1,
        "no_photo_credits": 0,
        "ddg_photo_credits": 1,
        "openai_photo_credits": 0,
        "with_photos": True,
        "description": "1 презентация (интернеттен мысал фотомен — ЖИ қателесуі мүмкін, PPTX-те ауыстыруға болады)",
    },
    "single_openai": {
        "id": "single_openai",
        "title": "«Бір реттік + ФОТО (OpenAI)»",
        "price_kzt": 500,
        "credits": 1,
        "no_photo_credits": 0,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 1,
        "with_photos": True,
        "description": "1 презентация (OpenAI gpt-image-2 AI фотогенерациясымен)",
    },
    "hit": {
        "id": "hit",
        "title": "«Студент (Хит)»",
        "price_kzt": 3490,
        "credits": 20,
        "no_photo_credits": 10,
        "ddg_photo_credits": 5,
        "openai_photo_credits": 5,
        "with_photos": True,
        "description": "20 презентация (10 фотосыз + 5 фотомен + 5 OpenAI)",
    },
    "pro": {
        "id": "pro",
        "title": "«Студент Pro»",
        "price_kzt": 4900,
        "credits": 30,
        "no_photo_credits": 10,
        "ddg_photo_credits": 10,
        "openai_photo_credits": 10,
        "with_photos": True,
        "description": "30 презентация (10 фотосыз + 10 фотомен + 10 OpenAI)",
    },
    "vip": {
        "id": "vip",
        "title": "«Студент (VIP)»",
        "price_kzt": 9900,
        "credits": 80,
        "no_photo_credits": 40,
        "ddg_photo_credits": 20,
        "openai_photo_credits": 20,
        "with_photos": True,
        "description": "80 презентация (40 фотосыз + 20 фотомен + 20 OpenAI)",
    },
    "kids_presentation": {
        "id": "kids_presentation",
        "title": "«Балаларға арналған презентация»",
        "price_kzt": 990,
        "credits": 1,
        "no_photo_credits": 0,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 1,
        "with_photos": True,
        "description": "1 балаларға арналған түрлі-түсті иллюстрацияланған презентация (990 ₸)",
    },
    "kids_storybook": {
        "id": "kids_storybook",
        "title": "«Ертегі-презентация (Бала фотосынсыз)»",
        "price_kzt": 1490,
        "credits": 1,
        "no_photo_credits": 0,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 1,
        "with_photos": True,
        "is_storybook": True,
        "with_child_photo": False,
        "description": "Баланың аты + ертегі тақырыбы → тек толық фотолардан тұратын ертегі-презентация (1 490 ₸)",
    },
    "kids_storybook_photo": {
        "id": "kids_storybook_photo",
        "title": "«Ертегі-презентация (Бала фотосымен)»",
        "price_kzt": 4990,
        "credits": 1,
        "no_photo_credits": 0,
        "ddg_photo_credits": 0,
        "openai_photo_credits": 1,
        "with_photos": True,
        "is_storybook": True,
        "with_child_photo": True,
        "description": "Баланың фотосы (GPT-4o Vision цифрлық аватар) + ертегі сюжеті → балаңыз басты кейіпкер болатын ертегі (4 990 ₸)",
    },
}

# Built-in Promo Codes & University Partnership Discounts (One-time use per user!)
DEFAULT_PROMO_CODES: Dict[str, Dict[str, Any]] = {
    "ALASH2025": {
        "code": "ALASH2025",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "Арнайы науқан — 1 реттік 50% жеңілдік",
    },
    "KAZNU50": {
        "code": "KAZNU50",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "ҚазҰУ (KazNU) студенттеріне 1 реттік 50% жеңілдік",
    },
    "ENU50": {
        "code": "ENU50",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "ЕҰУ (ENU) студенттеріне 1 реттік 50% жеңілдік",
    },
    "SATBAYEV50": {
        "code": "SATBAYEV50",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "Satbayev University студенттеріне 1 реттік 50% жеңілдік",
    },
    "SDU50": {
        "code": "SDU50",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "SDU студенттеріне 1 реттік 50% жеңілдік",
    },
    "COMEBACK50": {
        "code": "COMEBACK50",
        "discount_percent": 50,
        "bonus_credits": 0,
        "description": "AI Churn Бонусы — 1 реттік пакеттерге 50% жеңілдік",
    },
    "BONUS2025": {
        "code": "BONUS2025",
        "discount_percent": 0,
        "bonus_credits": 1,
        "description": "Сыйлық науқаны — +1 тегін презентация (Бір реттік / Фотомен)",
    },
}

# Supported Presentation Languages (3x Market Expansion)
SUPPORTED_LANGUAGES: Dict[str, Dict[str, str]] = {
    "қазақша": {"code": "қазақша", "label": "🇰🇿 Қазақша", "short": "🇰🇿 ҚАЗ"},
    "русский": {"code": "русский", "label": "🇷🇺 Орысша (Русский)", "short": "🇷🇺 РУС"},
    "english": {"code": "english", "label": "🇬🇧 Ағылшынша (English)", "short": "🇬🇧 ENG"},
}


# User Specialty / Course Styles (Персонализация)
PERSONA_STYLES: Dict[str, Dict[str, str]] = {
    "academic_universal": {
        "id": "academic_universal",
        "title": "🎓 Студент (Академиялық стиль)",
        "short": "🎓 Академиялық",
        "prompt_rule": "Use rigorous university academic style with clear theoretical definitions, analytical arguments, and structured conclusions.",
    },
    "medical_science": {
        "id": "medical_science",
        "title": "🧬 Медицина студенті → Ғылыми стиль",
        "short": "🧬 Ғылыми (Мед)",
        "prompt_rule": "Write in a strict evidence-based scientific & clinical medical style: emphasize etiology, pathogenesis, clinical diagnostic criteria, empirical statistics, and systematic medical terminology.",
    },
    "business_pitch": {
        "id": "business_pitch",
        "title": "💼 Бизнес студенті → Презентациялық стиль",
        "short": "💼 Презентациялық (Бизнес)",
        "prompt_rule": "Write in a dynamic executive business presentation style: focus on market sizing (TAM/SAM/SOM), ROI, KPIs, unit economics, competitive differentiation, and actionable growth strategies.",
    },
    "teacher_pedagogy": {
        "id": "teacher_pedagogy",
        "title": "👩‍🏫 Мұғалім → Педагогикалық стиль",
        "short": "👩‍🏫 Педагогикалық (Мұғалім)",
        "prompt_rule": "Write in a clear pedagogical & didactic style tailored for teachers: include clear learning objectives, accessible step-by-step explanations, engaging real-life examples, and student reflection takeaways.",
    },
    "kids_fairy": {
        "id": "kids_fairy",
        "title": "🧚 Балалар ертегісі / Танымдық стиль",
        "short": "🧚 Ертегі / Балалар",
        "prompt_rule": "Write in a magical, warm, imaginative children's fairy-tale and kid-friendly educational style with vivid sensory descriptions, heroic adventures, and an inspiring moral lesson.",
    },
}

# Expanded Template Library (8 Academic/Professional Templates)
TEMPLATE_LIBRARY: Dict[str, Dict[str, Any]] = {
    "standard": {
        "id": "standard",
        "title": "📑 Стандартты (Академиялық)",
        "gost_compliant": True,
        "structure": [],
    },
    "diploma": {
        "id": "diploma",
        "title": "🎓 Диплом қорғау",
        "gost_compliant": True,
        "structure": [
            "Кіріспе: Тақырыптың өзектілігі мен маңызы",
            "Зерттеудің мақсаты, міндеттері, нысаны мен пәні",
            "Теориялық-әдіснамалық негіздер және ғылыми жаңалығы",
            "Аналитикалық бөлім: Қазіргі жағдайды кешенді бағалау",
            "Жобалық-тәжірибелік бөлім және қолданбалы шешімдер",
            "Экономикалық және практикалық тиімділік көрсеткіштері",
            "Қорытынды тұжырымдар мен қорғауға шығарылатын қағидалар",
        ],
    },
    "business": {
        "id": "business",
        "title": "💼 Бизнес-жоспар",
        "gost_compliant": False,
        "structure": [
            "Жобаның түйіндемесі (Executive Summary) және миссиясы",
            "Нарық талдауы (TAM / SAM / SOM) және тұтынушы портреті",
            "Өнім немесе қызметтің бірегей артықшылықтары (USP)",
            "Бәсекелестік орта және салыстырмалы талдау",
            "Маркетингтік және сату стратегиясы (Go-to-Market)",
            "Қаржылық модель: шығындар, табыс болжамы және өзін-өзі ақтау (ROI)",
            "Тәуекелдерді басқару және инвестициялық ұсыныс",
        ],
    },
    "scientific": {
        "id": "scientific",
        "title": "🔬 Ғылыми баяндама",
        "gost_compliant": True,
        "structure": [
            "Аннотация, кілт сөздер және ғылыми мәселенің қойылымы",
            "Зерттеу гипотезасы, әдіснамасы және ғылыми жаңалығы",
            "Отандық және шетелдік әдебиеттерге сыни шолу",
            "Зерттеу материалдары мен эксперименттік әдістер",
            "Алынған сандық және сапалық нәтижелер талдауы",
            "Нәтижелерді талқылау және салыстырмалы интерпретация",
            "Ғылыми қорытындылар мен практикалық ұсынымдар",
        ],
    },
    "lesson": {
        "id": "lesson",
        "title": "📚 Сабақ жоспары (ҚМЖ / Дәріс)",
        "gost_compliant": True,
        "structure": [
            "Оқу мақсаты, күтілетін нәтижелер және бағалау критерийлері",
            "Негізгі ұғымдар мен терминдер глоссарийі",
            "Теориялық бөлім: басты заңдылықтар мен қағидаттар",
            "Көрнекі мысалдар, хронология және практикалық кейстер",
            "Топтық/жеке тапсырмалар мен проблемалық сұрақтар",
            "Сабақты бекіту тестілері мен кері байланыс (Рефлексия)",
            "Қорытынды және үй тапсырмасы (негізгі/қосымша әдебиеттер)",
        ],
    },
    "medical": {
        "id": "medical",
        "title": "🏥 Медициналық баяндама",
        "gost_compliant": True,
        "structure": [
            "Нозологияның өзектілігі және эпидемиологиялық деректер",
            "Этиологиясы, қауіп факторлары және патогенез механизмдері",
            "Клиникалық көрінісі, жіктелуі және симптомдары",
            "Лабораториялық және аспаптық диагностика критерийлері",
            "Дифференциалды диагностика және клиникалық хаттамалар",
            "Емдеу тактикасы: консервативті және инвазивті әдістер",
            "Профилактика, реабилитация және клиникалық болжам",
        ],
    },
    "law": {
        "id": "law",
        "title": "⚖️ Заң жобасы (Құқықтық талдау)",
        "gost_compliant": True,
        "structure": [
            "Құқықтық реттеу пәні және заң жобасының өзектілігі",
            "ҚР Конституциясы мен қолданыстағы заңнамалық базаға шолу",
            "Құқықтық олқылықтар мен коллизияларды талдау",
            "Халықаралық құқықтық тәжірибе және салыстырмалы талдау",
            "Ұсынылатын нормативтік-құқықтық өзгерістер мен толықтырулар",
            "Әлеуметтік-экономикалық және құқықтық салдарлар болжамы",
            "Қорытынды және заңнаманы жетілдіру бойынша нақты ұсыныстар",
        ],
    },
    "marketing": {
        "id": "marketing",
        "title": "📊 Маркетингтік стратегия",
        "gost_compliant": False,
        "structure": [
            "Нарықтық конъюнктура және трендтер талдауы",
            "Мақсатты аудитория сегментациясы (ICP & Buyer Persona)",
            "SWOT және PESTEL стратегиялық талдауы",
            "Бренд позициялау және бірегей құндылық ұсынысы (UVP)",
            "Digital-маркетинг арналары және трафик воронкасы (Funnel)",
            "Медиа-жоспар, бюджет бөлінісі және Unit-экономика (CAC / LTV)",
            "Күтілетін KPI көрсеткіштері және өсім жоспары",
        ],
    },
    "ecology": {
        "id": "ecology",
        "title": "🌍 Экологиялық жоба",
        "gost_compliant": True,
        "structure": [
            "Экологиялық мәселенің өзектілігі және аймақтық сипаттамасы",
            "Қоршаған ортаға антропогендік әсер факторлары мен мониторинг",
            "Ластану деңгейінің сандық көрсеткіштері мен экологиялық тәуекелдер",
            "ҚР Экологиялық кодексі және халықаралық ESG стандарттары",
            "Жасыл технологиялар мен табиғатты қорғау іс-шаралары",
            "Ресурс үнемдеу және экологиялық-экономикалық тиімділік",
            "Тұрақты даму (SDG) бойынша қорытынды ұсыныстар",
        ],
    },
    "storybook": {
        "id": "storybook",
        "title": "🧚 Ертегі-презентация (Тек фотодан)",
        "gost_compliant": False,
        "structure": [
            "Ертегінің басталуы: Басты кейіпкермен және сиқырлы әлеммен танысу",
            "Ғажайып саяхатқа шақыру және алғашқы құпия",
            "Сиқырлы достармен кездесу және жаңа өнер үйрену",
            "Үлкен сынақ: Батылдық пен тапқырлық таныту",
            "Сиқырлы жеңіс және достардың қуанышы",
            "Ертегінің тағылымы: Мейірімділік пен білімнің күші",
        ],
    },
    "kids_edu": {
        "id": "kids_edu",
        "title": "🧸 Балаларға арналған презентация",
        "gost_compliant": False,
        "structure": [
            "Сәлем, жас дос! Тақырыппен қызықты танысу",
            "Бұл қалай жұмыс істейді? Қарапайым әрі қызықты түсіндірме",
            "Таңғажайып деректер мен қызықты мысалдар",
            "Күнделікті өмірдегі пайдасы мен сиқырлы тәжірибелер",
            "Ойлан, тап! Қызықты сұрақтар мен тапсырмалар",
            "Жарайсың! Бүгінгі үйренген басты білімдеріміз",
        ],
    },
}

# Admin Telegram user IDs (comma-separated, e.g. "123456789,987654321")
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS: List[int] = []
if raw_admins:
    for aid in raw_admins.split(","):
        aid_clean = aid.strip()
        if aid_clean.isdigit():
            ADMIN_IDS.append(int(aid_clean))


def is_admin(user_id: int) -> bool:
    """Қолданушы әкімші ме? ADMIN_IDS бос болса — ешкім әкімші емес."""
    return bool(ADMIN_IDS) and user_id in ADMIN_IDS
