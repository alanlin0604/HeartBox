import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


# Register CID font for CJK support
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

CJK_FONT = 'STSong-Light'

# i18n labels
PDF_LABELS = {
    'zh-TW': {
        'title': '心情日誌報告',
        'total_notes': '日誌總數',
        'avg_sentiment': '平均情緒',
        'avg_stress': '平均壓力',
        'sentiment': '情緒',
        'stress': '壓力',
        'tags': '標籤',
        'ai_feedback': 'AI 分析回饋',
        'no_notes': '所選日期範圍內沒有找到日誌。',
        'weather': '天氣',
    },
    'en': {
        'title': 'Mood Journal Report',
        'total_notes': 'Total Notes',
        'avg_sentiment': 'Avg Sentiment',
        'avg_stress': 'Avg Stress',
        'sentiment': 'Sentiment',
        'stress': 'Stress',
        'tags': 'Tags',
        'ai_feedback': 'AI Analysis',
        'no_notes': 'No notes found in the selected date range.',
        'weather': 'Weather',
    },
    'ja': {
        'title': '気分日記レポート',
        'total_notes': '日記総数',
        'avg_sentiment': '平均感情',
        'avg_stress': '平均ストレス',
        'sentiment': '感情',
        'stress': 'ストレス',
        'tags': 'タグ',
        'ai_feedback': 'AI分析フィードバック',
        'no_notes': '選択された日付範囲に日記が見つかりませんでした。',
        'weather': '天気',
    },
}


def _get_labels(lang):
    return PDF_LABELS.get(lang, PDF_LABELS['zh-TW'])


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'CJKTitle', fontName=CJK_FONT, fontSize=24, leading=34,
        spaceAfter=18, alignment=1, textColor=colors.HexColor('#1e1b4b'),
    ))
    styles.add(ParagraphStyle(
        'CJKSubtitle', fontName=CJK_FONT, fontSize=13, leading=18,
        spaceAfter=12, alignment=1, textColor=colors.HexColor('#6b7280'),
    ))
    styles.add(ParagraphStyle(
        'CJKHeading', fontName=CJK_FONT, fontSize=15, leading=22,
        spaceAfter=8, spaceBefore=16, textColor=colors.HexColor('#4c1d95'),
    ))
    styles.add(ParagraphStyle(
        'CJKBody', fontName=CJK_FONT, fontSize=13, leading=20,
        spaceAfter=6, textColor=colors.HexColor('#1f2937'),
    ))
    styles.add(ParagraphStyle(
        'CJKSmall', fontName=CJK_FONT, fontSize=11, leading=16,
        textColor=colors.HexColor('#6b7280'),
    ))
    styles.add(ParagraphStyle(
        'CJKFeedback', fontName=CJK_FONT, fontSize=12, leading=18,
        spaceAfter=4, leftIndent=12,
        textColor=colors.HexColor('#7c3aed'),
    ))
    styles.add(ParagraphStyle(
        'CJKFeedbackLabel', fontName=CJK_FONT, fontSize=12, leading=18,
        spaceBefore=6, spaceAfter=2, leftIndent=12,
        textColor=colors.HexColor('#5b21b6'),
    ))
    return styles


def _escape(text):
    """Escape XML special chars for ReportLab Paragraph."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _format_ai_feedback(text, style):
    """Convert AI feedback text with newlines into multiple Paragraphs."""
    paragraphs = []
    escaped = _escape(text)
    # Split by newlines (handle \r\n, \n, and double newlines)
    lines = escaped.replace('\r\n', '\n').split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped:
            paragraphs.append(Paragraph(stripped, style))
        else:
            paragraphs.append(Spacer(1, 2 * mm))
    return paragraphs


def generate_notes_pdf(queryset, date_from=None, date_to=None, user=None, lang='zh-TW'):
    """Generate a PDF report of mood notes. Returns a BytesIO buffer."""
    labels = _get_labels(lang)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = _build_styles()
    story = []

    # Filter by date range
    qs = queryset.order_by('created_at')
    if date_from:
        try:
            dt = datetime.strptime(date_from, '%Y-%m-%d')
            qs = qs.filter(created_at__date__gte=dt.date())
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, '%Y-%m-%d')
            qs = qs.filter(created_at__date__lte=dt.date())
        except ValueError:
            pass

    notes = list(qs)

    # --- Title ---
    username = user.username if user else ''
    story.append(Paragraph(f'{labels["title"]} — {username}', styles['CJKTitle']))

    date_range_text = ''
    if date_from and date_to:
        date_range_text = f'{date_from} ~ {date_to}'
    elif date_from:
        date_range_text = f'{date_from} ~'
    elif date_to:
        date_range_text = f'~ {date_to}'
    if date_range_text:
        story.append(Paragraph(date_range_text, styles['CJKSubtitle']))

    story.append(Spacer(1, 6*mm))

    # --- Summary statistics ---
    total = len(notes)
    sentiments = [n.sentiment_score for n in notes if n.sentiment_score is not None]
    stresses = [n.stress_index for n in notes if n.stress_index is not None]
    avg_sent = round(sum(sentiments) / len(sentiments), 2) if sentiments else 'N/A'
    avg_stress = round(sum(stresses) / len(stresses), 1) if stresses else 'N/A'

    summary_data = [
        [labels['total_notes'], labels['avg_sentiment'], labels['avg_stress']],
        [str(total), str(avg_sent), str(avg_stress)],
    ]
    summary_table = Table(summary_data, colWidths=[55*mm, 55*mm, 55*mm])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), CJK_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTSIZE', (0, 1), (-1, 1), 15),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ede9fe')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f5f3ff')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c4b5fd')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8*mm))

    # --- Each note ---
    for note in notes:
        date_str = note.created_at.strftime('%Y-%m-%d %H:%M')
        story.append(Paragraph(f'{date_str}', styles['CJKHeading']))

        content = note.content or ''
        content = _escape(content)
        story.append(Paragraph(content, styles['CJKBody']))

        meta_parts = []
        if note.sentiment_score is not None:
            meta_parts.append(f'{labels["sentiment"]}: {note.sentiment_score}')
        if note.stress_index is not None:
            meta_parts.append(f'{labels["stress"]}: {note.stress_index}/10')
        weather = (note.metadata or {}).get('weather')
        if weather:
            meta_parts.append(f'{labels["weather"]}: {weather}')
        tags = (note.metadata or {}).get('tags', [])
        if tags:
            meta_parts.append(f'{labels["tags"]}: {", ".join(tags)}')
        if meta_parts:
            story.append(Paragraph(' | '.join(meta_parts), styles['CJKSmall']))

        if note.ai_feedback:
            story.append(Paragraph(f'<b>{labels["ai_feedback"]}</b>', styles['CJKFeedbackLabel']))
            feedback_parts = _format_ai_feedback(note.ai_feedback, styles['CJKFeedback'])
            story.extend(feedback_parts)

        story.append(Spacer(1, 4*mm))

    if not notes:
        story.append(Paragraph(labels['no_notes'], styles['CJKBody']))

    doc.build(story)
    buf.seek(0)
    return buf
