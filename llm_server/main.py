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
* X-API-Key compared with ``hmac.compare_digest``, IN MIDDLEWARE — before
  the body is parsed by Pydantic. Unauth requests never reach JSON parse.
* CORS strict allowlist from env (no wildcards).
* Request body >100KB rejected at the ASGI layer with 413; ``Transfer-
  Encoding: chunked`` is refused with 411 so an attacker can't bypass the
  size cap by omitting Content-Length.
* Per-request 60s timeout enforced via ``StoppingCriteria`` + thread join,
  not just ``asyncio.wait_for`` — so timed-out requests do not leak HF
  threads holding a GPU model.
* No swagger / openapi docs exposed.

SSRF / decompression-bomb defense
---------------------------------
* ``_fetch_images`` resolves every URL's host via ``getaddrinfo`` and
  rejects any address that is private, loopback, link-local, reserved,
  multicast, or unspecified. Redirects are disabled outright — a 302
  could otherwise land on metadata services or internal hosts.
* ``Image.MAX_IMAGE_PIXELS`` is hard-clamped and the decompression-bomb
  warning is promoted to an exception so a 200-byte JPEG that decompresses
  to 100MP cannot OOM the process.
"""
from __future__ import annotations

import asyncio
import hmac
import io
import ipaddress
import logging
import os
import socket
import uuid
import warnings
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# --- Optional FastAPI imports guarded for early-collection tooling.
try:
    from fastapi import FastAPI, HTTPException, Request
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
# PIL safety knobs — set once, on first image fetch.
# ----------------------------------------------------------------------
_MAX_IMAGE_PIXELS = 4096 * 4096   # 16 MP cap regardless of declared dims
_PIL_SAFETY_DONE = False


def _init_pil_safety() -> None:
    """Hard-cap PIL pixel count and promote bomb warnings to exceptions.

    Idempotent — only executes once per process. Without this, a 200-byte
    JPEG declaring 100,000 x 100,000 pixels would still attempt to decode
    a 30GB buffer in ``convert('RGB')``."""
    global _PIL_SAFETY_DONE
    if _PIL_SAFETY_DONE:
        return
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = _MAX_IMAGE_PIXELS
    warnings.simplefilter('error', Image.DecompressionBombWarning)
    _PIL_SAFETY_DONE = True


def _resolve_and_check_host(host: str) -> None:
    """Resolve ``host`` and reject if ANY resolved IP is non-public.

    Defends against SSRF: an attacker-supplied URL pointing to
    ``169.254.169.254`` (AWS metadata), ``127.0.0.1`` (local services),
    ``10.x`` / ``172.16-31.x`` / ``192.168.x`` (RFC1918), or link-local
    addresses must NOT be fetched. We check every address ``getaddrinfo``
    returns — DNS could legitimately resolve to A + AAAA records, but the
    moment one is internal we reject the whole URL (else an attacker could
    flip between calls).

    Raises ``ValueError`` on rejection (caller maps to 400).
    """
    if not host:
        raise ValueError('empty host in url')
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f'dns resolution failed for {host!r}') from e
    if not infos:
        raise ValueError(f'no addresses for {host!r}')
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            # Shouldn't happen — getaddrinfo returns IPs — but reject
            # rather than continue on something we can't classify.
            raise ValueError(f'unparseable address {ip_str!r} for {host!r}')
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError(
                f'rejected non-public host: {host} -> {ip_str}'
            )


# ----------------------------------------------------------------------
# Image fetch helper — kept tight (5s per image, 15s total, content-type check).
# ----------------------------------------------------------------------
async def _fetch_images(urls: list[str], *, max_total: int = 3) -> list:
    """Fetch images concurrently with budget. Returns PIL.Image list.

    Hardening: blocks non-http schemes, SSRF (private/loopback resolution),
    redirect-based SSRF (follow_redirects=False), oversize payloads, and
    PIL decompression bombs.
    """
    import httpx
    from PIL import Image

    if not urls:
        return []
    urls = urls[:max_total]
    _init_pil_safety()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=3.0),
        follow_redirects=False,   # SSRF: a 302 to 169.254.169.254 would bypass the host check.
        max_redirects=0,
    ) as client:
        async def _one(url: str):
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'rejected non-http url: {url[:40]}')
            parsed = urlparse(url)
            # getaddrinfo blocks — run in a thread so the event loop stays
            # responsive when DNS is slow.
            await asyncio.to_thread(_resolve_and_check_host, parsed.hostname or '')
            r = await client.get(url)
            if r.status_code in (301, 302, 303, 307, 308):
                raise ValueError(
                    f'rejected redirect {r.status_code} to '
                    f'{r.headers.get("location", "?")[:80]}'
                )
            r.raise_for_status()
            ct = r.headers.get('content-type', '').lower()
            if not ct.startswith('image/'):
                raise ValueError(f'rejected non-image content-type: {ct}')
            if len(r.content) > 8 * 1024 * 1024:
                raise ValueError('image > 8MB')
            # Open without decoding pixels to inspect declared dimensions.
            head = Image.open(io.BytesIO(r.content))
            w, h = head.size
            if w * h > _MAX_IMAGE_PIXELS:
                raise ValueError(f'image too large: {w}x{h} ({w*h:,} pixels)')
            head.verify()
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
    # Body-size middleware. Two attack shapes to defuse:
    #   1. Honest oversize: Content-Length > cap → 413.
    #   2. Chunked-encoding bypass: ``Transfer-Encoding: chunked`` omits
    #      Content-Length so the prior check let unlimited bodies through.
    #      We refuse chunked uploads outright — clients to this server
    #      never need streaming.
    # Also a malformed Content-Length (negative, non-int) → 400 not crash.
    # ------------------------------------------------------------------
    @app.middleware('http')
    async def _body_size_limit(request: Request, call_next):
        te = request.headers.get('transfer-encoding', '').lower()
        if 'chunked' in te:
            return JSONResponse(
                {'detail': 'chunked transfer-encoding not supported'},
                status_code=411,
            )
        cl = request.headers.get('content-length')
        if cl is not None:
            try:
                cl_int = int(cl)
            except (TypeError, ValueError):
                return JSONResponse(
                    {'detail': 'invalid Content-Length'}, status_code=400,
                )
            if cl_int < 0 or cl_int > settings.body_limit_bytes:
                return JSONResponse(
                    {'detail': 'body too large'}, status_code=413,
                )
        rid = request.headers.get('x-request-id') or str(uuid.uuid4())
        request.state.request_id = rid
        return await call_next(request)

    # ------------------------------------------------------------------
    # Auth middleware. Runs BEFORE FastAPI's body parsing — an
    # unauthenticated request never gets its Pydantic model parsed, so an
    # attacker cannot DoS us by sending many large invalid JSON bodies.
    # Skips /health (uptime ping) and CORS preflight OPTIONS.
    # ------------------------------------------------------------------
    @app.middleware('http')
    async def _auth_middleware(request: Request, call_next):
        if request.method == 'OPTIONS' or request.url.path == '/health':
            return await call_next(request)
        api_key = request.headers.get('x-api-key', '')
        if not api_key or not hmac.compare_digest(api_key, settings.api_key):
            return JSONResponse({'detail': 'invalid API key'}, status_code=401)
        return await call_next(request)

    # ------------------------------------------------------------------
    # Routes.
    # ------------------------------------------------------------------
    @app.get('/health')
    async def health():
        # Unauthenticated endpoint — return only what's needed to confirm
        # the process is alive. Model IDs / current backend are info-
        # disclosure surface for an attacker fingerprinting the deployment;
        # keep them behind the API key on /v1/switch_model (GET if needed).
        return {'status': 'ok'}

    @app.post('/v1/chat/completions')
    async def chat_completions(req: ChatCompletionsRequest):
        # Auth enforced upstream in _auth_middleware.
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
    async def chat_json(req: ChatJsonRequest):
        # Auth enforced upstream in _auth_middleware.
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
    async def vision(req: VisionRequest):
        # Auth enforced upstream in _auth_middleware.
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
    async def switch_model(req: SwitchModelRequest):
        # Auth enforced upstream in _auth_middleware.
        # Read ``_current`` INSIDE the lock — releasing the lock and then
        # reading would race against any concurrent /chat or /vision call
        # whose ``swap_to`` already started flipping the model.
        async with engine._swap_lock:
            await engine.swap_to(req.target)
            current = engine._current
        return {'current_model': current}

    return app
