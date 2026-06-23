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


def _resolve_safe_ips(host: str) -> set[str]:
    """Resolve ``host`` and return the set of public IPs (or raise).

    Defends against SSRF: an attacker-supplied URL pointing to
    ``169.254.169.254`` (AWS metadata), ``127.0.0.1`` (local services),
    RFC1918, or link-local addresses must NOT be fetched. We check every
    address ``getaddrinfo`` returns — DNS could legitimately resolve to
    A + AAAA records, but the moment one is internal we reject the whole
    URL (else an attacker could flip between A/AAAA answers).

    Returns the set of safe IP strings on success. Raises ``ValueError``
    if any address is non-public, or if resolution fails.

    The set is used by ``_fetch_images`` to *verify the actual TCP peer*
    after connect — that closes the DNS-rebinding window where the
    httpx-internal resolution could legally differ from this one.
    """
    if not host:
        raise ValueError('empty host in url')
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError(f'dns resolution failed for {host!r}') from e
    if not infos:
        raise ValueError(f'no addresses for {host!r}')
    safe_ips: set[str] = set()
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f'unparseable address {ip_str!r} for {host!r}')
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError(
                f'rejected non-public host: {host} -> {ip_str}'
            )
        safe_ips.add(ip_str)
    return safe_ips


def _verify_peer_ip(response, safe_ips: set[str], host: str) -> None:
    """After httpx opens the TCP connection, verify the socket peer is in
    the pre-validated ``safe_ips`` set. Closes the DNS-rebinding TOCTOU
    where ``_resolve_safe_ips`` saw a public IP but the actual connect
    landed on 127.0.0.1 because the attacker flipped the zone between
    the two getaddrinfo calls (validation vs httpx-internal).

    Uses httpcore's ``'server_addr'`` extension key — adversarial review
    found the previous ``'peername'`` key is NOT recognized by any
    httpcore backend (anyio / trio / sync) and silently returned None,
    making the entire peer-verify a no-op. Verified against
    ``httpcore/_backends/anyio.py`` which recognizes only
    ``{ssl_object, client_addr, server_addr, socket, is_readable}``.

    Fails CLOSED on missing peer info: in production every real
    connection has a populated ``server_addr``; an absent extension
    means a misconfigured client or test mock, and we would rather
    reject than open the SSRF window. Tests that mock the transport
    must inject a stub with the extension set.
    """
    stream = response.extensions.get('network_stream') if hasattr(response, 'extensions') else None
    if stream is None:
        raise ValueError(
            f'cannot verify peer IP for {host!r}: network_stream extension '
            'missing — refusing to fetch (would open SSRF rebind window)'
        )
    peer = stream.get_extra_info('server_addr')
    if not peer or not isinstance(peer, tuple) or len(peer) < 1:
        raise ValueError(
            f'cannot verify peer IP for {host!r}: server_addr extension '
            f'returned {peer!r} — refusing to fetch'
        )
    peer_ip = peer[0]
    if peer_ip not in safe_ips:
        raise ValueError(
            f'DNS rebind detected for {host!r}: connected to {peer_ip}, '
            f'expected one of {sorted(safe_ips)}'
        )


