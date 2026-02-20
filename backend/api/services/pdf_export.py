import io
import os
import re
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
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
        'attachments': '附件圖片',
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
        'attachments': 'Attached Images',
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
        'attachments': '添付画像',
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


def _strip_emoji(text):
    """Remove emoji characters that CID fonts cannot render."""
    emoji_pattern = re.compile(
        r'[\U0001F300-\U0001F9FF'   # Misc Symbols, Emoticons, etc.
        r'\U00002600-\U000027BF'     # Misc symbols (sun, cloud, etc.)
        r'\U0000FE00-\U0000FE0F'     # Variation selectors
        r'\U0000200D'                 # Zero width joiner
        r'\U000020E3'                 # Combining enclosing keycap
        r']+', flags=re.UNICODE
    )
    return emoji_pattern.sub('', text).strip()


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

    # Filter by date range (prefetch image attachments)
    qs = queryset.prefetch_related('attachments').order_by('created_at')
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

    notes = list(qs[:1000])  # Cap at 1000 notes per PDF to prevent memory exhaustion

    # --- Title ---
    story.append(Paragraph(labels['title'], styles['CJKTitle']))
    username = user.username if user else ''
    if username:
        story.append(Paragraph(username, styles['CJKSubtitle']))

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
            meta_parts.append(f'{labels["weather"]}: {_strip_emoji(weather)}')
        tags = (note.metadata or {}).get('tags', [])
        if tags:
            meta_parts.append(f'{labels["tags"]}: {", ".join(tags)}')
        if meta_parts:
            story.append(Paragraph(' | '.join(meta_parts), styles['CJKSmall']))

        if note.ai_feedback:
            story.append(Paragraph(f'<b>{labels["ai_feedback"]}</b>', styles['CJKFeedbackLabel']))
            feedback_parts = _format_ai_feedback(note.ai_feedback, styles['CJKFeedback'])
            story.extend(feedback_parts)

        # Include image attachments
        image_attachments = [a for a in note.attachments.all() if a.file_type == 'image']
        if image_attachments:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(f'<b>{labels["attachments"]}</b>', styles['CJKFeedbackLabel']))
            for att in image_attachments:
                try:
                    img_path = att.file.path
                    if os.path.exists(img_path):
                        img = Image(img_path)
                        # Scale to fit within page width (max 150mm wide, 100mm tall)
                        max_w, max_h = 150*mm, 100*mm
                        iw, ih = img.drawWidth, img.drawHeight
                        if iw > max_w:
                            ratio = max_w / iw
                            iw, ih = iw * ratio, ih * ratio
                        if ih > max_h:
                            ratio = max_h / ih
                            iw, ih = iw * ratio, ih * ratio
                        img.drawWidth = iw
                        img.drawHeight = ih
                        story.append(img)
                        story.append(Spacer(1, 2*mm))
                except Exception:
                    pass  # Skip images that can't be loaded

        story.append(Spacer(1, 4*mm))

    if not notes:
        story.append(Paragraph(labels['no_notes'], styles['CJKBody']))

    doc.build(story)
    buf.seek(0)
    return buf


# i18n labels for weekly summary PDF
WEEKLY_PDF_LABELS = {
    'zh-TW': {
        'title': '每週心情報告',
        'note_count': '日記數',
        'avg_mood': '平均情緒',
        'avg_stress': '平均壓力',
        'top_activities': '熱門活動',
        'ai_summary': 'AI 智慧摘要',
        'diary_entries': '本週日記',
    },
    'en': {
        'title': 'Weekly Mood Summary',
        'note_count': 'Diary Entries',
        'avg_mood': 'Avg Mood',
        'avg_stress': 'Avg Stress',
        'top_activities': 'Top Activities',
        'ai_summary': 'AI Summary',
        'diary_entries': 'Diary Entries This Week',
    },
    'ja': {
        'title': '週間気分レポート',
        'note_count': '日記数',
        'avg_mood': '平均気分',
        'avg_stress': '平均ストレス',
        'top_activities': '人気活動',
        'ai_summary': 'AIサマリー',
        'diary_entries': '今週の日記',
    },
}


def generate_weekly_summary_pdf(summary, notes_qs, user, lang='zh-TW'):
    """Generate a PDF for a weekly summary including AI analysis and diary entries."""
    labels = WEEKLY_PDF_LABELS.get(lang, WEEKLY_PDF_LABELS['zh-TW'])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = _build_styles()
    story = []

    # Title
    story.append(Paragraph(labels['title'], styles['CJKTitle']))

    username = user.username if user else ''
    if username:
        story.append(Paragraph(username, styles['CJKSubtitle']))

    week_end = summary.week_start + timedelta(days=6)
    story.append(Paragraph(
        f'{summary.week_start} ~ {week_end}',
        styles['CJKSubtitle'],
    ))
    story.append(Spacer(1, 6*mm))

    # Summary statistics table
    mood_str = str(round(summary.mood_avg, 2)) if summary.mood_avg is not None else 'N/A'
    stress_str = str(round(summary.stress_avg, 1)) if summary.stress_avg is not None else 'N/A'

    summary_data = [
        [labels['note_count'], labels['avg_mood'], labels['avg_stress']],
        [str(summary.note_count), mood_str, stress_str],
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
    story.append(Spacer(1, 6*mm))

    # Top activities
    if summary.top_activities:
        story.append(Paragraph(f'<b>{labels["top_activities"]}</b>', styles['CJKHeading']))
        acts_text = ', '.join(
            f'{_strip_emoji(a["name"])} ({a["count"]})' for a in summary.top_activities
        )
        story.append(Paragraph(acts_text, styles['CJKBody']))
        story.append(Spacer(1, 4*mm))

    # AI Summary
    if summary.ai_summary:
        story.append(Paragraph(f'<b>{labels["ai_summary"]}</b>', styles['CJKHeading']))
        feedback_parts = _format_ai_feedback(summary.ai_summary, styles['CJKBody'])
        story.extend(feedback_parts)
        story.append(Spacer(1, 6*mm))

    # Diary entries
    notes = list(notes_qs[:100])
    if notes:
        story.append(Paragraph(f'<b>{labels["diary_entries"]}</b>', styles['CJKHeading']))
        story.append(Spacer(1, 2*mm))
        for note in notes:
            date_str = note.created_at.strftime('%Y-%m-%d %H:%M')
            story.append(Paragraph(date_str, styles['CJKSmall']))
            content = note.content or ''
            story.append(Paragraph(_escape(content), styles['CJKBody']))
            story.append(Spacer(1, 3*mm))

    doc.build(story)
    buf.seek(0)
    return buf
