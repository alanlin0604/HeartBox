"""Reachability preflight for seed commands that generate text with the LLM.

``provider.is_configured()`` only asserts that a URL and an API key are set —
it deliberately does no I/O, so it stays cheap on the request path. That makes
it the wrong check for a batch job: a configured-but-unreachable server passes
it, and then every note in the run fails individually and falls back to canned
feedback. The run "succeeds", the counts look right, and the seeded data is
quietly not what was asked for.

So before writing anything, actually talk to the server. ``GET /health`` is
unauthenticated on llm_server, which keeps this a pure liveness check with no
key handling of its own.
"""
from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings


def check_llm_reachable(timeout_s: float = 10.0) -> str | None:
    """Return None if the LLM is usable, else a human-readable reason.

    The reason string is meant to be printed straight to the operator: it says
    what to do next, not just what went wrong.
    """
    from api.services.llm import get_llm_provider

    provider = get_llm_provider()
    if not provider.is_configured():
        return (
            'LLM provider is not configured. Set LLM_SERVER_URL and '
            'LLM_SERVER_API_KEY in the root .env (LLM_SERVER_API_KEY must match '
            'API_KEY in ~/.heartbox-llm.env).'
        )

    base_url = getattr(settings, 'LLM_SERVER_URL', '')
    if not base_url:
        return 'LLM_SERVER_URL is empty.'

    try:
        import httpx
    except ImportError:  # pragma: no cover - httpx ships with the backend
        return None  # can't check; let the run proceed rather than block it

    health_url = urljoin(base_url.rstrip('/') + '/', 'health')
    try:
        resp = httpx.get(health_url, timeout=timeout_s)
    except Exception as e:  # noqa: BLE001 - any transport failure is fatal here
        return (
            f'Cannot reach the LLM server at {health_url} ({e.__class__.__name__}: {e}). '
            'Start it with llm_server/start-all.ps1 and wait for the model to '
            'finish loading, then re-run.'
        )

    if resp.status_code != 200:
        return (
            f'LLM server at {health_url} answered HTTP {resp.status_code}, '
            'expected 200. Check llm_server logs (scripts/llm-logs.ps1).'
        )

    # /health deliberately returns only {'status': 'ok'} — model IDs are
    # info-disclosure surface, so they sit behind the API key instead. That
    # means this confirms the process is alive but NOT that weights are
    # loaded; with AUTOLOAD_ON_STARTUP the first generation can still stall
    # for minutes on a cold start. Liveness is the useful signal here anyway:
    # it separates "server is down" (the common case, and fatal) from "server
    # is slow" (recoverable, and reported per-note by the caller).
    return None
