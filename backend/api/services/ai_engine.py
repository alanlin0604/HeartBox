import json
import logging
import os
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

# Local keyword-based sentiment dictionaries
_POSITIVE_WORDS = {
    '開心', '快樂', '高興', '幸福', '愉快', '滿足', '感恩', '感謝', '棒', '讚',
    '好', '美好', '喜歡', '愛', '溫暖', '舒服', '輕鬆', '自在', '希望', '期待',
    '興奮', '驚喜', '成功', '順利', '進步', '成長', '充實', '能量', '活力', '享受',
    '樂', '笑', '甜', '暖', '陽光', '美', '贊', '太好了', '開朗', '正面',
    '平靜', '安心', '踏實', '放鬆', '悠閒', '自由', '精彩', '完美', '優秀', '厲害',
}
_NEGATIVE_WORDS = {
    '難過', '傷心', '痛苦', '焦慮', '壓力', '煩', '煩躁', '生氣', '憤怒', '失望',
    '沮喪', '憂鬱', '孤單', '寂寞', '害怕', '恐懼', '擔心', '緊張', '累', '疲憊',
    '無聊', '無力', '崩潰', '絕望', '悲傷', '哭', '淚', '糟糕', '討厭', '恨',
    '煩惱', '不安', '挫折', '委屈', '失落', '迷茫', '困惑', '無奈', '後悔', '自責',
    '痛', '苦', '慘', '差', '爛', '厭', '怒', '鬱悶', '低落', '消沉',
}
_STRESS_WORDS = {
    '壓力', '焦慮', '緊張', '崩潰', '失眠', '頭痛', '加班', '趕', 'deadline',
    '考試', '報告', '來不及', '忙', '喘不過氣', '受不了', '撐不住', '太多', '爆',
}


