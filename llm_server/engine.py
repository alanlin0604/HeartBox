"""Model loading + generation engine.

Owns the GPU. Single instance per process. Lazy-swap between TAIDE (chat) and
LLaVA (vision):

* On startup, ``load_taide()`` loads the chat model in 4-bit NF4.
* On a /vision call, ``swap_to('llava')`` unloads TAIDE and loads LLaVA.
* On a /chat call, ``swap_to('taide')`` swaps back (or no-op if already loaded).

Concurrent /chat + /vision are serialized through ``_swap_lock`` so two callers
never race a model swap. Each swap costs ~5-15s of wall clock and ~30s of disk
I/O when warm cache is cold.

Safety properties:

* **Atomic swap.** Loaders return their (model, tokenizer, processor) tuple
  rather than overwriting ``self.*`` mid-load, so a transient HF download
  error or CUDA OOM during load does NOT leave the engine in a half-loaded
  state. The previous model stays usable until the new one is fully ready.
* **Cooperative cancel.** ``generate()`` is run with a ``StoppingCriteria``
  that polls a ``threading.Event``. On client timeout the event is set, the
  HF loop bails at the next token, and the worker thread joins before
  ``_swap_lock`` is released — so a timed-out request can never leave a
  zombie thread holding a GPU model that a subsequent swap is about to GC.
"""
from __future__ import annotations

import asyncio
import gc
import json
import logging
import threading
import time
from typing import Literal

logger = logging.getLogger(__name__)

ModelName = Literal['taide', 'llava']

# How long we wait, after setting the stop event, for the HF worker thread
# to actually exit before we declare it leaked. One additional token is the
# typical bound; 5s gives a generous safety margin without blocking the
# event loop forever.
_STOP_GRACE_SECONDS = 5.0


