"""
Intelligent Multi-Language (Қазақша / Русский / English) & Template-Aware Fallback Presentation Generator.
Supports:
- 3 Languages: 'қазақша', 'русский', 'english'
- Template Library: 'diploma', 'business', 'scientific', 'lesson', 'medical', 'law', 'marketing', 'ecology', 'standard'
- Rich, detailed multi-sentence paragraphs and 4 comprehensive bullet points per slide (especially for no-photo mode)
- Document-to-Slide chunking when document_text is provided
"""
import re
import time
import random
from typing import Optional, List
import config
from app.core.types import (
    PresentationData,
    SlideContent,
    SlideStat,
    TimelineItem,
    SlideComparison,
    ComparisonEntity,
    SlideQuote,
    QualityScore,
)
from app.core.themes import THEMES_REGISTRY, detect_best_theme_for_topic


def _generate_from_document_text(
    topic: str,
    document_text: str,
    slide_count: int,
    theme_id: str,
    language: str = "қазақша",
    template_id: str = "standard",
    with_photos: bool = False,
    persona_style: str = "academic_universal",
    is_storybook: bool = False,
    child_name: Optional[str] = None,
    child_avatar_desc: Optional[str] = None,
) -> PresentationData:
    """
    Splits an uploaded document's text into structured, information-rich slides when LLM APIs are offline.
    """
    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", document_text)
        if len(p.strip()) > 30
    ]
    if not paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", document_text) if len(s.strip()) > 15]
        paragraphs = sentences or [document_text[:650]]

    slides: List[SlideContent] = []
    max_para_chars = 360 if with_photos else 580
    max_bullet_chars = 150 if with_photos else 230

    intro_text = (
        " ".join(paragraphs[:2])[:max_para_chars]
        if paragraphs
        else f"«{topic}» тақырыбы бойынша негізгі теориялық қағидаттар, аналитикалық деректер мен практикалық тұжырымдар жүйеленіп ұсынылған."
    )
    cover_pts = [p[:max_bullet_chars] for p in paragraphs[1:5]]
    while len(cover_pts) < 3:
        cover_pts.append(
            "Құжаттағы іргелі теориялық негіздер, статистикалық көрсеткіштер мен тәжірибелік тұжырымдар толықтай құрылымдалды."
        )

    slides.append(
        SlideContent(
            slide_number=1,
            type="cover",
            title=topic,
            subtitle="Құжат мазмұны бойынша тереңдетілген аналитикалық презентация",
            content=intro_text,
            key_points=cover_pts[:3],
            image_query=f"{topic} cover concept" if with_photos else None,
        )
    )

    inner_count = max(slide_count - 2, 1)
    body_paras = paragraphs[1:] if len(paragraphs) > 1 else paragraphs

    for i in range(inner_count):
        s_num = i + 2
        idx_start = int((i / inner_count) * len(body_paras))
        chunk = body_paras[idx_start : idx_start + 5] or body_paras[:3]
        main_para = " ".join(chunk[:2])[:max_para_chars] if chunk else intro_text

        sents: List[str] = []
        for c in chunk[1:]:
            for s in re.split(r"(?<=[.!?])\s+", c):
                if 20 < len(s.strip()) <= max_bullet_chars:
                    sents.append(s.strip())
        if len(sents) < 4:
            for s in re.split(r"(?<=[.!?])\s+", main_para):
                if 20 < len(s.strip()) <= max_bullet_chars and s.strip() not in sents:
                    sents.append(s.strip())
        while len(sents) < 4:
            sents.append(
                "Бұл бөлімде негізгі себеп-салдарлық байланыстар, қолданбалы тетіктер мен нақты көрсеткіштер жан-жақты талданады."
            )

        first_line = chunk[0].split(".")[0].strip()[:68]
        slide_title = first_line if 6 <= len(first_line) <= 65 else f"{topic}: {i + 1}-аналитикалық бөлім"
        l_type = ("photo_split" if i % 2 == 0 else "photo_magazine") if with_photos else "split_screen"

        slides.append(
            SlideContent(
                slide_number=s_num,
                type=l_type,
                title=slide_title,
                subtitle="Құрылымдық талдау, негізгі деректер және практикалық маңызы",
                content=main_para,
                key_points=sents[:4],
                image_query=f"{topic} {slide_title}" if with_photos else None,
            )
        )

    last_para = " ".join(paragraphs[-2:])[:max_para_chars] if paragraphs else intro_text
    slides.append(
        SlideContent(
            slide_number=len(slides) + 1,
            type="conclusion",
            title="Қорытынды тұжырымдар мен тәжірибелік ұсынымдар",
            subtitle="Зерттеу нәтижелерінің жиынтық қорытындысы",
            content=last_para,
            key_points=cover_pts[:3],
            image_query=f"{topic} summary" if with_photos else None,
        )
    )

    return PresentationData(
        id=f"pres_doc_{int(time.time())}_{random.randint(1000, 9999)}",
        topic=topic,
        title_presentation=topic,
        design_id=theme_id,
        language=language,
        template_id=template_id,
        persona_style=persona_style,
        is_storybook=is_storybook,
        child_name=child_name,
        with_photos=with_photos,
        slide_count=len(slides),
        slides=slides,
        plan_summary=[f"{s.slide_number}-слайд: {s.title}" for s in slides],
        quality_score=QualityScore(),
        createdAt=str(time.time()),
    )