class AIEngine:
    """Singleton AI engine for sentiment analysis + RAG feedback."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._chroma_collection = None
                    cls._instance._retriever = None
        return cls._instance

    # --- Chinese text segmentation ---

    @staticmethod
    def _segment_text(text: str) -> list[str]:
        try:
            import jieba
            return list(jieba.cut(text))
        except Exception:
            return list(text)

    # --- Local keyword sentiment analysis (no API needed) ---

    @staticmethod
    def _analyze_sentiment_local(words: list[str]) -> dict:
        pos = sum(1 for w in words if w in _POSITIVE_WORDS)
        neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
        stress_hits = sum(1 for w in words if w in _STRESS_WORDS)

        total = pos + neg
        if total == 0:
            score = 0.0
        else:
            score = round((pos - neg) / total, 2)
            score = max(-1.0, min(1.0, score))

        stress = min(10, round(stress_hits * 2.5 + (neg * 0.8)))
        if score > 0.3:
            stress = max(0, stress - 2)

        return {
            'sentiment_score': score,
            'stress_index': max(0, min(10, stress)),
        }

    # --- Sentiment Analysis via OpenAI ---

    def _analyze_sentiment_openai(self, text: str) -> dict:
        """Call OpenAI to get sentiment_score and stress_index as JSON."""
        from openai import OpenAI

        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = (
            '你是一位心理健康分析專家。分析以下日記內容的情緒狀態，'
            '回傳 JSON 格式：{"sentiment_score": float (-1.0到1.0, 負面到正面), '
            '"stress_index": int (0到10, 0=平靜 10=極度壓力)}。'
            '只回傳 JSON，不要其他文字。\n\n'
            f'日記內容：{text[:1500]}'
        )
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        return json.loads(raw)

    # --- RAG Feedback (for negative sentiment) ---

    def _get_retriever(self):
        """Lazy-load ChromaDB retriever."""
        if self._retriever is not None:
            return self._retriever

        try:
            import chromadb
            from langchain_chroma import Chroma
            from langchain_openai import OpenAIEmbeddings

            persist_dir = settings.CHROMA_PERSIST_DIR
            if not os.path.exists(persist_dir):
                logger.info('ChromaDB directory not found — RAG unavailable')
                return None

            embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
            vectorstore = Chroma(
                persist_directory=persist_dir,
                embedding_function=embeddings,
                collection_name='psychology_kb',
            )
            if vectorstore._collection.count() == 0:
                logger.info('ChromaDB collection is empty — RAG unavailable')
                return None

            self._retriever = vectorstore.as_retriever(search_kwargs={'k': 3})
            return self._retriever
        except Exception as e:
            logger.warning(f'Failed to init ChromaDB retriever: {e}')
            return None

    def _generate_personalized_feedback(self, text: str, sentiment_score: float) -> str:
        """Generate personalized feedback based on actual journal content using OpenAI."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            if sentiment_score >= 0.3:
                tone_hint = '使用者心情偏正面，回覆時肯定他們的正向經歷，並鼓勵繼續保持。'
            elif sentiment_score >= -0.2:
                tone_hint = '使用者心情平穩或略有起伏，回覆時溫和陪伴，提供實用的日常調適建議。'
            elif sentiment_score >= -0.5:
                tone_hint = '使用者心情偏低落，回覆時展現同理與理解，提供具體的情緒調適方法。'
            else:
                tone_hint = '使用者承受較大壓力或情緒低落，回覆時展現深度同理，提供專業的心理調適建議，必要時建議尋求專業協助。'

            prompt = (
                '你是一位溫暖、專業的心理健康顧問。請根據以下使用者的日記內容，'
                '給出客製化的回饋。\n\n'
                '要求：\n'
                '1. 必須回應日記中提到的具體事件、人物或感受，不要給出泛泛的建議\n'
                '2. 用「你」稱呼使用者，語氣溫暖但不做作\n'
                '3. 給出 2-3 點針對日記內容的具體建議或回饋\n'
                '4. 回覆長度約 80-150 字\n'
                '5. 使用繁體中文\n'
                f'6. {tone_hint}\n\n'
                f'日記內容：\n「{text[:800]}」'
            )
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.8,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f'Personalized feedback failed: {e}')
            return self._generate_basic_feedback(sentiment_score)

    def _generate_rag_feedback(self, text: str, sentiment_score: float) -> str:
        """Use LangChain RetrievalQA + ChromaDB to generate psychology-backed advice."""
        retriever = self._get_retriever()
        if retriever is None:
            return self._generate_personalized_feedback(text, sentiment_score)

        try:
            from langchain.chains import RetrievalQA
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7,
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type='stuff',
                retriever=retriever,
            )
            query = (
                f'使用者寫了以下日記（情緒分數 {sentiment_score}，偏負面）：\n'
                f'「{text[:500]}」\n\n'
                '請根據心理學知識，針對日記中提到的具體事件與感受，'
                '用溫暖、同理的語氣，提供 2-3 點具體建議來幫助使用者。'
                '回覆請用繁體中文。'
            )
            result = qa_chain.invoke({'query': query})
            return result.get('result', self._generate_personalized_feedback(text, sentiment_score))
        except Exception as e:
            logger.warning(f'RAG feedback failed: {e}')
            return self._generate_personalized_feedback(text, sentiment_score)

    # --- Basic Feedback ---

    @staticmethod
    def _generate_basic_feedback(sentiment_score: float) -> str:
        if sentiment_score >= 0.5:
            return (
                '你今天的心情看起來很不錯！繼續保持正向的心態，記得也要適時休息。\n\n'
                '建議：\n'
                '1. 把今天的好心情記錄下來，未來低潮時可以回顧\n'
                '2. 和身邊的人分享你的快樂，正面情緒是會感染的'
            )
        elif sentiment_score >= 0.1:
            return (
                '你今天的狀態看起來還算平穩，這很好。\n\n'
                '建議：\n'
                '1. 試著做一些讓自己開心的小事，比如散步、聽音樂或吃喜歡的食物\n'
                '2. 保持規律的作息，穩定的生活節奏有助於維持好心情'
            )
        elif sentiment_score >= -0.3:
            return (
                '看起來你今天的心情有些起伏，這是很正常的。\n\n'
                '建議：\n'
                '1. 試著深呼吸幾次，讓自己慢下來\n'
                '2. 如果有煩心的事，可以試著寫下來釐清思緒\n'
                '3. 適度運動可以幫助釋放壓力，即使只是短暫散步也好'
            )
        elif sentiment_score >= -0.6:
            return (
                '看起來你今天有些低落，辛苦了。請記得，低潮是暫時的。\n\n'
                '建議：\n'
                '1. 試著和信任的朋友或家人聊聊，傾訴本身就是一種療癒\n'
                '2. 做一些讓自己放鬆的事——泡杯熱茶、聽輕柔的音樂、洗個熱水澡\n'
                '3. 提醒自己：你已經很努力了，不需要對自己太苛刻'
            )
        else:
            return (
                '我注意到你現在可能承受了不少壓力，你的感受是被理解的。\n\n'
                '建議：\n'
                '1. 允許自己感受這些情緒，不需要壓抑或否認\n'
                '2. 試著做腹式呼吸：吸氣4秒、憋住4秒、吐氣6秒，重複幾次\n'
                '3. 如果持續感到困擾，建議尋求專業心理諮商師的協助\n\n'
                '你並不孤單，有需要請撥打安心專線：1925（24小時免費）'
            )

    # --- Vision-based analysis (with images) ---

    def analyze_with_images(self, text: str, image_urls: list[str]) -> dict:
        """
        Re-analyze journal text together with attached images using GPT-4o-mini vision.
        Returns dict with sentiment_score, stress_index, ai_feedback.
        """
        result = {
            'sentiment_score': None,
            'stress_index': None,
            'ai_feedback': '',
        }

        if not settings.OPENAI_API_KEY:
            return self.analyze(text)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Build multimodal content blocks (max 3 images, low detail)
            content_blocks = [
                {
                    'type': 'text',
                    'text': (
                        '你是一位心理健康分析專家。分析以下日記內容與附件圖片的情緒狀態，'
                        '請同時參考圖片內容來理解使用者的情緒和狀況。'
                        '回傳 JSON 格式：{"sentiment_score": float (-1.0到1.0, 負面到正面), '
                        '"stress_index": int (0到10, 0=平靜 10=極度壓力)}。'
                        '只回傳 JSON，不要其他文字。\n\n'
                        f'日記內容：{text[:1500]}'
                    ),
                },
            ]
            for url in image_urls[:3]:
                content_blocks.append({
                    'type': 'image_url',
                    'image_url': {'url': url, 'detail': 'low'},
                })

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{'role': 'user', 'content': content_blocks}],
                temperature=0.3,
                max_tokens=100,
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
            sentiment_data = json.loads(raw)

            score = float(sentiment_data.get('sentiment_score', 0))
            stress = int(sentiment_data.get('stress_index', 5))
            result['sentiment_score'] = max(-1.0, min(1.0, score))
            result['stress_index'] = max(0, min(10, stress))

            # Generate feedback with image context
            feedback_blocks = [
                {
                    'type': 'text',
                    'text': (
                        '你是一位溫暖、專業的心理健康顧問。請根據以下使用者的日記內容與附件圖片，'
                        '給出客製化的回饋。\n\n'
                        '要求：\n'
                        '1. 必須回應日記中提到的具體事件、人物或感受，也要提及圖片中觀察到的內容\n'
                        '2. 用「你」稱呼使用者，語氣溫暖但不做作\n'
                        '3. 給出 2-3 點針對日記內容與圖片的具體建議或回饋\n'
                        '4. 回覆長度約 80-150 字\n'
                        '5. 使用繁體中文\n\n'
                        f'日記內容：\n「{text[:800]}」'
                    ),
                },
            ]
            for url in image_urls[:3]:
                feedback_blocks.append({
                    'type': 'image_url',
                    'image_url': {'url': url, 'detail': 'low'},
                })

            feedback_response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{'role': 'user', 'content': feedback_blocks}],
                temperature=0.8,
                max_tokens=300,
            )
            result['ai_feedback'] = feedback_response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f'Vision analysis failed, falling back to text-only: {e}')
            return self.analyze(text)

        return result

    # --- Main entry point ---

    def analyze(self, text: str) -> dict:
        """
        Analyze journal text. Returns dict with sentiment_score, stress_index, ai_feedback.
        Three-tier strategy:
          1. OpenAI API (best quality)
          2. Local keyword analysis (fallback when API unavailable)
          3. Graceful degradation (note always savable)
        """
        result = {
            'sentiment_score': None,
            'stress_index': None,
            'ai_feedback': '',
        }

        # Always do local segmentation
        words = self._segment_text(text)

        # Tier 1: Try OpenAI
        openai_success = False
        if settings.OPENAI_API_KEY:
            try:
                sentiment_data = self._analyze_sentiment_openai(text)
                score = float(sentiment_data.get('sentiment_score', 0))
                stress = int(sentiment_data.get('stress_index', 5))
                result['sentiment_score'] = max(-1.0, min(1.0, score))
                result['stress_index'] = max(0, min(10, stress))
                openai_success = True

                # Dual-layer feedback: RAG for very negative, personalized for others
                if score < -0.4:
                    result['ai_feedback'] = self._generate_rag_feedback(text, score)
                else:
                    result['ai_feedback'] = self._generate_personalized_feedback(text, score)

            except Exception as e:
                logger.warning(f'OpenAI analysis failed, falling back to local: {e}')

        # Tier 2: Local keyword analysis
        if not openai_success:
            try:
                local_data = self._analyze_sentiment_local(words)
                result['sentiment_score'] = local_data['sentiment_score']
                result['stress_index'] = local_data['stress_index']
                result['ai_feedback'] = self._generate_basic_feedback(local_data['sentiment_score'])
                logger.info(f'Local analysis: score={local_data["sentiment_score"]}, stress={local_data["stress_index"]}')
            except Exception as e:
                logger.error(f'Local analysis also failed: {e}')
                result['ai_feedback'] = '分析暫時無法使用，但你的日記已安全儲存。'

        return result


ai_engine = AIEngine()
