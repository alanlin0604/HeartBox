"""FastAPI app for HeartBox local LLM inference.

Endpoints
---------
GET  /health         — no auth; uptime ping
POST /v1/chat/completions       — OpenAI-shaped, X-API-Key required
POST /v1/chat_json              — same as above but parses model output to dict
POST /v1/vision                 — multimodal call (LLaVA)
POST /v1/switch_model           — explicit ``{"target": "taide"|"llava"}`` for ops

Hardening
---------
* X-API-Key compared with ``hmac.compare_digest``.
* CORS strict allowlist from env (no wildcards).
* Request body >100KB rejected at the ASGI layer with 413.
* Per-request 60s timeout via asyncio.wait_for.
* No swagger / openapi docs exposed.
"""
from __future__ import annotations

import asyncio
import hmac
import io
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Literal

logger = logging.getLogger(__name__)

# --- Optional FastAPI imports guarded for early-collection tooling.
try:
    from fastapi import FastAPI, Header, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    _HAS_FASTAPI = False

from .config import Settings
from .engine import InferenceEngine, best_effort_json


# ----------------------------------------------------------------------
# Pydantic request models — OpenAI shape.
# ----------------------------------------------------------------------
if _HAS_FASTAPI:
    class _ChatMessage(BaseModel):
        role: Literal['system', 'user', 'assistant']
        content: object  # string or list[dict] for multimodal

    class ChatCompletionsRequest(BaseModel):
        model: str | None = None
        messages: list[_ChatMessage] = Field(..., min_length=1)
        temperature: float = Field(0.7, ge=0.0, le=2.0)
        max_tokens: int = Field(500, ge=1, le=4096)
        stream: bool = False

    class ChatJsonRequest(BaseModel):
        model: str | None = None
        system: str
        user: str
        schema_hint: str | None = None
        temperature: float = Field(0.3, ge=0.0, le=2.0)
        max_tokens: int = Field(200, ge=1, le=2048)

    class VisionRequest(BaseModel):
        model: str | None = None
        messages: list[_ChatMessage] = Field(..., min_length=1)
        image_urls: list[str] = Field(default_factory=list)
        temperature: float = Field(0.7, ge=0.0, le=2.0)
        max_tokens: int = Field(300, ge=1, le=2048)

    class SwitchModelRequest(BaseModel):
        target: Literal['taide', 'llava']


# ----------------------------------------------------------------------
# Image fetch helper — kept tight (5s per image, 15s total, content-type check).
# ----------------------------------------------------------------------
async def _fetch_images(urls: list[str], *, max_total: int = 3) -> list:
    """Fetch images concurrently with budget. Returns PIL.Image list."""
    import httpx
    from PIL import Image

    if not urls:
        return []
    urls = urls[:max_total]

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=3.0),
        follow_redirects=True,
        max_redirects=3,
    ) as client:
        async def _one(url: str):
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'rejected non-http url: {url[:40]}')
            r = await client.get(url)
            r.raise_for_status()
            ct = r.headers.get('content-type', '').lower()
            if not ct.startswith('image/'):
                raise ValueError(f'rejected non-image content-type: {ct}')
            if len(r.content) > 8 * 1024 * 1024:
                raise ValueError('image > 8MB')
            img = Image.open(io.BytesIO(r.content))
            img.verify()
            return Image.open(io.BytesIO(r.content)).convert('RGB')

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*(_one(u) for u in urls)),
                timeout=15.0,
            )
        except asyncio.TimeoutError as e:
            raise ValueError('image batch fetch exceeded 15s') from e
        return list(results)


