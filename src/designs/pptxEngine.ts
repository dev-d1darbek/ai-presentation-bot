import pptxgen from 'pptxgenjs';
import { PresentationData, SlideContent } from './types';
import { THEMES_REGISTRY, getThemeHeadingColor } from './registry';

/**
 * Professional PPTX Engine (1:1 Web Canvas Proportions, Photo-Free, Footer-Free)
 * Uses LAYOUT_16x9 (10.0" x 5.625" / 720pt x 405pt) so that point sizes,
 * compact card heights, borders, bullet colors, and margins match the web 16:9 preview 1:1
 * with zero overlap between the header paragraph (<p>) and the cards below it.
 */
export function buildPptxDeck(presentation: PresentationData): any {
  const theme = THEMES_REGISTRY[presentation.design_id] || THEMES_REGISTRY.swiss_minimalism;
  const headingColor = getThemeHeadingColor(theme);
  const pres = new pptxgen();
  pres.layout = 'LAYOUT_16x9'; // 10.0" wide x 5.625" high (720pt x 405pt)

  const slides = presentation.slides || [];
  const fontFace = 'Arial';

  // Helper to build colored bullet paragraphs matching web flex-dot bullets without huge hanging indents
  const buildColoredBullets = (items: string[], dotColor: string, fontSize = 9, spaceAfter = 5) => {
    const runs: any[] = [];
    items.forEach((item, idx) => {
      runs.push({
        text: '•  ',
        options: {
          fontFace,
          fontSize,
          bold: true,
          color: dotColor,
        },
      });
      runs.push({
        text: item,
        options: {
          fontFace,
          fontSize,
          color: theme.textColor,
          breakLine: idx < items.length - 1,
          paraSpaceAfter: spaceAfter,
        },
      });
    });
    return runs;
  };

  slides.forEach((slideItem: SlideContent, idx: number) => {
    const slide = pres.addSlide();
    slide.background = { color: theme.bgColor };

    const slideTitle = slideItem.title || `Слайд ${idx + 1}`;
    const contentText = slideItem.content || '';
    const keyPoints = Array.isArray(slideItem.key_points) ? slideItem.key_points : [];

    // Helper to render standard slide header (Title + sleek accent pill + full uncovered <p> paragraph)
    // Returns the safe top Y coordinate for cards below the header so cards NEVER overlap <p>.
    const addSlideHeader = (subtitleText?: string): number => {
      slide.addText(slideTitle, {
        x: 0.45,
        y: 0.36,
        w: 9.1,
        h: 0.38,
        fontFace,
        fontSize: 15,
        bold: true,
        color: headingColor,
        valign: 'middle',
        margin: 0,
      });

      // Sleek accent pill under title (matching w-14 h-1 rounded-full on web)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.45,
        y: 0.78,
        w: 0.72,
        h: 0.04,
        rectRadius: 0.02,
        fill: { color: theme.accentColor },
        line: { color: theme.accentColor, width: 0.1 },
      });

      if (subtitleText) {
        const isLongParagraph = subtitleText.length > 100;
        const paraH = isLongParagraph ? 0.92 : 0.42;
        slide.addText(subtitleText, {
          x: 0.45,
          y: 0.88,
          w: 9.1,
          h: paraH,
          fontFace,
          fontSize: 9,
          color: theme.textMuted,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
        return 0.88 + paraH + 0.12; // e.g., 1.92" for long paragraph, 1.42" for short subtitle
      }
      return 1.02;
    };

    // ==========================================
    // 1. COVER SLIDE (No Design Name Badge, No Footer, Full 16:9 Proportions)
    // ==========================================
    if (idx === 0 || slideItem.type === 'cover') {
      // Main Card Container (10.0" x 5.625" canvas -> 0.45" X margin, 0.40" Y margin)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.45,
        y: 0.4,
        w: 9.1,
        h: 4.82,
        rectRadius: 0.12,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      // Top sleek accent bar inside Cover Card
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 4.1,
        y: 0.65,
        w: 1.8,
        h: 0.05,
        rectRadius: 0.025,
        fill: { color: theme.accentColor },
        line: { color: theme.accentColor, width: 0.1 },
      });

      // Main Title
      slide.addText(slideTitle, {
        x: 0.85,
        y: 0.86,
        w: 8.3,
        h: 1.05,
        fontFace,
        fontSize: 21,
        bold: true,
        color: headingColor,
        align: 'center',
        valign: 'middle',
        lineSpacingMultiple: 1.15,
        margin: 0,
      });

      // Subtitle
      if (slideItem.subtitle) {
        slide.addText(slideItem.subtitle, {
          x: 1.0,
          y: 1.96,
          w: 8.0,
          h: 0.38,
          fontFace,
          fontSize: 10.5,
          color: theme.textMuted,
          align: 'center',
          valign: 'middle',
          margin: 0,
        });
      }

      // Expanded Overview Card
      if (contentText) {
        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: 0.85,
          y: 2.48,
          w: 8.3,
          h: 1.42,
          rectRadius: 0.08,
          fill: { color: theme.bgColor },
          line: { color: theme.borderColor, width: 0.75 },
        });

        slide.addText(contentText, {
          x: 1.05,
          y: 2.58,
          w: 7.9,
          h: 1.22,
          fontFace,
          fontSize: 9.5,
          color: theme.textColor,
          align: 'center',
          valign: 'middle',
          lineSpacingMultiple: 1.25,
          margin: 0,
        });
      }

      // Bottom 3 Key Focus Pillars on Cover
      if (keyPoints.length > 0) {
        const cardW = 2.64;
        const gap = 0.19;
        keyPoints.slice(0, 3).forEach((pt, kIdx) => {
          const posX = 0.85 + kIdx * (cardW + gap);
          slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
            x: posX,
            y: 4.06,
            w: cardW,
            h: 0.9,
            rectRadius: 0.07,
            fill: { color: theme.bgColor },
            line: { color: theme.borderColor, width: 0.6 },
          });
          slide.addText(pt, {
            x: posX + 0.14,
            y: 4.12,
            w: cardW - 0.28,
            h: 0.78,
            fontFace,
            fontSize: 8.5,
            bold: true,
            color: headingColor,
            align: 'center',
            valign: 'middle',
            lineSpacingMultiple: 1.15,
            margin: 0,
          });
        });
      }
    } else if (slideItem.type === 'two_person_comparison' && slideItem.comparison) {
      // ==========================================
      // 2. TWO-PERSON COMPARISON SLIDE (Compact Cards below <p>, Zero Overlap)
      // ==========================================
      const cardY = addSlideHeader(contentText);
      const cardH = 5.2 - cardY;

      // Entity A Card (Left)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.45,
        y: cardY,
        w: 4.42,
        h: cardH,
        rectRadius: 0.08,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      // Badge A
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.68,
        y: cardY + 0.18,
        w: 0.3,
        h: 0.3,
        rectRadius: 0.05,
        fill: { color: theme.secondaryColor },
        line: { color: theme.secondaryColor, width: 0.1 },
      });
      slide.addText('A', {
        x: 0.68,
        y: cardY + 0.18,
        w: 0.3,
        h: 0.3,
        fontFace,
        fontSize: 9,
        bold: true,
        color: 'FFFFFF',
        align: 'center',
        valign: 'middle',
        margin: 0,
      });

      slide.addText(slideItem.comparison.entityA.name, {
        x: 1.08,
        y: cardY + 0.18,
        w: 3.55,
        h: 0.3,
        fontFace,
        fontSize: 10.5,
        bold: true,
        color: headingColor,
        valign: 'middle',
        margin: 0,
      });

      if (slideItem.comparison.entityA.points.length > 0) {
        slide.addText(buildColoredBullets(slideItem.comparison.entityA.points, theme.accentColor, 9, 5), {
          x: 0.68,
          y: cardY + 0.58,
          w: 3.96,
          h: cardH - 0.72,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
      }

      // Entity B Card (Right)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 5.13,
        y: cardY,
        w: 4.42,
        h: cardH,
        rectRadius: 0.08,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      // Badge B
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 5.36,
        y: cardY + 0.18,
        w: 0.3,
        h: 0.3,
        rectRadius: 0.05,
        fill: { color: theme.accentColor },
        line: { color: theme.accentColor, width: 0.1 },
      });
      slide.addText('B', {
        x: 5.36,
        y: cardY + 0.18,
        w: 0.3,
        h: 0.3,
        fontFace,
        fontSize: 9,
        bold: true,
        color: 'FFFFFF',
        align: 'center',
        valign: 'middle',
        margin: 0,
      });

      slide.addText(slideItem.comparison.entityB.name, {
        x: 5.76,
        y: cardY + 0.18,
        w: 3.55,
        h: 0.3,
        fontFace,
        fontSize: 10.5,
        bold: true,
        color: headingColor,
        valign: 'middle',
        margin: 0,
      });

      if (slideItem.comparison.entityB.points.length > 0) {
        slide.addText(buildColoredBullets(slideItem.comparison.entityB.points, theme.secondaryColor, 9, 5), {
          x: 5.36,
          y: cardY + 0.58,
          w: 3.96,
          h: cardH - 0.72,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
      }
    } else if (slideItem.type === 'timeline' && slideItem.timeline && slideItem.timeline.length > 0) {
      // ==========================================
      // 3. TIMELINE SLIDE (3 Compact Step Cards below <p>, Zero Overlap)
      // ==========================================
      const cardY = addSlideHeader(contentText);
      const cardH = 5.2 - cardY;

      const cardW = 2.88;
      const gap = 0.23;
      slideItem.timeline.slice(0, 3).forEach((item, tIdx) => {
        const posX = 0.45 + tIdx * (cardW + gap);

        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: posX,
          y: cardY,
          w: cardW,
          h: cardH,
          rectRadius: 0.08,
          fill: { color: theme.cardBg },
          line: { color: theme.borderColor, width: 0.75 },
        });

        // Step number
        slide.addText(item.step || `0${tIdx + 1}`, {
          x: posX + 0.22,
          y: cardY + 0.18,
          w: cardW - 0.44,
          h: 0.36,
          fontFace,
          fontSize: 16,
          bold: true,
          color: theme.secondaryColor,
          valign: 'top',
          margin: 0,
        });

        // Step title
        slide.addText(item.title, {
          x: posX + 0.22,
          y: cardY + 0.58,
          w: cardW - 0.44,
          h: 0.4,
          fontFace,
          fontSize: 10.5,
          bold: true,
          color: headingColor,
          valign: 'top',
          margin: 0,
        });

        // Step description
        slide.addText(item.desc, {
          x: posX + 0.22,
          y: cardY + 1.02,
          w: cardW - 0.44,
          h: cardH - 1.16,
          fontFace,
          fontSize: 9,
          color: theme.textColor,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
      });
    } else if (slideItem.type === 'statistics' && slideItem.stats && slideItem.stats.length > 0) {
      // ==========================================
      // 4. STATISTICS SLIDE (3 Compact Metric Cards + Key Findings below <p>)
      // ==========================================
      const cardY = addSlideHeader(contentText);
      const metricH = 1.65;

      const cardW = 2.88;
      const gap = 0.23;
      slideItem.stats.slice(0, 3).forEach((st, sIdx) => {
        const posX = 0.45 + sIdx * (cardW + gap);

        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: posX,
          y: cardY,
          w: cardW,
          h: metricH,
          rectRadius: 0.08,
          fill: { color: theme.cardBg },
          line: { color: theme.borderColor, width: 0.75 },
        });

        slide.addText(st.value, {
          x: posX + 0.16,
          y: cardY + 0.18,
          w: cardW - 0.32,
          h: 0.65,
          fontFace,
          fontSize: 21,
          bold: true,
          color: theme.secondaryColor,
          align: 'center',
          valign: 'middle',
          margin: 0,
        });

        slide.addText(st.label, {
          x: posX + 0.18,
          y: cardY + 0.88,
          w: cardW - 0.36,
          h: 0.62,
          fontFace,
          fontSize: 9.5,
          bold: true,
          color: headingColor,
          align: 'center',
          valign: 'top',
          lineSpacingMultiple: 1.15,
          margin: 0,
        });
      });

      // Bottom Analytical Takeaways Box on Statistics Slide
      if (keyPoints.length > 0) {
        const bottomY = cardY + metricH + 0.14;
        const bottomH = 5.2 - bottomY;
        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: 0.45,
          y: bottomY,
          w: 9.1,
          h: bottomH,
          rectRadius: 0.08,
          fill: { color: theme.cardBg },
          line: { color: theme.borderColor, width: 0.75 },
        });
        slide.addText(buildColoredBullets(keyPoints.slice(0, 3), theme.accentColor, 9, 4), {
          x: 0.68,
          y: bottomY + 0.14,
          w: 8.64,
          h: bottomH - 0.24,
          valign: 'top',
          lineSpacingMultiple: 1.15,
          margin: 0,
        });
      }
    } else if (slideItem.type === 'big_typography' || slideItem.quote) {
      // ==========================================
      // 5. BIG TYPOGRAPHY / STRATEGIC QUOTE SLIDE
      // ==========================================
      const cardY = addSlideHeader();

      // Hero Quote Card (Top)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.45,
        y: cardY,
        w: 9.1,
        h: 2.15,
        rectRadius: 0.08,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      const quoteText = slideItem.quote?.text || contentText;
      const quoteAuthor = slideItem.quote?.author || 'Түйінді стратегиялық қағида';

      slide.addText('«', {
        x: 0.7,
        y: cardY + 0.12,
        w: 0.45,
        h: 0.5,
        fontFace,
        fontSize: 26,
        bold: true,
        color: theme.secondaryColor,
        valign: 'top',
        margin: 0,
      });

      slide.addText(quoteText, {
        x: 1.2,
        y: cardY + 0.22,
        w: 8.1,
        h: 1.25,
        fontFace,
        fontSize: 11,
        bold: true,
        italic: true,
        color: headingColor,
        valign: 'top',
        lineSpacingMultiple: 1.22,
        margin: 0,
      });

      slide.addText(`— ${quoteAuthor}`, {
        x: 1.2,
        y: cardY + 1.58,
        w: 8.1,
        h: 0.35,
        fontFace,
        fontSize: 9.5,
        bold: true,
        color: theme.secondaryColor,
        valign: 'middle',
        margin: 0,
      });

      // Bottom 3 Strategic Pillars
      const cardW = 2.88;
      const gap = 0.23;
      const pillarY = cardY + 2.32;
      const pillarH = 5.2 - pillarY;
      const pillars = keyPoints.slice(0, 3);
      pillars.forEach((item, pIdx) => {
        const posX = 0.45 + pIdx * (cardW + gap);

        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: posX,
          y: pillarY,
          w: cardW,
          h: pillarH,
          rectRadius: 0.08,
          fill: { color: theme.cardBg },
          line: { color: theme.borderColor, width: 0.75 },
        });

        slide.addText(`#0${pIdx + 1} ҚАҒИДАТ`, {
          x: posX + 0.2,
          y: pillarY + 0.16,
          w: cardW - 0.4,
          h: 0.24,
          fontFace,
          fontSize: 8,
          bold: true,
          color: theme.secondaryColor,
          valign: 'middle',
          margin: 0,
        });

        slide.addText(item, {
          x: posX + 0.2,
          y: pillarY + 0.44,
          w: cardW - 0.4,
          h: pillarH - 0.56,
          fontFace,
          fontSize: 9,
          color: headingColor,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
      });
    } else if (slideItem.type === 'key_takeaway' || slideItem.type === 'conclusion') {
      // ==========================================
      // 6. KEY TAKEAWAYS / CONCLUSION SLIDE (Compact Cards below <p>, Zero Overlap)
      // ==========================================
      const cardY = addSlideHeader(contentText);
      const cardH = 5.2 - cardY;

      const cardW = 2.88;
      const gap = 0.23;
      const items = keyPoints.slice(0, 3);
      items.forEach((item, kIdx) => {
        const posX = 0.45 + kIdx * (cardW + gap);

        slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
          x: posX,
          y: cardY,
          w: cardW,
          h: cardH,
          rectRadius: 0.08,
          fill: { color: theme.cardBg },
          line: { color: theme.borderColor, width: 0.75 },
        });

        // Badge #
        slide.addText(`#0${kIdx + 1}`, {
          x: posX + 0.22,
          y: cardY + 0.18,
          w: cardW - 0.44,
          h: 0.32,
          fontFace,
          fontSize: 11,
          bold: true,
          color: theme.secondaryColor,
          valign: 'middle',
          margin: 0,
        });

        // Content
        slide.addText(item, {
          x: posX + 0.22,
          y: cardY + 0.56,
          w: cardW - 0.44,
          h: cardH - 0.72,
          fontFace,
          fontSize: 9,
          color: headingColor,
          valign: 'top',
          lineSpacingMultiple: 1.2,
          margin: 0,
        });
      });
    } else {
      // ==========================================
      // 7. EXPANDED ANALYTICAL SPLIT SCREEN (2 Compact Text Cards below <p>, Zero Overlap)
      // ==========================================
      const cardY = addSlideHeader(slideItem.subtitle);
      const cardH = 5.2 - cardY;

      // Left Column Card (In-Depth Narrative & Analytical Context)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 0.45,
        y: cardY,
        w: 4.42,
        h: cardH,
        rectRadius: 0.08,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      slide.addText('📌 НЕГІЗГІ МАЗМҰН ЖӘНЕ ТАЛДАУ', {
        x: 0.68,
        y: cardY + 0.18,
        w: 3.96,
        h: 0.24,
        fontFace,
        fontSize: 8.5,
        bold: true,
        color: theme.secondaryColor,
        valign: 'middle',
        margin: 0,
      });

      if (contentText) {
        slide.addText(contentText, {
          x: 0.68,
          y: cardY + 0.48,
          w: 3.96,
          h: cardH - 0.64,
          fontFace,
          fontSize: 9,
          color: theme.textColor,
          valign: 'top',
          lineSpacingMultiple: 1.22,
          margin: 0,
        });
      }

      // Right Column Card (Key Arguments, Facts & Defense Points)
      slide.addShape((pres as any).shapes.ROUNDED_RECTANGLE, {
        x: 5.13,
        y: cardY,
        w: 4.42,
        h: cardH,
        rectRadius: 0.08,
        fill: { color: theme.cardBg },
        line: { color: theme.borderColor, width: 0.75 },
      });

      slide.addText('💡 НЕГІЗГІ ТЕЗИСТЕР МЕН ДӘЙЕКТЕР', {
        x: 5.36,
        y: cardY + 0.18,
        w: 3.96,
        h: 0.24,
        fontFace,
        fontSize: 8.5,
        bold: true,
        color: theme.secondaryColor,
        valign: 'middle',
        margin: 0,
      });

      if (keyPoints.length > 0) {
        slide.addText(buildColoredBullets(keyPoints, theme.accentColor, 9, 5), {
          x: 5.36,
          y: cardY + 0.48,
          w: 3.96,
          h: cardH - 0.64,
          valign: 'top',
          lineSpacingMultiple: 1.18,
          margin: 0,
        });
      }
    }
  });

  return pres;
}
