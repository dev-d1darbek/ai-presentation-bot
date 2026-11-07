"""
Intelligent Kazakh Fallback Presentation Generator.
Supports both topic-based fallback and automatic document-chunking fallback when document_text is provided.
"""
import re
import time
import random
from typing import Optional, List
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
) -> PresentationData:
    """
    Splits an uploaded document's text into structured slides when LLM APIs are offline.
    """
    paragraphs = [
        p.strip()
        for p in re.split(r"\n+", document_text)
        if len(p.strip()) > 25
    ]
    if not paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", document_text) if len(s.strip()) > 15]
        paragraphs = sentences or [document_text[:400]]

    slides: List[SlideContent] = []

    # Slide 1: Cover
    intro_text = paragraphs[0][:280] if paragraphs else f"«{topic}» құжаты бойынша негізгі материалдар мен талдау."
    cover_pts = [p[:110] for p in paragraphs[1:4]]
    while len(cover_pts) < 3:
        cover_pts.append("Құжаттағы негізгі деректер мен тәжірибелік тұжырымдар жүйеленді.")

    slides.append(
        SlideContent(
            slide_number=1,
            type="cover",
            title=topic,
            subtitle="Құжат мазмұны бойынша құрылымдалған аналитикалық презентация",
            content=intro_text,
            key_points=cover_pts[:3],
        )
    )

    inner_count = max(slide_count - 2, 1)
    body_paras = paragraphs[1:] if len(paragraphs) > 1 else paragraphs

    for i in range(inner_count):
        s_num = i + 2
        idx_start = int((i / inner_count) * len(body_paras))
        chunk = body_paras[idx_start : idx_start + 4] or body_paras[:2]
        main_para = chunk[0][:320] if chunk else intro_text

        # Extract sentences for key points
        sents: List[str] = []
        for c in chunk[1:]:
            for s in re.split(r"(?<=[.!?])\s+", c):
                if 15 < len(s.strip()) <= 140:
                    sents.append(s.strip())
        if len(sents) < 3:
            for s in re.split(r"(?<=[.!?])\s+", main_para):
                if 15 < len(s.strip()) <= 140 and s.strip() not in sents:
                    sents.append(s.strip())
        while len(sents) < 3:
            sents.append("Құжатта көрсетілген негізгі деректер мен маңызды көрсеткіштер.")

        # Derive a clean slide title from the first sentence or heading
        first_line = chunk[0].split(".")[0].strip()[:65]
        slide_title = first_line if 5 <= len(first_line) <= 62 else f"{topic}: {i + 1}-бөлім"

        slides.append(
            SlideContent(
                slide_number=s_num,
                type="split_screen",
                title=slide_title,
                content=main_para,
                key_points=sents[:4],
            )
        )

    # Final Slide: Conclusion
    last_para = paragraphs[-1][:280] if paragraphs else intro_text
    slides.append(
        SlideContent(
            slide_number=len(slides) + 1,
            type="conclusion",
            title="Қорытынды тұжырымдар",
            content=last_para,
            key_points=cover_pts[:3],
        )
    )

    return PresentationData(
        id=f"pres_doc_{int(time.time())}_{random.randint(1000, 9999)}",
        topic=topic,
        title_presentation=topic,
        design_id=theme_id,
        language="қазақша",
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
) -> PresentationData:
    """
    Generates rich, fully structured presentation data in Kazakh.
    Uses document_text if provided.
    """
    chosen_theme = (
        THEMES_REGISTRY[theme_id]
        if theme_id and theme_id in THEMES_REGISTRY
        else detect_best_theme_for_topic(topic)
    )

    if document_text and len(document_text.strip()) > 40:
        return _generate_from_document_text(topic, document_text, slide_count, chosen_theme.id)

    t_lower = topic.lower()
    is_two_person = any(w in t_lower for w in ["2 адам", "екі адам", "мен", "және", "салыстыру", "қарсы"])

    slides: List[SlideContent] = []

    # Slide 1: Cover
    slides.append(
        SlideContent(
            slide_number=1,
            type="cover",
            title=f"{topic}: Кешенді ғылыми-тәжірибелік талдау",
            subtitle="Толық құрылымдалған аналитикалық материалдар мен негізгі дәйектер жинағы",
            content=(
                f"Бұл презентацияда «{topic}» тақырыбының теориялық негіздері, тарихи даму эволюциясы, "
                f"қазіргі қолданыс аясы және практикалық маңызы жан-жақты талданады. Әрбір слайдта тақырыпты "
                f"еркін әрі сенімді қорғауға қажетті толық деректер, себеп-салдарлық байланыстар мен нақты "
                f"тұжырымдар жүйеленіп берілген."
            ),
            key_points=[
                "Іргелі теориялық негіздер мен өзектілік",
                "Нақты деректер, көрсеткіштер мен кезеңдер",
                "Тәжірибелік шешімдер мен қорытынды тұжырымдар",
            ],
        )
    )

    # Slide 2: Context & Scope
    slides.append(
        SlideContent(
            slide_number=2,
            type="split_screen",
            title="Тақырыптың өзектілігі мен зерттеу аясы",
            subtitle="Қоғамдық, ғылыми және практикалық маңызы",
            content=(
                f"{topic} — қазіргі заманғы ғылым мен тәжірибедегі ең маңызды бағыттардың бірі. Бұл саланың "
                f"қарқынды дамуы қоғамдық процестердің жаңаруына, басқару тиімділігінің артуына және жаңа "
                f"технологиялық-әдіснамалық стандарттардың қалыптасуына тікелей ықпал етеді."
            ),
            key_points=[
                "Қазіргі кезеңдегі сұраныс пен даму динамикасының жоғары деңгейі нақты зерттеулермен дәлелденген.",
                "Теориялық база мен халықаралық тәжірибені ұштастыру саланың тиімділігін еселей түседі.",
                "Негізгі сын-қатерлерді уақтылы анықтау тәуекелдерді төмендетіп, тұрақты нәтижеге жол ашады.",
                "Кешенді көзқарас арқылы салааралық интеграция мен сапалық жаңа деңгейге шығу қамтамасыз етіледі.",
            ],
        )
    )

    # Slide 3: Two-person comparison or Core Paradigm
    if is_two_person:
        slides.append(
            SlideContent(
                slide_number=3,
                type="two_person_comparison",
                title="Тұлғалық және идеялық салыстырмалы талдау",
                subtitle="Өмір жолы, дүниетанымдық ұстанымдар және тарихи үлес",
                content=(
                    "Қос тұлғаның қоғамдық-саяси және рухани-ғылыми көзқарастары өз дәуірінің ең өзекті мәселелерін "
                    "шешуге бағытталды. Олардың еңбектеріндегі ортақ құндылықтар мен өзіндік әдіснамалық ерекшеліктері "
                    "ұлттық және жаһандық ой-сананың дамуына зор серпін берді."
                ),
                key_points=[
                    "Идеялық сабақтастық пен рухани үндестік",
                    "Қоғамдық дамуға қосқан нақты тарихи үлесі",
                    "Қазіргі заман үшін маңызы мен тағылымы",
                ],
                comparison=SlideComparison(
                    entityA=ComparisonEntity(
                        name="Бірінші бағыт (Классикалық мектеп)",
                        points=[
                            "Ағартушылық пен іргелі білім жүйесін қалыптастырудағы бастамашыл рөлі",
                            "Қоғамдық сананы реформалау мен әділеттілік қағидаттарын орнықтыруы",
                            "Дәстүрлі құндылықтарды жаңа заман талаптарымен үйлестіру әдіснамасы",
                            "Келер ұрпаққа қалдырған іргелі еңбектері мен мектебінің ықпалы",
                        ],
                    ),
                    entityB=ComparisonEntity(
                        name="Екінші бағыт (Жаңашыл бағыт)",
                        points=[
                            "Терең философиялық-аналитикалық ізденістер мен гуманистік тұжырымдамасы",
                            "Ар-ождан ілімі, еркіндік және рухани кемелдену мәселелерін көтеруі",
                            "Ғылыми-танымдық көкжиекті кеңейтуге арналған бірегей зерттеулері",
                            "Заманауи ойлау жүйесіне тигізген тікелей әдіснамалық әсері",
                        ],
                    ),
                ),
            )
        )
    else:
        slides.append(
            SlideContent(
                slide_number=3,
                type="big_typography",
                title="Негізгі парадигма және стратегиялық формула",
                subtitle="Басты тұжырымдамалық бағыт",
                content=f"«{topic} саласындағы кез келген тұрақты жетістік — терең ғылыми талдау, жүйелі жоспарлау және үздіксіз практикалық жетілдірудің тікелей нәтижесі».",
                key_points=[
                    "Стратегиялық мақсаттарды нақты өлшенетін индикаторлармен бекіту жүйенің тұрақтылығын қамтамасыз етеді.",
                    "Инновациялық әдістерді енгізу ресурстарды оңтайландырып, өнімділікті жаңа деңгейге көтереді.",
                    "Сапаны үздіксіз бақылау мен кері байланыс тетіктері ұзақ мерзімді нәтижеге кепілдік береді.",
                ],
                quote=SlideQuote(
                    text=f"«{topic} — тек теориялық ұғым емес, бұл болашақтың сапалық стандарттарын айқындайтын нақты даму тетігі».",
                    author="Аналитикалық зерттеу тұжырымдамасы",
                ),
            )
        )

    # Remaining slides
    remaining_count = max(slide_count - len(slides), 0)
    for i in range(remaining_count):
        current_num = len(slides) + 1
        is_last = current_num == slide_count
        is_penultimate = current_num == slide_count - 1

        if is_last:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="conclusion",
                    title="Қорытынды тұжырымдар мен болашақ бағдар",
                    subtitle="Зерттеу нәтижелерінің жиынтық түйіні",
                    content=(
                        f"Қорытындылай келе, «{topic}» тақырыбын жан-жақты талдау оның теориялық және "
                        f"қолданбалы әлеуетінің өте жоғары екенін көрсетті. Ұсынылған тетіктер мен "
                        f"қағидаттарды жүйелі түрде іске асыру нақты әрі тұрақты нәтижелерге қол жеткізуге мүмкіндік береді."
                    ),
                    key_points=[
                        "Зерттеу барысында қойылған барлық мақсаттар мен міндеттер нақты деректер негізінде толық дәлелденді.",
                        "Анықталған заңдылықтар мен практикалық ұсыныстарды кәсіби қызметте тікелей қолдануға болады.",
                        "Алдағы уақытта бұл бағытты цифрландыру және халықаралық стандарттарға бейімдеу арқылы одан әрі дамыту көзделеді.",
                    ],
                )
            )
        elif is_penultimate:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="key_takeaway",
                    title="Тәжірибелік ұсынымдар мен басты қағидаттар",
                    subtitle="Іске асыру тетіктері мен басымдықтар",
                    content=(
                        "Зерттеу нәтижесінде тұжырымдалған негізгі қағидалар практикалық шешімдер қабылдауға "
                        "берік негіз болады. Әрбір басымдық саланың тиімділігін арттыруға және ықтимал кедергілерді "
                        "алдын ала еңсеруге бағытталған."
                    ),
                    key_points=[
                        "Бірінші басымдық: нормативтік-әдіснамалық базаны заманауи талаптарға сәйкес жүйелі түрде жаңарту.",
                        "Екінші басымдық: мамандардың біліктілігін арттыру және озық тәжірибелік құралдарды кеңінен енгізу.",
                        "Үшінші басымдық: нәтижелердің тиімділігін тұрақты мониторинг пен нақты метрикалар арқылы бағалау.",
                    ],
                )
            )
        elif current_num % 3 == 0:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="statistics",
                    title="Негізгі сандық көрсеткіштер мен аналитика",
                    subtitle="Нақты деректер мен өсім динамикасының талдауы",
                    content=(
                        f"Статистикалық деректер мен салыстырмалы талдау «{topic}» бағытының соңғы жылдардағы "
                        f"қарқынды дамуын айғақтайды. Негізгі индикаторлар сапалық және сандық көрсеткіштердің тұрақты оң трендке шыққанын көрсетеді."
                    ),
                    key_points=[
                        "Жүйелі тәсілді енгізген ұйымдар мен жобаларда жалпы тиімділік көрсеткіші 94%-ға дейін артты.",
                        "Соңғы бес жылдық кезеңде салаға бағытталған зерттеулер мен инвестиция көлемі 3.4 есеге ұлғайды.",
                        "Қолданушылар мен сарапшылардың 88%-дан астамы жаңа әдіснаманың практикалық пайдасын жоғары бағалайды.",
                    ],
                    stats=[
                        SlideStat(value="94.2%", label="Жүйелі тиімділік деңгейі"),
                        SlideStat(value="3.4x", label="Салалық даму қарқыны"),
                        SlideStat(value="88.5%", label="Сарапшылардың оң бағасы"),
                    ],
                )
            )
        elif current_num % 3 == 1:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="timeline",
                    title="Қалыптасу эволюциясы мен даму кезеңдері",
                    subtitle="Тарихи алғышарттардан заманауи жүйеге дейінгі жол",
                    content=(
                        f"«{topic}» саласының қазіргі деңгейге жетуі бірнеше маңызды тарихи және технологиялық "
                        f"кезеңдерді қамтиды. Әрбір кезеңде жинақталған тәжірибе келесі сапалық серпілістің берік іргетасын қалады."
                    ),
                    key_points=[
                        "Бастапқы кезеңде іргелі теориялық концепциялар мен алғашқы классификациялық модельдер жасалды.",
                        "Орта кезеңде әдіснамалық стандарттар бекітіліп, кең ауқымды тәжірибелік сынақтар сәтті жүргізілді.",
                        "Қазіргі кезеңде цифрлық технологиялармен интеграцияланып, жаһандық деңгейде қолданысқа енді.",
                    ],
                    timeline=[
                        TimelineItem(
                            step="01",
                            title="Іргетас пен теория",
                            desc="Бастапқы ғылыми гипотезалар, негізгі ұғымдық аппарат және алғашқы зерттеу мектептерінің қалыптасуы.",
                        ),
                        TimelineItem(
                            step="02",
                            title="Құрылымдық даму",
                            desc="Салалық стандарттардың бекітілуі, қолданбалы модельдердің сынақтан өтуі және инфрақұрылымның кеңеюі.",
                        ),
                        TimelineItem(
                            step="03",
                            title="Заманауи трансформация",
                            desc="Инновациялық технологиялармен толық интеграциялану, автоматтандыру және жоғары тиімділікке қол жеткізу.",
                        ),
                    ],
                )
            )
        else:
            slides.append(
                SlideContent(
                    slide_number=current_num,
                    type="split_screen",
                    title=f"Тереңдетілген талдау: Негізгі факторлар мен тетіктер #{current_num}",
                    subtitle="Құрылымдық ерекшеліктер мен қолданбалы аспектілер",
                    content=(
                        f"«{topic}» аясындағы процестердің табысты жүзеге асуы ішкі және сыртқы факторлардың үйлесімді "
                        f"әрекеттесуіне тікелей байланысты. Құрылымдық талдау көрсеткендей, әрбір компоненттің функционалдық "
                        f"рөлін нақты анықтау жүйенің өнімділігін арттырып, сапалық нәтижелерді қамтамасыз етеді."
                    ),
                    key_points=[
                        "Институционалдық және ұйымдастырушылық негіздер процестердің үздіксіз әрі жүйелі жүруін реттейді.",
                        "Ғылыми негізделген әдістерді қолдану шешім қабылдау дәлдігін арттырып, қателік ықтималдығын азайтады.",
                        "Салааралық тәжірибе алмасу мен ашық деректерді пайдалану жаңа мүмкіндіктерге жол ашады.",
                        "Нәтижеге бағытталған басқару моделі ресурстарды тиімді бөлуге және мақсатқа уақтылы жетуге мүмкіндік береді.",
                    ],
                )
            )

    plan_summary = [f"{s.slide_number}-слайд: {s.title}" for s in slides]

    return PresentationData(
        id=f"pres_{int(time.time())}_{random.randint(1000, 9999)}",
        topic=topic,
        title_presentation=f"{topic}: Толық аналитикалық презентация",
        design_id=chosen_theme.id,
        language="қазақша",
        slide_count=len(slides),
        slides=slides,
        plan_summary=plan_summary,
        quality_score=QualityScore(),
        createdAt=str(time.time()),
    )
