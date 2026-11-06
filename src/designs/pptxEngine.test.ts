import test from 'node:test';
import assert from 'node:assert/strict';
import { THEMES_REGISTRY, getThemeHeadingColor, detectBestThemeForTopic } from './registry';
import { buildPptxDeck } from './pptxEngine';
import { PresentationData } from './types';

test('getThemeHeadingColor ensures readable contrast', () => {
  const darkTheme = THEMES_REGISTRY.apple_keynote;
  assert.equal(darkTheme.isDark, true);
  const darkHeading = getThemeHeadingColor(darkTheme);
  assert.notEqual(darkHeading, '000000');
  assert.equal(darkHeading, 'FFFFFF');

  const lightTheme = THEMES_REGISTRY.swiss_minimalism;
  assert.equal(lightTheme.isDark, false);
  const lightHeading = getThemeHeadingColor(lightTheme);
  assert.equal(lightHeading, '111827');
});

test('detectBestThemeForTopic selects appropriate themes', () => {
  const aiTheme = detectBestThemeForTopic('Жасанды интеллект және машиналық оқыту');
  assert.equal(aiTheme.id, 'futuristic_tech');

  const historyTheme = detectBestThemeForTopic('Қазақстан тарихы');
  assert.equal(historyTheme.id, 'cinematic_history');
});

test('buildPptxDeck generates photo-free, note-free deck with no cover design name badge and exact 10x5.625 bounds', () => {
  const sampleData: PresentationData = {
    id: 'test_deck_1',
    topic: 'Жасанды интеллект',
    title_presentation: 'Жасанды интеллекттің келешегі',
    design_id: 'apple_keynote',
    language: 'қазақша',
    slide_count: 7,
    plan_summary: ['Кіріспе', 'Талдау', 'Салыстыру', 'Статистика', 'Кезеңдер', 'Қағидат', 'Қорытынды'],
    quality_score: { total: 98, design: 25, content: 20, imagery: 15, readability: 15, structure: 10 },
    createdAt: new Date().toISOString(),
    slides: [
      {
        slide_number: 1,
        type: 'cover',
        title: 'Жасанды интеллект дамуы',
        subtitle: 'Кәсіби ғылыми-тәжірибелік зерттеу',
        content: 'Жасанды интеллект саласындағы кешенді шолу мен негізгі бағыттар.',
        key_points: ['Теориялық негіздер', 'Технологиялық серпіліс', 'Болашақ бағдар'],
      },
      {
        slide_number: 2,
        type: 'two_person_comparison',
        title: 'Екі ғалымның көзқарасы',
        content: 'Ғалымдардың теориялық ұстанымдары мен ғылыми мұрасы.',
        key_points: ['Салыстыру'],
        comparison: {
          entityA: { name: 'Алан Тьюринг', points: ['Тьюринг сынағы', 'Машиналық сана'] },
          entityB: { name: 'Джон Маккарти', points: ['AI терминін енгізу', 'LISP тілі'] },
        },
      },
      {
        slide_number: 3,
        type: 'timeline',
        title: 'Даму кезеңдері',
        content: 'Үш маңызды тарихи белес.',
        key_points: ['1950', '2012', '2024'],
        timeline: [
          { step: '01', title: 'Бастау', desc: 'Символдық жүйелер дәуірі' },
          { step: '02', title: 'Серпіліс', desc: 'Тереңдетілген нейрожелілер' },
          { step: '03', title: 'Генеративті AI', desc: 'LLM және мультимодальділік' },
        ],
      },
      {
        slide_number: 4,
        type: 'statistics',
        title: 'Негізгі көрсеткіштер',
        content: 'Қарқынды өсім динамикасы.',
        key_points: ['Нарық көлемі 3.4 есе өсті', 'Қолданушылар саны артты'],
        stats: [
          { value: '88%', label: 'Қолдау деңгейі' },
          { value: '4.2x', label: 'Өсім қарқыны' },
          { value: '$1.3T', label: 'Нарық көлемі' },
        ],
      },
      {
        slide_number: 5,
        type: 'big_typography',
        title: 'Басты философиялық қағидат',
        content: 'Жүйелі көзқарас табысқа жетелейді.',
        key_points: ['Этикалық қағидалар', 'Қауіпсіздік', 'Адамға бағытталу'],
        quote: { text: 'Жасанды интеллект адам мүмкіндігін еселей түседі.', author: 'Зерттеушілер қауымдастығы' },
      },
      {
        slide_number: 6,
        type: 'split_screen',
        title: 'Қазіргі қолданыс аясы',
        content: 'AI күнделікті өмір мен өндірісте сенімді көмекшіге айналуда.',
        key_points: ['Медициналық диагностика', 'Білім беру жүйесі', 'Өнеркәсіптік автоматтандыру'],
      },
      {
        slide_number: 7,
        type: 'conclusion',
        title: 'Қорытынды тұжырымдар',
        content: 'Болашаққа бағытталған стратегиялық шешімдер.',
        key_points: ['Инфрақұрылымды дамыту', 'Білікті мамандар дайындау', 'Қорытынды нәтижелер'],
      },
    ],
  };

  const pres = buildPptxDeck(sampleData);
  assert.ok(pres);
  assert.equal(pres._slides.length, 7);

  // Verify cover slide does NOT contain theme name badge
  const coverSlide = pres._slides[0];
  for (const obj of coverSlide._slideObjects) {
    if (typeof obj.text === 'string') {
      assert.ok(!obj.text.includes(THEMES_REGISTRY.apple_keynote.nameKz.toUpperCase()));
    }
  }

  // Verify every object on every slide has NO images, NO bottom footer counter, and fits within LAYOUT_16x9 (10.0" x 5.625")
  for (let i = 0; i < pres._slides.length; i++) {
    const slide = pres._slides[i];
    for (const obj of slide._slideObjects) {
      assert.notEqual(obj._type, 'image', 'Slide must not contain any photos/images');
      if (typeof obj.text === 'string') {
        assert.notEqual(obj.text, `${i + 1} / ${pres._slides.length}`, 'Slide must not contain page counter badge');
        assert.notEqual(obj.text, sampleData.topic, 'Slide must not contain bottom topic footer');
      }
      if (!obj.options) continue;
      const { x, y, w, h, fontSize, rectRadius } = obj.options;
      assert.ok(x >= 0.44 && x + w <= 9.6, `Object horizontal bounds out of 10.0" slide range: x=${x}, w=${w}`);
      assert.ok(y >= 0.35 && y + h <= 5.3, `Object vertical bounds out of 5.625" slide range: y=${y}, h=${h}`);
      if (fontSize !== undefined) {
        assert.ok(fontSize >= 8 && fontSize <= 28, `Font size out of proportional range: ${fontSize}`);
      }
      if (rectRadius !== undefined) {
        assert.ok(rectRadius > 0 && rectRadius <= 0.15, `Corner radius too large: ${rectRadius}`);
      }
    }
  }
});
