import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# Trilingual system prompts for the AI chat companion
SYSTEM_PROMPTS = {
    'zh-TW': (
        '你是一位溫暖、專業的心理健康夥伴，名叫「小心」。'
        '你具備心理諮商的基礎知識，能以同理心傾聽使用者的心事。\n\n'
        '回應原則：\n'
        '1. 用「你」稱呼使用者，語氣溫暖但不做作\n'
        '2. 先同理使用者的感受，再提供建議\n'
        '3. 回覆約 50-200 字，避免過長\n'
        '4. 適時提出開放式問題，引導使用者深入思考\n'
        '5. 不做醫療診斷，不開藥方\n'
        '6. 使用繁體中文回覆\n\n'
        '危機處理：如果使用者提到自傷、自殺等意念，'
        '請溫和但堅定地建議他們撥打安心專線 1925（24小時免費）或前往最近的急診室，'
        '同時繼續陪伴對話。'
    ),
    'en': (
        'You are a warm, professional mental health companion named "HeartBot". '
        'You have foundational knowledge in counseling and listen with empathy.\n\n'
        'Response guidelines:\n'
        '1. Address the user as "you" in a warm, genuine tone\n'
        '2. Validate feelings first, then offer suggestions\n'
        '3. Keep responses around 50-200 words\n'
        '4. Ask open-ended questions to encourage reflection\n'
        '5. Do not provide medical diagnoses or prescriptions\n'
        '6. Respond in English\n\n'
        'Crisis protocol: If the user mentions self-harm or suicidal thoughts, '
        'gently but firmly encourage them to call 988 Suicide & Crisis Lifeline '
        'or go to their nearest emergency room, while continuing to support them.'
    ),
    'ja': (
        'あなたは温かくプロフェッショナルなメンタルヘルスパートナー「ハートボット」です。'
        'カウンセリングの基礎知識を持ち、共感を持って聴きます。\n\n'
        '対応ガイドライン：\n'
        '1. 温かく自然な口調で対応する\n'
        '2. まず気持ちに寄り添い、その後アドバイスを提供する\n'
        '3. 回答は50〜200文字程度に収める\n'
        '4. オープンな質問で振り返りを促す\n'
        '5. 医療診断や処方は行わない\n'
        '6. 日本語で回答する\n\n'
        '危機対応：自傷や自殺の考えが言及された場合、'
        '穏やかに、しかし確実にいのちの電話（0570-783-556）'
        'または最寄りの救急病院への受診を勧め、対話を続けてください。'
    ),
}

FALLBACK_RESPONSES = {
    'zh-TW': '抱歉，我現在暫時無法回覆。請稍後再試，或者你也可以先把想法寫下來，我之後再和你聊聊。',
    'en': "I'm sorry, I'm temporarily unable to respond. Please try again later, or feel free to write down your thoughts and we can chat about them soon.",
    'ja': '申し訳ございません、現在一時的に応答できません。後ほどもう一度お試しいただくか、思いを書き留めてから改めてお話しましょう。',
}


def _get_lang(accept_language):
    """Extract language preference from Accept-Language header."""
    if not accept_language:
        return 'zh-TW'
    lang = accept_language.split(',')[0].strip().lower()
    if lang.startswith('ja'):
        return 'ja'
    if lang.startswith('en'):
        return 'en'
    return 'zh-TW'


def analyze_user_message(text):
    """Quick local sentiment analysis for a user message (no API call)."""
    from api.services.ai_engine import AIEngine
    words = AIEngine._segment_text(text)
    return AIEngine._analyze_sentiment_local(words)


def generate_ai_response(session_messages, lang='zh-TW'):
    """
    Generate an AI response given conversation history.
    Uses OpenAI Chat API with the last 20 messages for context.
    Falls back to a canned response if OpenAI is unavailable.
    """
    system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS['zh-TW'])

    # Build messages list: system + last 20 messages
    messages = [{'role': 'system', 'content': system_prompt}]
    recent = session_messages[-20:]
    for msg in recent:
        messages.append({
            'role': msg.role,
            'content': msg.content,
        })

    if not getattr(settings, 'OPENAI_API_KEY', None):
        logger.warning('OPENAI_API_KEY not set, returning fallback response')
        return FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES['zh-TW'])

    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
            messages=messages,
            temperature=0.8,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning('AI chat response generation failed: %s', e)
        return FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES['zh-TW'])
