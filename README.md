# ✨ SlideAI KZ — AI Presentation Telegram Bot

&lt;div align=&quot;center&quot;&gt;






**Кәсіби `.PPTX` және `.PDF` презентацияларды жасанды интеллект арқылы лезде жасайтын коммерциялық Telegram-бот.**  
Қазақ, орыс және ағылшын тілдерінде толық қызмет көрсетеді.

[Мүмкіндіктер](#-негізгі-мүмкіндіктер) • [Архитектура](#-жоба-құрылымы) • [Орнату](#-орнату-және-іске-қосу) • [Админ панель](#-админ-панель) • [Автор](#-автор)

&lt;/div&gt;

---

## 🚀 Негізгі мүмкіндіктер

- **🌐 3 тілді интерфейс:** Бот толықтай `🇰🇿 Қазақша`, `🇷🇺 Русский` және `🇺🇸 English` тілдерінде жұмыс істейді.
- **🎓 9 мамандандырылған бағыт:** Академиялық, Ғылыми баяндама, Диплом қорғау, Бизнес-жоспар, Сабақ жоспары, Медицина, Заң жобасы, Маркетинг, Экология.
- **🖼 2 таза генерация режимі:** `🚫 Фотосыз` (минималистік аналитикалық стиль) және `🖼 Фотомен` (автоматты сурет іріктеу + кэштеу).
- **📐 Zero-Overlap `.PPTX` + `.PDF` қозғалтқышы:** Мәтіндердің бірінің үстіне бірі шығып кетуін болдырмайтын динамикалық типография және телефоннан көруге ыңғайлы HD `.PDF` экспорты.
- **💳 Қос төлем жүйесі:**
  - **Kaspi Pay:** PDF фискалдық чектегі QR-кодты автоматты тексеру (`httpx` + `pypdf` / `pypdfium2`).
  - **Telegram Stars (`⭐️ XTR`):** Telegram-ның ішкі жүйесі арқылы лезде төлеу.
- **🧹 Таза чат (Auto Chat Cleanup):** Мәзір мен шебер (wizard) қадамдарындағы ескі хаттарды автоматты түрде өшіріп, чатта тек дайын `.PDF` және `.PPTX` файлдарын қалдырады.
- **📂 Менің жобаларым:** Жасалған барлық презентациялар сақталады және 1 батырмамен қайта жүктеледі.
- **🎟 Промокодтар & 2 жақты қолдау:** Бір реттік промокодтар жүйесі (`BONUS2025`, `ALASH2025`, т.б.) және бот ішіндегі админ-қолдау чаты.

---

## ⚙️ Админ панель (`/admin`)

- **💰 Динамикалық баға баптауы:** 1 презентация бағасын (`₸`) және **Telegram Stars (`⭐️`)** бағасын админ панельден лезде өзгерту (бүкіл ботта автоматты жаңарады).
- **📊 Аналитика:** 7 және 30 күндік табыс пен генерация графиктері (PNG), воронка (Funnel) және когорта талдауы.
- **👥 Қолданушыларды басқару:** Іздеу, фильтрлеу, баланс қосу/алу (`+1`, `+5`, `+10`, `-1`), жобаларын өшіру және тікелей жауап жазу.
- **🛡 Қауіпсіздік & Мониторинг:** Қайталанған чектерді бұғаттау (Anti-Fraud), Redis/SQLite сурет кэші, Sentry және Prometheus метрикалары.

---

## 📁 Жоба құрылымы

```text
ai_presentation_bot/
├── bot.py                        # Негізгі іске қосу файлы, хендлерлер және FSM
├── config.py                     # Баптаулар, тарифтер, промокодтар және орта айнымалылары
├── requirements.txt              # Python тәуелділіктері
├── Dockerfile                    # Docker контейнері
├── docker-compose.yml            # Bot + Redis + PostgreSQL стекі
├── app/
│   ├── ai/
│   │   ├── client.py             # DeepSeek / Gemini / OpenAI AI клиенттері
│   │   ├── prompts.py            # Жоғары сапалы жүйелік промпттар
│   │   ├── parser.py             # JSON парсер және тазалау
│   │   └── fallback.py           # Офлайн резервтік генератор
│   ├── bot/
│   │   ├── i18n.py               # 3 тілді локализация (kk / ru / en)
│   │   ├── session.py            # Redis + SQLite сессия менеджері
│   │   ├── service.py            # Бизнес-логика және аналитика графиктері
│   │   ├── handlers/commands.py  # Мәзір және команда мәтіндері
│   │   └── keyboards/            # Inline және Reply пернетақталар
│   ├── core/
│   │   ├── db.py                 # SQLite/PostgreSQL дерекқор қабаты
│   │   ├── verifier.py           # Kaspi PDF фискалдық чек тексеруші
│   │   ├── image_search.py       # Сурет іздеу және кэштеу
│   │   ├── themes.py             # 35+ дизайн тақырыптары
│   │   └── monitoring.py         # Sentry & Prometheus мониторингі
│   └── pptx_generator/
│       ├── engine.py             # PPTX генераторы (Zero-Overlap)
│       └── pdf_engine.py         # HD PDF генераторы
└── tests/
    └── test_system.py            # Автоматтандырылған жүйелік тесттер
```

---

## 🛠 Орнату және іске қосу

### 1. Репозиторийді клондау және ортаны дайындау

```bash
git clone https://github.com/dev-d1darbek/ai_presentation_bot.git
cd ai_presentation_bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. `.env` файлын баптау

Жоба түбірінде `.env` файлын құрып, қажетті кілттерді енгізіңіз:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789
ADMIN_CONTACT=dev_d1darbek

DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

KASPI_PAY_URL=https://pay.kaspi.kz/pay/your_link
STARS_PRICE_XTR=50
WELCOME_FREE_CREDITS=0

# Қосымша (Production үшін):
# REDIS_URL=redis://localhost:6379/0
# DATABASE_URL=postgresql://user:pass@localhost:5432/slideai
```

### 3. Тесттерді тексеру және ботты қосу

```bash
python tests/test_system.py
python bot.py
```

### 4. Docker арқылы іске қосу

```bash
docker-compose up -d --build
```

---

## 👨‍💻 Автор

**D1darbek**  
- GitHub: [@dev-d1darbek](https://github.com/dev-d1darbek/)
- Telegram: [@dev\_d1darbek](https://www.google.com/search?q=https://t.me/dev_d1darbek)

---

<div align="center"> <sub>Жоба ұнаса, GitHub репозиторийге ⭐️ жұлдызша басуды ұмытпаңыз!</sub> </div>