# ----------------------------------------------------------------------
# App factory.
# ----------------------------------------------------------------------
def create_app(settings: Settings | None = None) -> 'FastAPI':
    if not _HAS_FASTAPI:
        raise RuntimeError('FastAPI not installed. pip install fastapi uvicorn')

    settings = settings or Settings()

    if not settings.api_key:
        raise RuntimeError(
            'API_KEY missing. Set it in ~/.heartbox-llm.env or env var API_KEY.'
        )

    if settings.hf_home:
        os.environ['HF_HOME'] = settings.hf_home

    engine = InferenceEngine(
        taide_model_id=settings.taide_model_id,
        llava_model_id=settings.llava_model_id,
        bnb_disable=settings.bnb_disable,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.autoload_on_startup:
            await asyncio.to_thread(engine.load_taide)
        yield
        engine._release_model()

    app = FastAPI(
        title='HeartBox LLM Server',
        version='0.1.0',
        docs_url=None,         # no swagger on a public tunnel
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=False,
            allow_methods=['POST', 'GET'],
            allow_headers=['Content-Type', 'X-API-Key'],
        )

    # ------------------------------------------------------------------
    # Body-size middleware (Starlette has no default limit).
    # ------------------------------------------------------------------
    @app.middleware('http')
    async def _body_size_limit(request: Request, call_next):
        cl = request.headers.get('content-length')
        if cl and int(cl) > settings.body_limit_bytes:
            return JSONResponse({'detail': 'body too large'}, status_code=413)
        rid = request.headers.get('x-request-id') or str(uuid.uuid4())
        request.state.request_id = rid
        return await call_next(request)

    # ------------------------------------------------------------------
    # Auth — constant-time compare.
    # ------------------------------------------------------------------
    def _require_key(x_api_key: str | None) -> None:
        if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
            raise HTTPException(401, 'invalid API key')

    # ------------------------------------------------------------------
    # Routes.
    # ------------------------------------------------------------------
    @app.get('/health')
    async def health():
        return {
            'status': 'ok',
            'current_model': engine._current,
            'taide_model': settings.taide_model_id,
            'llava_model': settings.llava_model_id,
        }

    @app.post('/v1/chat/completions')
    async def chat_completions(
        req: ChatCompletionsRequest,
        x_api_key: str | None = Header(None, alias='X-API-Key'),
    ):
        _require_key(x_api_key)
        try:
            result = await engine.chat(
                [m.model_dump() for m in req.messages],
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                timeout_s=float(settings.request_timeout_s),
            )
        except TimeoutError:
            raise HTTPException(504, 'generation timeout')
        # Repack into OpenAI shape for client compatibility.
        return {
            'id': f'cmpl-{uuid.uuid4().hex[:12]}',
            'object': 'chat.completion',
            'model': result['model'],
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': result['reply']},
                'finish_reason': 'stop',
            }],
            'usage': {
                'prompt_tokens': result['tokens_in'],
                'completion_tokens': result['tokens_out'],
                'total_tokens': result['tokens_in'] + result['tokens_out'],
            },
            'latency_ms': result['latency_ms'],
        }

    @app.post('/v1/chat_json')
    async def chat_json(
        req: ChatJsonRequest,
        x_api_key: str | None = Header(None, alias='X-API-Key'),
    ):
        _require_key(x_api_key)
        sys_with_hint = req.system
        if req.schema_hint:
            sys_with_hint = (
                f'{req.system}\n\n'
                f'你必須只回傳一個 JSON 物件，符合此 schema: {req.schema_hint}\n'
                '不要回傳 markdown、解釋文字 — 只有 JSON。'
            )
        try:
            result = await engine.chat(
                [
                    {'role': 'system', 'content': sys_with_hint},
                    {'role': 'user', 'content': req.user},
                ],
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                timeout_s=float(settings.request_timeout_s),
            )
        except TimeoutError:
            raise HTTPException(504, 'generation timeout')

        parsed = best_effort_json(result['reply'])
        return {
            'raw': result['reply'],
            'parsed': parsed,
            'model': result['model'],
            'latency_ms': result['latency_ms'],
            'usage': {
                'prompt_tokens': result['tokens_in'],
                'completion_tokens': result['tokens_out'],
            },
        }

    @app.post('/v1/vision')
    async def vision(
        req: VisionRequest,
        x_api_key: str | None = Header(None, alias='X-API-Key'),
    ):
        _require_key(x_api_key)
        try:
            images = await _fetch_images(req.image_urls)
        except ValueError as e:
            raise HTTPException(400, str(e))

        try:
            result = await engine.vision(
                [m.model_dump() for m in req.messages],
                images,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                timeout_s=float(max(settings.request_timeout_s, 120)),
            )
        except TimeoutError:
            raise HTTPException(504, 'vision generation timeout')
        return {
            'id': f'visn-{uuid.uuid4().hex[:12]}',
            'object': 'vision.completion',
            'model': result['model'],
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': result['reply']},
                'finish_reason': 'stop',
            }],
            'usage': {
                'prompt_tokens': result['tokens_in'],
                'completion_tokens': result['tokens_out'],
            },
            'latency_ms': result['latency_ms'],
        }

    @app.post('/v1/switch_model')
    async def switch_model(
        req: SwitchModelRequest,
        x_api_key: str | None = Header(None, alias='X-API-Key'),
    ):
        _require_key(x_api_key)
        async with engine._swap_lock:
            await engine.swap_to(req.target)
        return {'current_model': engine._current}

    return app