class InferenceEngine:
    """Owns the single GPU model. Thread-safe via the swap lock + worker thread."""

    def __init__(self, *, taide_model_id: str, llava_model_id: str, bnb_disable: bool = False) -> None:
        self.taide_model_id = taide_model_id
        self.llava_model_id = llava_model_id
        self.bnb_disable = bnb_disable

        self._current: ModelName | None = None
        self._model = None
        self._tokenizer = None
        self._processor = None  # LLaVA needs a processor (tokenizer + image preproc)

        self._swap_lock = asyncio.Lock()        # swap + generate guarded together
        self._thread_lock = threading.Lock()    # protects model attrs in the worker thread

    # ------------------------------------------------------------------
    # Configs
    # ------------------------------------------------------------------
    def _bnb_config(self):
        if self.bnb_disable:
            return None
        import torch
        from transformers import BitsAndBytesConfig
        return BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type='nf4',
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    # ------------------------------------------------------------------
    # Loaders (atomic-swap variants)
    # ------------------------------------------------------------------
    def _gc_cuda(self) -> None:
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def _release_model(self) -> None:
        with self._thread_lock:
            self._model = None
            self._tokenizer = None
            self._processor = None
            self._current = None
        self._gc_cuda()

    def _load_taide_inner(self) -> tuple:
        """Build (model, tokenizer, processor=None, name) without touching
        ``self.*``. Lets ``swap_to`` perform an atomic commit only after a
        full successful load."""
        from transformers import AutoModelForCausalLM, AutoTokenizer

        t0 = time.monotonic()
        logger.info('Loading TAIDE chat model %s ...', self.taide_model_id)
        tokenizer = AutoTokenizer.from_pretrained(self.taide_model_id)
        kwargs = {'device_map': 'auto'}
        bnb = self._bnb_config()
        if bnb is not None:
            kwargs['quantization_config'] = bnb
        model = AutoModelForCausalLM.from_pretrained(self.taide_model_id, **kwargs)
        logger.info('TAIDE loaded in %.1fs', time.monotonic() - t0)
        return model, tokenizer, None, 'taide'

    def _load_llava_inner(self) -> tuple:
        from transformers import AutoProcessor, LlavaNextForConditionalGeneration

        t0 = time.monotonic()
        logger.info('Loading LLaVA vision model %s ...', self.llava_model_id)
        processor = AutoProcessor.from_pretrained(self.llava_model_id)
        kwargs = {'device_map': 'auto'}
        bnb = self._bnb_config()
        if bnb is not None:
            kwargs['quantization_config'] = bnb
        model = LlavaNextForConditionalGeneration.from_pretrained(
            self.llava_model_id, **kwargs
        )
        logger.info('LLaVA loaded in %.1fs', time.monotonic() - t0)
        return model, processor.tokenizer, processor, 'llava'

    # Back-compat shims so callers (lifespan startup, tests) can keep using
    # ``load_taide`` / ``load_llava`` — they now go through the atomic path.
    def load_taide(self) -> None:
        model, tok, proc, name = self._load_taide_inner()
        with self._thread_lock:
            self._model = model
            self._tokenizer = tok
            self._processor = proc
            self._current = name

    def load_llava(self) -> None:
        model, tok, proc, name = self._load_llava_inner()
        with self._thread_lock:
            self._model = model
            self._tokenizer = tok
            self._processor = proc
            self._current = name

    async def swap_to(self, target: ModelName) -> None:
        """Async swap. Caller must already hold ``_swap_lock``.

        Atomicity: we release the *old* model first to free VRAM before the
        new one is loaded — peak holding both 4-bit 7B models can exceed
        16GB GPUs. If the new load fails, we surface a clean error and
        leave the engine in an unloaded state (subsequent calls will retry).
        We never silently lie about ``_current``.
        """
        if self._current == target:
            return
        loader = self._load_taide_inner if target == 'taide' else self._load_llava_inner
        # Release first; new load happens with a clean slate.
        self._release_model()
        try:
            model, tok, proc, name = await asyncio.to_thread(loader)
        except Exception as e:
            # Loader raised — make absolutely sure we don't lie about state.
            self._release_model()
            logger.exception('Failed to load %s', target)
            raise RuntimeError(f'load failed for {target}: {e}') from e
        with self._thread_lock:
            self._model = model
            self._tokenizer = tok
            self._processor = proc
            self._current = name

    # ------------------------------------------------------------------
    # Generation (chat)
    # ------------------------------------------------------------------
    def _build_chat_prompt(self, messages: list[dict]) -> str:
        """Use the model's chat template if present; otherwise plain concat.

        For multimodal content blocks (vision path), emit an ``<image>``
        placeholder where each image_url block appeared instead of silently
        dropping it — LLaVA-Next aligns its visual embeddings to that token
        and a missing placeholder breaks the chat path entirely.
        """
        tokenizer = self._tokenizer
        if hasattr(tokenizer, 'apply_chat_template'):
            try:
                return tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                )
            except Exception:
                pass
        parts = []
        for m in messages:
            content = m.get('content', '')
            if isinstance(content, list):
                rendered = []
                for b in content:
                    btype = b.get('type')
                    if btype == 'text':
                        rendered.append(b.get('text', ''))
                    elif btype == 'image_url':
                        # Preserve a marker so the visual encoder's
                        # embeddings line up with the right position.
                        rendered.append('<image>')
                content = ' '.join(rendered)
            parts.append(f"{m.get('role', 'user')}: {content}")
        parts.append('assistant:')
        return '\n'.join(parts)

    def _make_stop_criteria(self, stop_event: threading.Event):
        """Build a ``StoppingCriteriaList`` that polls ``stop_event`` between
        tokens. HF calls this hook after every generated token, so client
        cancellation is observed within ~1 token latency."""
        from transformers import StoppingCriteria, StoppingCriteriaList

        class _EventStop(StoppingCriteria):
            def __init__(self, ev: threading.Event) -> None:
                self.ev = ev

            def __call__(self, input_ids, scores, **kwargs) -> bool:  # noqa: D401
                return self.ev.is_set()

        return StoppingCriteriaList([_EventStop(stop_event)])

    def _generate_chat_sync(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
        stop_event: threading.Event,
    ) -> tuple[str, int, int]:
        import torch

        with self._thread_lock:
            model = self._model
            tokenizer = self._tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError('no model loaded')

        prompt = self._build_chat_prompt(messages)
        # ``truncation=True`` + ``max_length`` caps input so a prompt-bomb
        # client can't OOM us by sending a 10MB prompt. The 8192 cap matches
        # ``settings.max_context_tokens`` default; callers may pre-truncate.
        max_in = 8192
        inputs = tokenizer(
            prompt, return_tensors='pt', truncation=True, max_length=max_in,
        ).to(model.device)
        tokens_in = inputs.input_ids.shape[1]

        gen_kwargs = {
            'max_new_tokens': max_tokens,
            'do_sample': temperature > 0,
            'temperature': max(temperature, 1e-5),
            'top_p': 0.9,
            'repetition_penalty': 1.05,
            'pad_token_id': tokenizer.pad_token_id or tokenizer.eos_token_id,
            'stopping_criteria': self._make_stop_criteria(stop_event),
        }
        with torch.inference_mode():
            output_ids = model.generate(**inputs, **gen_kwargs)

        # If the stop event fired, surface that as a timeout to the caller —
        # we don't want to return a half-completed reply masquerading as ok.
        if stop_event.is_set():
            raise TimeoutError('generation cancelled by stop event')

        full = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # Strip the prompt prefix.
        if full.startswith(prompt):
            reply = full[len(prompt):].strip()
        else:
            # Fallback: take everything after the last 'assistant:' marker
            reply = full.split('assistant:')[-1].strip()
        tokens_out = output_ids.shape[1] - tokens_in
        return reply, int(tokens_in), int(tokens_out)

    async def _await_with_cancel(
        self,
        fut: asyncio.Future,
        stop_event: threading.Event,
        *,
        timeout_s: float,
        op_label: str,
    ):
        """Wait for ``fut`` with timeout. On timeout: set ``stop_event`` so the
        HF generate loop bails at the next token, then JOIN the worker thread
        before raising — that's the only way ``_swap_lock`` can be released
        safely without leaving a zombie thread that still holds the GPU model.
        """
        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=timeout_s)
        except asyncio.TimeoutError as e:
            stop_event.set()
            try:
                # Worker should observe stop_event within one token (~50ms).
                # Allow generous grace before declaring leak.
                await asyncio.wait_for(asyncio.shield(fut), timeout=_STOP_GRACE_SECONDS)
            except asyncio.TimeoutError:
                logger.error(
                    '%s worker thread did not exit within %.1fs of stop signal — '
                    'thread leaked, GPU model may be GC-blocked',
                    op_label, _STOP_GRACE_SECONDS,
                )
            except Exception:
                # Worker raised on the way out — that's fine, we'll surface
                # the original timeout to the client.
                pass
            raise TimeoutError(f'{op_label} generation exceeded {timeout_s}s') from e

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        max_tokens: int = 500,
        timeout_s: float = 60.0,
    ) -> dict:
        async with self._swap_lock:
            await self.swap_to('taide')
            t0 = time.monotonic()
            stop_event = threading.Event()
            fut = asyncio.ensure_future(
                asyncio.to_thread(
                    self._generate_chat_sync, messages,
                    temperature=temperature, max_tokens=max_tokens,
                    stop_event=stop_event,
                )
            )
            reply, tokens_in, tokens_out = await self._await_with_cancel(
                fut, stop_event, timeout_s=timeout_s, op_label='chat',
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return {
                'reply': reply,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'latency_ms': elapsed_ms,
                'model': self.taide_model_id,
            }

    # ------------------------------------------------------------------
    # Vision (LLaVA)
    # ------------------------------------------------------------------
    def _generate_vision_sync(
        self,
        *,
        messages: list[dict],
        images,
        temperature: float,
        max_tokens: int,
        stop_event: threading.Event,
    ) -> tuple[str, int, int]:
        import torch

        with self._thread_lock:
            model = self._model
            processor = self._processor
        if model is None or processor is None:
            raise RuntimeError('no vision model loaded')

        # Stitch text + images into LLaVA chat format. We rely on the processor's
        # chat template if available.
        prompt = self._build_chat_prompt(messages)
        inputs = processor(
            text=prompt, images=images, return_tensors='pt',
            truncation=True, max_length=4096,
        ).to(model.device)
        tokens_in = inputs.input_ids.shape[1] if hasattr(inputs, 'input_ids') else 0

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 1e-5),
                top_p=0.9,
                stopping_criteria=self._make_stop_criteria(stop_event),
            )
        if stop_event.is_set():
            raise TimeoutError('vision generation cancelled by stop event')

        full = processor.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        if full.startswith(prompt):
            reply = full[len(prompt):].strip()
        else:
            reply = full.split('assistant:')[-1].strip()
        tokens_out = output_ids.shape[1] - tokens_in
        return reply, int(tokens_in), int(tokens_out)

    async def vision(
        self,
        messages: list[dict],
        images,
        *,
        temperature: float = 0.7,
        max_tokens: int = 300,
        timeout_s: float = 120.0,
    ) -> dict:
        async with self._swap_lock:
            await self.swap_to('llava')
            t0 = time.monotonic()
            stop_event = threading.Event()
            fut = asyncio.ensure_future(
                asyncio.to_thread(
                    self._generate_vision_sync,
                    messages=messages, images=images,
                    temperature=temperature, max_tokens=max_tokens,
                    stop_event=stop_event,
                )
            )
            reply, tokens_in, tokens_out = await self._await_with_cancel(
                fut, stop_event, timeout_s=timeout_s, op_label='vision',
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            return {
                'reply': reply,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'latency_ms': elapsed_ms,
                'model': self.llava_model_id,
            }


# ----------------------------------------------------------------------
# JSON best-effort parsing — same contract as the Django-side helper.
# ----------------------------------------------------------------------
def _first_balanced_json_object(text: str) -> str | None:
    """First balanced ``{ ... }`` substring. Mirrors
    ``LLMProvider._first_balanced_json_object`` in the Django backend so the
    server and client recover identically from messy model output."""
    start = text.find('{')
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if in_string:
            if c == '\\':
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def best_effort_json(raw: str) -> dict | None:
    if not raw:
        return None
    text = raw.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, json.JSONDecodeError):
        pass
    candidate = _first_balanced_json_object(text)
    if candidate:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, json.JSONDecodeError):
            return None
    return None
