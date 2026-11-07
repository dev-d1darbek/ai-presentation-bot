<div align="center">

# 🎯 AI Presentation Bot

**AI көмегімен презентацияларды, қорғау мәтіндерін және слайдтарды автоматты жасайтын Telegram-бот**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Мүмкіндіктер](#-мүмкіндіктер) • [Жылдам бастау](#-жылдам-бастау) • [Конфигурация](#️-конфигурация) • [Docker](#-docker-арқылы-іске-қосу) • [Үлес-қосу](#-үлес-қосу)

</div>

---

## 📋 Мазмұны

- [Жоба туралы](#-жоба-туралы)
- [Мүмкіндіктер](#-мүмкіндіктер)
- [Архитектура](#️-архитектура)
- [Жылдам бастау](#-жылдам-бастау)
- [Конфигурация](#️-конфигурация)
- [Жоба құрылымы](#-жоба-құрылымы)
- [Тестілеу](#-тестілеу)
- [Docker арқылы іске қосу](#-docker-арқылы-іске-қосу)
- [Монетизация және рефералдық жүйе](#-монетизация-және-рефералдық-жүйе)
- [AI провайдерлер](#-ai-провайдерлер)
- [Қауіпсіздік](#-қауіпсіздік)
- [Үлес қосу](#-үлес-қосу)
- [Лицензия](#-лицензия)

---

## 🚀 Жоба туралы

**AI Presentation Bot** — студенттер, мұғалімдер және кәсіби мамандар үшін арналған Telegram-бот. Пайдаланушы тақырыпты және қалаған слайд санын енгізеді — бот жасанды интеллект арқылы құрылымдалған мәтін мен `.pptx` форматында дайын презентация қайтарады.

Жоба **толық өндірістік циклды** қамтиды:

- 🎨 Автоматты слайд генерациясы (`python-pptx` + `Pillow`)
- 💳 Kaspi Pay арқылы төлем және чек валидациясы
- 👥 Рефералдық жүйе және баланс есебі
- 🛠️ Әкімші панелі (`/admin`, `/give`)
- 🗄️ Дерекқор (SQLite / PostgreSQL дайын)

---

## ✨ Мүмкіндіктер

| Категория | Мүмкіндік |
|---|---|
| 🤖 **AI генерация** | DeepSeek, Gemini, OpenAI провайдерлерін қолдау |
| 📊 **Презентация** | Тақырып бойынша N слайдтан тұратын `.pptx` файл |
| 📝 **Мәтін** | Қорғау мәтіні, тезис, сөйлеу сценарийі |
| 💰 **Монетизация** | Баланс, тарифтер, VIP мүшелік |
| 💳 **Төлем** | Kaspi Pay чектерін автоматты тексеру |
| 👥 **Реферал** | Арнайы сілтеме, бонус есептеу |
| 🛡️ **Әкімші** | Статистика, қолмен баланс/VIP беру |
| 🐳 **Deploy** | Docker + docker-compose, бір командамен іске қосу |
| 🧪 **Тесттер** | `tests/test_system.py` — жүйелік тексеру |

---

## 🏗️ Архитектура

```text
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  Telegram    │──────▶│   aiogram    │──────▶│  Handlers    │
│   Client     │◀──────│   Router     │◀──────│  (commands)  │
└──────────────┘       └──────────────┘       └──────┬───────┘
                                                     │
                       ┌─────────────────────────────┼─────────────────────┐
                       ▼                             ▼                     ▼
                ┌──────────────┐              ┌──────────────┐      ┌──────────────┐
                │  AI Service  │              │ Presentation │      │   Payment    │
                │ (DeepSeek /  │              │   Builder    │      │   Service    │
                │  Gemini /    │              │ (python-pptx)│      │  (Kaspi)     │
                │  OpenAI)     │              └──────────────┘      └──────┬───────┘
                └──────────────┘                                          │
                       │                                                  ▼
                       ▼                                          ┌──────────────┐
                ┌──────────────┐                                  │   Database   │
                │   Storage    │                                  │ (SQLite/PG)  │
                │  (files/)    │                                  └──────────────┘
                └──────────────┘
```

---

## 🚀 Жылдам бастау

### 1. Репозиторийді клондау

```bash
git clone https://github.com/dev-d1darbek/ai_presentation_bot.git
cd ai_presentation_bot
```

### 2. Виртуалды орта жасау

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Тәуелділіктерді орнату

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. `.env` файлын дайындау

```bash
cp .env.example .env
# .env файлын редакторда ашып, мәндерді толтырыңыз
```

### 5. Ботты іске қосу

```bash
python bot.py
```

Telegram-да ботыңызды ашып, `/start` командасын жіберіңіз.

---

## ⚙️ Конфигурация

Барлық құпия параметрлер `.env` файлында сақталады. Үлгі — `.env.example`.

| Айнымалы | Міндетті | Сипаттама |
|---|:---:|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | [@BotFather](https://t.me/BotFather) арқылы алынатын токен |
| `ADMIN_IDS` | ✅ | Әкімшілердің Telegram ID-і (үтір арқылы) |
| `DEEPSEEK_API_KEY` | ⚠️ | DeepSeek кілті (кемінде бір AI кілті міндетті) |
| `GEMINI_API_KEY` | ⚠️ | Google Gemini кілті |
| `OPENAI_API_KEY` | ⚠️ | OpenAI кілті |
| `AI_PROVIDER` | ❌ | `deepseek` \| `gemini` \| `openai` (әдепкі: `deepseek`) |
| `KASPI_PAY_URL` | ✅ | Kaspi Pay төлем сілтемесі |
| `KASPI_BIN` | ✅ | Kaspi чек тексеру үшін БСН |
| `KASPI_PHONE` | ✅ | Kaspi телефоны |
| `KASPI_RECIPIENT_NAME` | ✅ | Алушының аты-жөні |
| `DATABASE_URL` | ❌ | Әдепкі: `sqlite:///data/bot.db` |
| `LOG_LEVEL` | ❌ | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

> ⚠️ `.env` файлын **ешқашан** Git-ке жібермеңіз. Ол `.gitignore`-та.

---

## 📁 Жоба құрылымы

```text
ai_presentation_bot/
├── bot.py                  # Кіру нүктесі
├── config.py               # Pydantic Settings арқылы конфигурация
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CHANGELOG.md
├── SECURITY.md
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── handlers/               # aiogram router-лер
│   ├── start.py
│   ├── presentation.py
│   ├── payment.py
│   └── admin.py
├── services/
│   ├── ai_service.py
│   ├── presentation_builder.py
│   └── payment_service.py
├── database/
│   ├── models.py
│   └── repository.py
├── keyboards/
├── middlewares/
├── utils/
├── tests/
│   └── test_system.py
└── data/                   # SQLite, файлдар (gitignore-та)
```

---

## 🧪 Тестілеу

```bash
# Барлық тесттер
pytest -v

# Жүйелік тест (README-де көрсетілген)
python tests/test_system.py

# Линтер
ruff check .
black --check .
```

---

## 🐳 Docker арқылы іске қосу

```bash
# 1. .env дайындау
cp .env.example .env

# 2. Контейнерді іске қосу
docker compose up -d --build

# 3. Логтарды тексеру
docker compose logs -f bot

# 4. Тоқтату
docker compose down
```

`docker-compose.yml` `.env`-ті автоматты түрде оқиды, ал `restart: unless-stopped` саясаты контейнерді қайта іске қосады.

---

## 💰 Монетизация және рефералдық жүйе

- **Баланс** — әр пайдаланушының жеке есепшоты (`users.balance`)
- **Тарифтер** — 1 презентация, пакет, VIP (шексіз)
- **Kaspi Pay** — чек суреті жіберіледі, `payment_service` оны `KASPI_BIN` / `KASPI_PHONE` / `KASPI_RECIPIENT_NAME` арқылы тексереді
- **Реферал** — `?start=ref_<id>` арқылы шақырылған пайдаланушы үшін бонус
- **Әкімші** — `/give <user_id> <amount>` және `/vip <user_id>` арқылы қолмен беру

---

## 🤖 AI провайдерлер

Бот бірнеше AI провайдерін қолдайды, `.env`-те біреуін таңдаңыз:

| Провайдер | Артықшылығы | Кілт |
|---|---|---|
| **DeepSeek** | Арзан, жылдам | `DEEPSEEK_API_KEY` |
| **Gemini** | Тегін лимит | `GEMINI_API_KEY` |
| **OpenAI** | Ең сапалы | `OPENAI_API_KEY` |

Провайдерді ауыстыру үшін `AI_PROVIDER` мәнін өзгертіп, ботты қайта іске қосыңыз.

---

## 🔐 Қауіпсіздік

- Барлық құпия кілттер тек `.env` файлында
- SQL-инъекцияға қарсы параметрленген сұраныстар
- Чектердің криптографиялық тексерілуі
- Толығырақ — [SECURITY.md](SECURITY.md)

Егер осалдық тапсаңыз — ашық issue ашпаңыз, [SECURITY.md](SECURITY.md)-дегі нұсқаулық бойынша хабарласыңыз.

---

## 🤝 Үлес қосу

Жобаға үлес қосуға қуаныштымыз! Нұсқаулық — [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
# Fork → clone → branch
git checkout -b feature/my-feature

# Өзгерістер
git commit -m "feat: my new feature"
git push origin feature/my-feature

# Pull Request ашу
```

Commit хабарламалары [Conventional Commits](https://www.conventionalcommits.org/) стандартына сай болуы керек.

---

## 📄 Лицензия

Бұл жоба **MIT License** аясында таратылады — толығырақ [LICENSE](LICENSE) файлында.

---

<div align="center">

**⭐ Жоба ұнаса — жұлдызша қалдырыңыз!**

Made with ❤️ by [@dev-d1darbek](https://github.com/dev-d1darbek)

</div>