def generate_intelligent_fallback(
    topic: str,
    slide_count: int = 15,
    theme_id: Optional[str] = None,
    document_text: Optional[str] = None,
    language: str = "қазақша",
    template_id: str = "standard",
    with_photos: bool = False,
    persona_style: str = "academic_universal",
    is_storybook: bool = False,
    child_name: Optional[str] = None,
    child_avatar_desc: Optional[str] = None,
) -> PresentationData:
    """
    Generates rich, deeply informative presentation data in Kazakh, Russian, or English,
    honoring template_id structure and photo/no-photo layouts.
    """
    chosen_theme = (
        THEMES_REGISTRY[theme_id]
        if theme_id and theme_id in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic, with_photos=with_photos)
    )

    lang = language.lower().strip()
    if is_storybook or template_id == "storybook":
        hero = (child_name or topic.split()[0] or "Айсұлтан").strip()
        clean_story_topic = topic.replace(f"{hero}:", "").strip() or topic
        avatar_prefix = (
            child_avatar_desc.strip()
            if child_avatar_desc and child_avatar_desc.strip()
            else f"7-year-old Kazakh child named {hero}, round face, short dark hair, expressive brown eyes, warm smile"
        )
        story_slides: List[SlideContent] = []
        if lang == "русский":
            chapters = [
                (f"Волшебное начало: {hero} и «{clean_story_topic}»", f"Давным-давно в уютном и солнечном городе жил добрый и любознательный ребенок по имени {hero}. Однажды вечером перед {hero} открылась сияющая золотая книга, ведущая в мир «{clean_story_topic}».", "opening a glowing golden magical book in a cozy bedroom with sparkles"),
                (f"Шаг в сказочный мир", f"Сделав смелый шаг вперед, {hero} оказался на цветущей поляне, где деревья шептали древние тайны, а в небе летали светящиеся бабочки, указывая путь к чудесам.", "stepping into an enchanted glowing meadow with magical butterflies"),
                (f"Встреча с мудрым проводником", f"Навстречу {hero} вылетела золотая птица Самрук и подарила волшебный компас, который светится ярче, когда сердце наполнено добротой и смелостью.", "holding a glowing golden compass next to a friendly golden phoenix bird"),
                (f"Тайна хрустального моста", f"Впереди раскинулась быстрая звездная река. {hero} улыбнулся, вспомнил добрые слова и смело ступил на хрустальный мост, который засиял всеми цветами радуги.", "crossing a sparkling crystal rainbow bridge over a starry river"),
                (f"Верные сказочные друзья", f"В волшебном лесу {hero} познакомился с веселыми лесными жителями. Вместе они решили разгадать главную загадку страны «{clean_story_topic}».", "laughing with cute woodland animal friends in a sunlit magical forest"),
                (f"Загадка древней башни", f"У ворот серебряной башни стоял каменный страж и задал непростую загадку. {hero} проявил смекалку и дал верный ответ, после чего ворота мягко распахнулись.", "solving a glowing puzzle at the gates of a silver fairy-tale tower"),
                (f"Свет доброго сердца", f"Когда на долину опустился густой туман, {hero} поднял волшебный фонарь доброты. Его теплый свет мгновенно рассеял темноту и согрел всех вокруг.", "holding a warm glowing lantern that lights up a misty magical valley"),
                (f"Праздник в сказочном королевстве", f"Все жители волшебной страны радостно встретили {hero}! В честь юного героя устроили большой праздник с музыкой, звездами и сладкими угощениями.", "celebrating at a grand fairy-tale festival with lanterns and confetti"),
                (f"Счастливое возвращение {hero}", f"Поблагодарив новых друзей, {hero} вернулся домой с радостной улыбкой. Теперь {hero} точно знает: доброта, дружба и смелость творят настоящие чудеса!", "smiling happily back home holding a glowing star souvenir"),
            ]
        else:
            chapters = [
                (f"Ертегінің басталуы: {hero} және «{clean_story_topic}»", f"Ерте-ерте ертеде, күлімдеген шуақты қалада мейірімді әрі білімге құштар {hero} есімді бала өмір сүріпті. Бір күні {hero} «{clean_story_topic}» атты ғажайып әлемге апаратын алтын кілт тауып алды.", "holding a glowing golden key in front of a magical shimmering portal"),
                (f"Сиқырлы әлемге алғашқы қадам", f"{hero} алтын есікті ашқан сәтте, айналасы түрлі-түсті гүлдерге, жарқыраған жұлдыздарға және ән салған сиқырлы құстарға толы таңғажайып өлкеге тап болды.", "walking into a vibrant enchanted wonderland with glowing flowers and birds"),
                (f"Алтын Самұрықпен кездесу", f"Сол кезде аспаннан қанаттары күндей жарқыраған мейірімді Алтын Самұрық түсіп, {hero}-ға жол көрсететін сиқырлы жұлдызды сыйға тартты.", "meeting a friendly glowing golden Samruk bird under a starry sky"),
                (f"Кемпірқосақ көпірінен өту", f"Алда мөлдір бұлақ пен биік шыңдар тұрды. {hero} еш қорықпастан кемпірқосақ көпіріне қадам басты, ал көпір батыл баланың астында жарқырап жол ашты.", "walking across a glowing rainbow bridge above crystal waterfalls"),
                (f"Адал достардың көмегі", f"Саяхат барысында {hero} ормандағы сүйкімді әрі тапқыр достармен танысты. Олар бірігіп «{clean_story_topic}» елінің ең үлкен құпиясын ашуға аттанды.", "smiling with cute magical forest friends on an adventure trail"),
                (f"Дана қамалдың жұмбағы", f"Күміс қамалдың алдында сиқырлы жұмбақ жазылған екен. {hero} өзінің зеректігі мен ақылдылығының арқасында жұмбақтың шешімін бірден тапты!", "unlocking a sparkling silver castle gate with wisdom and joy"),
                (f"Мейірімді жүректің шуағы", f"Сиқырлы баққа көлеңке түскенде, {hero} қолындағы жұлдызды жоғары көтерді. Оның мейірімді жүрегінен тараған жылу бүкіл бақты қайтадан гүлдендірді.", "holding a shining star that blooms magical flowers all around"),
                (f"Ғажайып жеңіс мерекесі", f"Барлық ертегі кейіпкерлері {hero}-ның батылдығы мен мейірімділігіне тәнті болып, үлкен мереке ұйымдастырды. Аспанда алтын отшашулар жарқырады!", "celebrating with fairy-tale friends under golden fireworks"),
                (f"Бақытты оралу: Жарайсың, {hero}!", f"Осылайша {hero} сиқырлы саяхатын сәтті аяқтап, үйіне зор қуанышпен оралды. {hero} нағыз батырлық пен мейірімділік әрқашан жеңіске жетелейтінін түсінді!", "waving happily at sunset with a warm heroic smile"),
            ]
        for idx_c in range(slide_count):
            if idx_c == slide_count - 1 and slide_count >= 3:
                c_title, c_text, c_scene = chapters[-1]
            else:
                c_title, c_text, c_scene = chapters[idx_c % (len(chapters) - 1)]
            story_slides.append(
                SlideContent(
                    slide_number=idx_c + 1,
                    type="storybook_full_photo",
                    title=c_title,
                    subtitle="",
                    content=c_text,
                    key_points=[],
                    image_query=f"{avatar_prefix}, {c_scene}",
                )
            )
        return PresentationData(
            id=f"story_{int(time.time())}_{random.randint(1000, 9999)}",
            topic=topic,
            title_presentation=f"Ертегі: {hero} және {topic}",
            design_id=chosen_theme.id,
            language=language,
            template_id="storybook",
            persona_style="kids_fairy",
            is_storybook=True,
            child_name=hero,
            child_avatar_desc=avatar_prefix,
            with_photos=True,
            image_source="gpt-image-2",
            slide_count=len(story_slides),
            slides=story_slides,
            plan_summary=[f"{s.slide_number}-слайд: {s.title}" for s in story_slides],
            quality_score=QualityScore(),
            createdAt=str(time.time()),
        )

    if document_text and len(document_text.strip()) > 40:
        return _generate_from_document_text(
            topic, document_text, slide_count, chosen_theme.id,
            language=language, template_id=template_id, with_photos=with_photos,
        )

    lang = language.lower().strip()
    tmpl = config.TEMPLATE_LIBRARY.get(template_id, config.TEMPLATE_LIBRARY["standard"])
    tmpl_titles: List[str] = tmpl.get("structure") or []

    t_lower = topic.lower()
    is_two_person = bool(
        re.search(
            r"\b(?:2\s*адам|екі\s*адам|салыстыру|қарсы\s*қою|vs|сравнение|против)\b"
            r"|\bжәне\b.*\bсалыстыр"
            r"|\bмен\b",
            t_lower,
        )
    )

    slides: List[SlideContent] = []

    if lang == "русский":
        cover_title = f"{topic}: Комплексный научно-практический и аналитический обзор"
        cover_sub = f"Фундаментальные основы, ключевые показатели и перспективы развития ({tmpl['title']})"
        cover_content = (
            f"Данное исследование представляет собой глубокий системный анализ темы «{topic}», охватывающий "
            f"теоретико-методологическую базу, историческую эволюцию, современные количественные индикаторы и "
            f"прикладные механизмы реализации. Особое внимание уделяется причинно-следственным связям, "
            f"институциональным факторам эффективности и разработке научно обоснованных практических рекомендаций."
        )
        cover_pts = [
            "Систематизация теоретико-методологических подходов и определение ключевого понятийного аппарата исследования.",
            "Анализ актуальных статистических показателей, динамики развития и международного опыта внедрения.",
            "Формулирование прикладных решений, оценка социально-экономического эффекта и перспектив масштабирования.",
        ]
    elif lang == "english":
        cover_title = f"{topic}: Comprehensive Analytical & Strategic Research"
        cover_sub = f"Foundational Theory, Empirical Metrics & Implementation Roadmap ({tmpl['title']})"
        cover_content = (
            f"This research delivers a rigorous, multidimensional examination of '{topic}', synthesizing foundational "
            f"theoretical frameworks, historical milestones, quantitative market benchmarks, and real-world operational "
            f"strategies. By evaluating structural drivers and causal mechanisms, the study establishes actionable "
            f"recommendations for sustainable institutional and technological advancement."
        )
        cover_pts = [
            "Comprehensive synthesis of foundational theories, core paradigms, and methodological frameworks.",
            "Quantitative evaluation of growth dynamics, empirical performance metrics, and global benchmarks.",
            "Actionable implementation roadmap, risk mitigation strategies, and long-term impact projections.",
        ]
    else:
        cover_title = f"{topic}: Кешенді ғылыми-тәжірибелік және аналитикалық талдау"
        cover_sub = f"Теориялық-әдіснамалық негіздері, даму динамикасы және қолданбалы маңызы ({tmpl['title']})"
        cover_content = (
            f"Бұл ғылыми-аналитикалық жұмыста «{topic}» тақырыбының іргелі теориялық негіздері, тарихи қалыптасу "
            f"кезеңдері, қазіргі сандық-статистикалық көрсеткіштері мен практикалық қолданылу тетіктері жан-жақты "
            f"зерделенеді. Зерттеу барысында саланың өзекті мәселелері, ішкі және сыртқы даму факторлары, сондай-ақ "
            f"тиімділікті арттырудың нақты ғылыми-тәжірибелік жолдары жүйелі түрде негізделген."
        )
        cover_pts = [
            "Зерттеу нысаны мен пәнін айқындау, негізгі ұғымдық-терминологиялық аппаратты ғылыми тұрғыдан жүйелеу.",
            "Саланың қазіргі даму динамикасын нақты статистикалық деректер, салыстырмалы көрсеткіштер арқылы бағалау.",
            "Қолданбалы шешімдерді енгізудің экономикалық-әлеуметтік тиімділігі мен болашақ даму бағыттарын айқындау.",
        ]

    # Slide 1: Cover
    slides.append(
        SlideContent(
            slide_number=1,
            type="photo_hero" if with_photos else "cover",
            title=cover_title,
            subtitle=cover_sub,
            content=cover_content,
            key_points=cover_pts,
            image_query=f"{topic} professional modern cover" if with_photos else None,
        )
    )

    # Slide 2: Context & Scope
    s2_title = (
        tmpl_titles[0]
        if len(tmpl_titles) > 0
        else (
            "Актуальность темы, объект и методология исследования"
            if lang == "русский"
            else ("Relevance, Theoretical Scope & Research Methodology" if lang == "english" else "Тақырыптың өзектілігі, зерттеу аясы және әдіснамалық негіздері")
        )
    )
    slides.append(
        SlideContent(
            slide_number=2,
            type="photo_split" if with_photos else "split_screen",
            title=s2_title,
            subtitle="Ғылыми-теориялық маңызы, зерттеу объектісі және негізгі алғышарттар" if lang == "қазақша" else ("Научно-теоретическая и практическая значимость направления" if lang == "русский" else "Scientific Significance, Core Objectives & Analytical Scope"),
            content=(
                f"«{topic}» мәселесін кешенді түрде зерттеу қазіргі ғылыми-технологиялық және әлеуметтік-экономикалық "
                f"трансформация жағдайында ерекше өзектілікке ие. Бұл бағыттың іргелі заңдылықтарын терең түсіну "
                f"басқару шешімдерінің сапасын арттырып, ресурстарды тиімді бөлуге және ұзақ мерзімді тұрақты даму "
                f"модельдерін қалыптастыруға тікелей мүмкіндік береді. Зерттеуде жүйелік, салыстырмалы және "
                f"статистикалық талдау әдістері кеңінен қолданылады."
                if lang == "қазақша"
                else (
                    f"Комплексное изучение темы «{topic}» приобретает особую значимость в условиях современной технологической и социально-экономической трансформации. Глубокое понимание закономерностей данной сферы позволяет оптимизировать управленческие процессы, повысить точность прогнозирования и сформировать устойчивую модель развития на основе системного и сравнительно-аналитического подходов."
                    if lang == "русский"
                    else f"A comprehensive investigation of '{topic}' is critical amid rapid technological and socioeconomic transformation. Understanding its underlying mechanisms enables evidence-based decision-making, optimal resource allocation, and scalable institutional growth supported by empirical and comparative analysis."
                )
            ),
            key_points=[
                "Қазіргі кезеңдегі жоғары сұраныс пен саланың қарқынды даму динамикасы отандық және халықаралық эмпирикалық зерттеулермен толық дәлелденген." if lang == "қазақша" else ("Высокий уровень востребованности и динамики развития подтвержден отечественными и международными эмпирическими исследованиями." if lang == "русский" else "High demand and rapid growth dynamics are thoroughly validated by domestic and international empirical studies."),
                "Классикалық теориялық база мен заманауи инновациялық тәжірибені өзара ұштастыру жүйенің жалпы тиімділігін бірнеше есеге арттырады." if lang == "қазақша" else ("Интеграция фундаментальной теоретической базы и передового международного опыта кратно повышает общую результативность системы." if lang == "русский" else "Integrating classical theoretical foundations with modern international best practices multiplies overall operational impact."),
                "Құрылымдық сын-қатерлер мен шектеулерді ерте сатыда анықтау ықтимал тәуекелдерді төмендетіп, тұрақты сапалық нәтижеге жол ашады." if lang == "қазақша" else ("Своевременная диагностика структурных вызовов минимизирует операционные риски и обеспечивает предсказуемый результат." if lang == "русский" else "Early identification of structural bottlenecks mitigates operational risks and ensures sustainable long-term outcomes."),
                "Пәнаралық және жүйелі әдіснаманы қолдану салааралық интеграцияны күшейтіп, практикалық енгізу процесін жеделдетеді." if lang == "қазақша" else ("Применение междисциплинарной методологии усиливает синергию между ключевыми компонентами и ускоряет практическое внедрение." if lang == "русский" else "Applying a systematic interdisciplinary methodology strengthens cross-functional synergy and accelerates practical deployment."),
            ],
            image_query=f"{topic} research analysis" if with_photos else None,
        )
    )

    # Slide 3: Two-person comparison or Core Paradigm
    s3_title = tmpl_titles[1] if len(tmpl_titles) > 1 else ("Екі негізгі тәсілдің салыстырмалы-аналитикалық талдауы" if is_two_person else "Негізгі тұжырымдамалық парадигма және даму формуласы")
    if is_two_person:
        slides.append(
            SlideContent(
                slide_number=3,
                type="two_person_comparison",
                title=s3_title,
                subtitle="Методологиялық ұстанымдар, құрылымдық ерекшеліктер және практикалық үлес",
                content=(
                    f"«{topic}» аясындағы қос бағыттың теориялық және қолданбалы ұстанымдары өз кезеңінің ең күрделі "
                    f"мәселелерін шешуге бағытталған. Салыстырмалы талдау олардың әдіснамалық айырмашылықтарын, "
                    f"артықшылықтары мен шектеулерін айқындап, қазіргі гибридті модельдердің қалыптасу негізін көрсетеді."
                ),
                key_points=[
                    "Идеялық сабақтастық пен әдіснамалық ерекшеліктердің жүйелі салыстырмасы",
                    "Саланың дамуына қосқан нақты теориялық және практикалық үлесі",
                    "Қазіргі заманғы интеграцияланған жүйелер үшін қолданбалы маңызы",
                ],
                comparison=SlideComparison(
                    entityA=ComparisonEntity(
                        name="Бірінші бағыт (Дәстүрлі-құрылымдық мектеп)",
                        points=[
                            "Қатаң логикалық ережелерге, нормативтік стандарттарға және сарапшылық білім базасына негізделеді.",
                            "Алдын ала нақтыланған, тұрақты жағдайларда жоғары дәлдік пен толық түсіндірілуді қамтамасыз етеді.",
                            "Құрылымдық тұрақтылығы жоғары болғанымен, өзгермелі ортаға бейімделуі қосымша ресурстарды талап етеді.",
                            "Іргелі теориялық аппаратты қалыптастыруда және базалық модельдерді құруда шешуші рөл атқарды.",
                        ],
                    ),
                    entityB=ComparisonEntity(
                        name="Екінші бағыт (Инновациялық-динамикалық мектеп)",
                        points=[
                            "Эмпирикалық деректерді өңдеуге, икемді алгоритмдерге және өздігінен бейімделу тетіктеріне сүйенеді.",
                            "Үлкен көлемді, құрылымсыз ақпаратты талдауда және күрделі заңдылықтарды табуда жоғары нәтиже береді.",
                            "Технологиялық өзгерістерге жылдам бейімделіп, жаңа қолданбалы шешімдерді генерациялауға мүмкіндік береді.",
                            "Заманауи цифрлық экожүйелер мен жоғары өнімді автоматтандырылған кешендердің негізін құрайды.",
                        ],
                    ),
                ),
                image_query=f"{topic} comparison" if with_photos else None,
            )
        )
    else:
        slides.append(
            SlideContent(
                slide_number=3,
                type="photo_magazine" if with_photos else "big_typography",
                title=s3_title,
                subtitle="Теориялық-әдіснамалық синтез және стратегиялық басымдықтар",
                content=(
                    f"«{topic} саласындағы тұрақты сапалық серпіліс — терең ғылыми-аналитикалық негіздемені, "
                    f"дәл есептелген ресурстық жоспарлауды және озық инновациялық технологияларды біртұтас жүйеге "
                    f"біріктірудің тікелей нәтижесі болып табылады.»"
                ),
                key_points=[
                    "Стратегиялық мақсаттарды нақты өлшенетін сандық және сапалық индикаторлармен (KPI) бекіту жүйенің ұзақ мерзімді тұрақтылығын қамтамасыз етеді.",
                    "Инновациялық әдістер мен цифрлық құралдарды кезең-кезеңімен енгізу операциялық шығындарды азайтып, еңбек өнімділігін жаңа деңгейге көтереді.",
                    "Сапаны үздіксіз мониторингтеу, деректерге негізделген шешім қабылдау және кері байланыс тетіктері жоғары тәжірибелік нәтижеге кепілдік береді.",
                ],
                quote=SlideQuote(
                    text=(
                        f"«{topic} — тек теориялық тұжырымдама емес, бұл саланың бәсекеге қабілеттілігі мен "
                        f"болашақ даму стандарттарын айқындайтын шешуші стратегиялық тетік.»"
                    ),
                    author="Ғылыми-аналитикалық зерттеу тұжырымдамасы",
                ),
                image_query=f"{topic} strategy vision" if with_photos else None,
            )
        )

    # Remaining slides
    remaining_count = max(slide_count - len(slides), 0)
    for i in range(remaining_count):
        current_num = len(slides) + 1
        is_last = current_num == slide_count
        is_penultimate = current_num == slide_count - 1
        custom_tmpl_title = tmpl_titles[current_num - 1] if (current_num - 1) < len(tmpl_titles) else None

        if is_last:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="conclusion",
                    title=custom_tmpl_title or ("Қорытынды тұжырымдар мен практикалық ұсынымдар" if lang == "қазақша" else ("Итоговые выводы и практические рекомендации" if lang == "русский" else "Key Conclusions & Strategic Recommendations")),
                    subtitle="Зерттеу нәтижелерінің жиынтық түйіні мен даму перспективалары",
                    content=(
                        f"Қорытындылай келе, «{topic}» тақырыбын кешенді ғылыми-тәжірибелік тұрғыдан талдау оның "
                        f"теориялық маңызы мен қолданбалы әлеуетінің өте жоғары екенін дәлелдеді. Жұмыста ұсынылған "
                        f"әдіснамалық тәсілдерді, құрылымдық модельдер мен практикалық ұсынымдарды жүйелі түрде іске "
                        f"асыру саланың тиімділігін арттырып, нақты әрі өлшенетін оң нәтижелерге қол жеткізуге берік негіз болады."
                    ),
                    key_points=[
                        "Зерттеу барысында қойылған барлық ғылыми-аналитикалық мақсаттар мен міндеттер нақты статистикалық және фактологиялық деректер негізінде толық орындалды.",
                        "Анықталған себеп-салдарлық заңдылықтар мен әзірленген қолданбалы ұсыныстарды білім беру, өндірістік және басқару тәжірибесінде тікелей қолдануға болады.",
                        "Алдағы кезеңде бұл бағытты цифрлық экожүйелермен интеграциялау және халықаралық стандарттарға бейімдеу арқылы одан әрі кеңейту ұсынылады.",
                    ],
                    image_query=f"{topic} future conclusion" if with_photos else None,
                )
            )
        elif is_penultimate:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="key_takeaway",
                    title=custom_tmpl_title or "Қолданбалы ұсынымдар мен іске асыру басымдықтары",
                    subtitle="Тәжірибеге енгізу тетіктері, тәуекелдерді басқару және күтілетін нәтижелер",
                    content=(
                        f"«{topic}» бойынша жүргізілген талдау нәтижесінде тұжырымдалған негізгі қағидалар нақты "
                        f"практикалық шешімдер қабылдауға бағытталған. Әрбір стратегиялық басымдық институционалдық "
                        f"инфрақұрылымды нығайтуға, кадрлық және технологиялық әлеуетті дамытуға, сондай-ақ ықтимал "
                        f"кедергілерді алдын ала еңсеруге мүмкіндік береді."
                    ),
                    key_points=[
                        "Нормативтік-әдіснамалық және инфрақұрылымдық базаны заманауи технологиялық талаптарға сәйкес кезең-кезеңімен жаңғырту және стандарттау.",
                        "Салалық мамандардың кәсіби құзыреттілігін арттыру, ғылыми-зерттеу орталықтары мен нақты сектор арасындағы интеграцияны күшейту.",
                        "Енгізілетін жобалардың экономикалық және әлеуметтік қайтарымын тұрақты мониторинг пен нақты сандық метрикалар (ROI, KPI) арқылы бағалау.",
                    ],
                    image_query=f"{topic} key takeaways" if with_photos else None,
                )
            )
        elif current_num % 3 == 0:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="statistics",
                    title=custom_tmpl_title or "Негізгі сандық көрсеткіштер мен эмпирикалық аналитика",
                    subtitle="Статистикалық деректер, өсім динамикасы және тиімділік индикаторлары",
                    content=(
                        f"Сандық деректер мен салыстырмалы-статистикалық талдау «{topic}» бағытының соңғы жылдардағы "
                        f"жоғары өсім динамикасын айғақтайды. Негізгі макро- және микродеңгейдегі индикаторлар жаңа "
                        f"әдіснамалық шешімдерді енгізудің операциялық өнімділік пен сапалық көрсеткіштерге тікелей "
                        f"оң әсер ететінін көрсетеді."
                    ),
                    key_points=[
                        "Жүйелі ғылыми-аналитикалық тәсілді және автоматтандырылған құралдарды енгізген ұйымдарда жалпы операциялық тиімділік 94.2%-ға дейін артты.",
                        "Соңғы бес жылдық кезеңде осы бағыттағы қолданбалы зерттеулер мен технологиялық инфрақұрылымға тартылған инвестиция көлемі 3.4 есеге ұлғайды.",
                        "Салалық сарапшылар мен тәжірибеші мамандардың 88.5%-дан астамы жаңа модельдің экономикалық және практикалық тиімділігін растайды.",
                    ],
                    stats=[
                        SlideStat(value="94.2%", label="Жүйелі тәсілді енгізген жобалардың орташа тиімділік көрсеткіші"),
                        SlideStat(value="3.4x", label="Соңғы 5 жылдағы ғылыми-технологиялық және инвестициялық өсім қарқыны"),
                        SlideStat(value="88.5%", label="Жаңа әдіснаманың практикалық қайтарымын растаған сарапшылар үлесі"),
                    ],
                )
            )
        elif current_num % 3 == 1:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="timeline",
                    title=custom_tmpl_title or "Тарихи қалыптасу эволюциясы мен негізгі даму кезеңдері",
                    subtitle="Бастапқы теориялық алғышарттардан заманауи жоғары технологиялық жүйеге дейін",
                    content=(
                        f"«{topic}» саласының қазіргі даму деңгейіне жетуі бірнеше іргелі тарихи, әдіснамалық және "
                        f"технологиялық кезеңдерді қамтиды. Әрбір кезеңде жинақталған ғылыми білім мен эмпирикалық "
                        f"тәжірибе бұрынғы шектеулерді еңсеріп, келесі сапалық серпілістің берік іргетасын қалады."
                    ),
                    key_points=[
                        "Бастапқы кезеңде іргелі теориялық концепциялар, базалық аксиомалар мен алғашқы классификациялық модельдер қалыптасты.",
                        "Орта кезеңде салалық стандарттар бекітіліп, институционалдық база құрылды және кең ауқымды тәжірибелік сынақтар жүргізілді.",
                        "Қазіргі кезеңде цифрлық технологиялармен және деректерді талдау жүйелерімен толық интеграцияланып, жаһандық деңгейде қолданысқа енді.",
                    ],
                    timeline=[
                        TimelineItem(
                            step="01",
                            title="Іргетас пен классикалық теория",
                            desc="Бастапқы ғылыми гипотезалардың пайда болуы, негізгі ұғымдық аппараттың жүйеленуі және алғашқы іргелі зерттеу мектептерінің қалыптасу кезеңі.",
                        ),
                        TimelineItem(
                            step="02",
                            title="Құрылымдық-әдіснамалық даму",
                            desc="Салалық стандарттар мен нормативтік базаның бекітілуі, қолданбалы модельдердің тәжірибелік сынақтан өтуі және институционалдық инфрақұрылымның кеңеюі.",
                        ),
                        TimelineItem(
                            step="03",
                            title="Заманауи цифрлық трансформация",
                            desc="Инновациялық және интеллектуалды технологиялармен толық интеграциялану, процестерді автоматтандыру және жоғары экономикалық-әлеуметтік тиімділікке жету.",
                        ),
                    ],
                )
            )
        else:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="photo_split" if with_photos else "split_screen",
                    title=custom_tmpl_title or f"Тереңдетілген құрылымдық талдау: Негізгі факторлар мен тетіктер #{current_num}",
                    subtitle="Жүйелік компоненттердің өзара әрекеттесуі және қолданбалы тиімділік шарттары",
                    content=(
                        f"«{topic}» аясындағы процестердің табысты әрі тұрақты жүзеге асуы ішкі ұйымдастырушылық "
                        f"резервтер мен сыртқы орта факторларының үйлесімді әрекеттесуіне тікелей байланысты. "
                        f"Құрылымдық-функционалдық талдау көрсеткендей, әрбір элементтің рөлін дәл айқындау және "
                        f"ресурстық ағындарды оңтайландыру жүйенің жалпы өнімділігін арттырып, ұзақ мерзімді сапалық "
                        f"нәтижелерді қамтамасыз етеді."
                    ),
                    key_points=[
                        "Институционалдық және ұйымдастырушылық-басқару тетіктері барлық ішкі процестердің үздіксіз, үйлесімді әрі жүйелі жүруін реттейді.",
                        "Ғылыми негізделген математикалық және аналитикалық модельдерді қолдану болжау дәлдігін арттырып, басқарушылық қателік ықтималдығын барынша азайтады.",
                        "Салааралық тәжірибе алмасу, ашық деректер базасын пайдалану және цифрлық мониторинг құралдары жаңа өсім нүктелерін ашуға жол береді.",
                        "Нәтижеге бағытталған жобалық басқару моделі материалдық және уақыттық ресурстарды тиімді бөлуге, стратегиялық мақсаттарға уақтылы жетуге мүмкіндік береді.",
                    ],
                    image_query=f"{topic} analysis slide {current_num}" if with_photos else None,
                )
            )

    plan_summary = [f"{s.slide_number}-слайд: {s.title}" for s in slides]

    return PresentationData(
        id=f"pres_{int(time.time())}_{random.randint(1000, 9999)}",
        topic=topic,
        title_presentation=cover_title,
        design_id=chosen_theme.id,
        language=language,
        template_id=template_id,
        persona_style=persona_style,
        is_storybook=is_storybook,
        child_name=child_name,
        with_photos=with_photos,
        slide_count=len(slides),
        slides=slides,
        plan_summary=plan_summary,
        quality_score=QualityScore(),
        createdAt=str(time.time()),
    )
