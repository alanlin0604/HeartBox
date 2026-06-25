"""AI companion chat (HeartBot / 小心).

Talks to the LLM via ``api.services.llm.get_llm_provider()`` — no vendor SDK
imported here. Crisis-keyword detection runs against the latest user message
so the safety preamble + hotline string is prepended even if the underlying
model misbehaves.
"""
import logging

from api.services.llm import LLMProviderError, get_llm_provider
from api.services.llm.crisis_guard import CrisisGuard
from api.services.llm.sanitize import detect_system_echo, scrub_llm_output

logger = logging.getLogger(__name__)

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


def _locale_for_crisis(lang: str) -> str:
    """Map ai_chat lang code to CrisisGuard's Locale type."""
    if lang in ('zh-TW', 'en', 'ja'):
        return lang
    return 'zh-TW'


def analyze_user_message(text):
    """Quick local sentiment analysis (no provider call)."""
    from api.services.ai_engine import AIEngine
    words = AIEngine._segment_text(text)
    return AIEngine._analyze_sentiment_local(words)


def generate_ai_response(session_messages, lang='zh-TW'):
    """Generate the next AI turn given conversation history.

    Calls the configured LLM provider with the last 20 messages.
    Falls back to a canned response on any provider error.
    """
    system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS['zh-TW'])

    # Inspect the latest user message for crisis signals before sending.
    last_user_text = ''
    for msg in reversed(session_messages):
        if getattr(msg, 'role', None) == 'user':
            last_user_text = getattr(msg, 'content', '') or ''
            break

    crisis = CrisisGuard.detect(last_user_text, locale=_locale_for_crisis(lang))
    if crisis is not None:
        system_prompt = CrisisGuard.inject_preamble(system_prompt, crisis.locale)

    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in session_messages[-20:]:
        messages.append({
            'role': msg.role,
            'content': msg.content,
        })

    provider = get_llm_provider()
    if not provider.is_configured():
        logger.warning('LLM provider not configured, returning fallback response')
        return FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES['zh-TW'])

    try:
        reply = provider.chat_messages(
            messages=messages,
            temperature=0.8,
            max_tokens=500,
        )
    except (LLMProviderError, Exception) as e:
        logger.warning('AI chat response generation failed: %s', e)
        return FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES['zh-TW'])

    # Consumer-side scrub. ORDER MATTERS — must run BEFORE hotline prepend
    # so the canonical hotline string isn't itself flagged as echo. ai_chat
    # is doubly risky: (a) reply renders directly to UI; (b) AIChatMessage
    # row persists the content and the next turn feeds it back as history,
    # so a leak self-reinforces unless killed at write time.
    reply = scrub_llm_output(reply)
    base_system = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS['zh-TW'])
    if not reply or detect_system_echo(reply, base_system):
        logger.warning(
            'ai_chat system_echo_or_empty detected lang=%s reply_len=%d',
            lang, len(reply),
        )
        return FALLBACK_RESPONSES.get(lang, FALLBACK_RESPONSES['zh-TW'])

    # Defense-in-depth: even if the model ignored the preamble, prepend hotline.
    if crisis is not None and crisis.severity == 'HIGH':
        reply = CrisisGuard.prepend_hotline(reply, crisis.locale)
    return reply