# ----------------------------------------------------------------------
# Multimodal message normalization helper — module-level so it is unit-
# testable. Mutates ``messages`` so the LAST user message contains one
# ``image_url`` content block per URL when ``urls`` is non-empty.
#
# Why this matters: VisionRequest allows ``content`` to be a plain string
# (per the OpenAI shape), and clients commonly pass ``image_urls`` as a
# separate top-level field. Without an ``image_url`` block somewhere in
# the messages, the chat-template path emits zero ``<image>``
# placeholders — LLaVA-Next's visual encoder then aligns embeddings to
# the wrong positions and the reply either errors or repeats the prompt
# verbatim. We normalize the message shape here so callers do not have
# to know LLaVA's prompt-template quirks.
# ----------------------------------------------------------------------
def _ensure_image_blocks(messages: list[dict], urls: list[str]) -> None:
    if not urls:
        return
    target = None
    for m in reversed(messages):
        if m.get('role') == 'user':
            target = m
            break
    if target is None:
        target = {'role': 'user', 'content': ''}
        messages.append(target)
    content = target.get('content', '')
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get('type') == 'image_url' for b in content):
            return  # caller already wired it correctly
        content = list(content)
    else:
        content = [{'type': 'text', 'text': str(content) if content else ''}]
    for u in urls:
        content.append({'type': 'image_url', 'image_url': {'url': u}})
    target['content'] = content


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

    _MAX_BYTES = 8 * 1024 * 1024  # 8MB per image
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(5.0, connect=3.0),
        follow_redirects=False,   # SSRF: a 302 to 169.254.169.254 would bypass the host check.
        max_redirects=0,
    ) as client:
        async def _one(url: str):
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f'rejected non-http url: {url[:40]}')
            parsed = urlparse(url)
            host = parsed.hostname or ''
            # First-pass DNS: validate every resolved IP is public.
            # getaddrinfo blocks — run in a thread so the event loop stays
            # responsive when DNS is slow.
            safe_ips = await asyncio.to_thread(_resolve_safe_ips, host)
            # Stream-mode GET so we can abort the moment cumulative body
            # bytes cross the 8MB cap — the previous ``await client.get``
            # buffered the entire body before the size check ran, letting
            # a 500MB image/png response allocate hundreds of MB despite
            # the cap.
            async with client.stream('GET', url) as r:
                # Second-pass: verify the TCP peer we actually connected
                # to is one of the pre-validated safe IPs. Closes the
                # DNS-rebinding TOCTOU window between getaddrinfo and the
                # httpx-internal resolution.
                _verify_peer_ip(r, safe_ips, host)
                if r.status_code in (301, 302, 303, 307, 308):
                    raise ValueError(
                        f'rejected redirect {r.status_code} to '
                        f'{r.headers.get("location", "?")[:80]}'
                    )
                r.raise_for_status()
                ct = r.headers.get('content-type', '').lower()
                if not ct.startswith('image/'):
                    raise ValueError(f'rejected non-image content-type: {ct}')
                cl = r.headers.get('content-length')
                if cl is not None:
                    try:
                        if int(cl) > _MAX_BYTES:
                            raise ValueError(
                                f'image > 8MB (declared content-length={cl})'
                            )
                    except (TypeError, ValueError) as e:
                        # Re-raise ValueError, swallow non-int CL.
                        if 'image >' in str(e):
                            raise
                buf = io.BytesIO()
                total = 0
                async for chunk in r.aiter_bytes():
                    total += len(chunk)
                    if total > _MAX_BYTES:
                        raise ValueError(
                            f'image > 8MB (streamed {total} bytes before abort)'
                        )
                    buf.write(chunk)
            raw = buf.getvalue()
            # Open without decoding pixels to inspect declared dimensions.
            head = Image.open(io.BytesIO(raw))
            w, h = head.size
            if w * h > _MAX_IMAGE_PIXELS:
                raise ValueError(f'image too large: {w}x{h} ({w*h:,} pixels)')
            head.verify()
            return Image.open(io.BytesIO(raw)).convert('RGB')

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

    # CORS LAST so it wraps the auth/body-limit middleware. Otherwise a
    # 401 returned by _auth_middleware reaches the browser without
    # Access-Control-Allow-Origin, and the user sees a cryptic CORS error
    # instead of the actual "bad API key" reason. Order matters in
    # Starlette: most-recently-added is outermost on the inbound path.
    if settings.cors_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins_list,
            allow_credentials=False,
            allow_methods=['POST', 'GET'],
            allow_headers=['Content-Type', 'X-API-Key'],
        )

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

        # Normalize messages so every supplied image_url has a matching
        # ``image_url`` content block — _build_chat_prompt translates each
        # block into an ``<image>`` placeholder, and LLaVA-Next's visual
        # encoder will silently misalign embeddings without one.
        normalized_messages = [m.model_dump() for m in req.messages]
        _ensure_image_blocks(normalized_messages, list(req.image_urls))

        try:
            result = await engine.vision(
                normalized_messages,
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
