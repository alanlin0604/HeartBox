"""Model loading + generation engine.

Owns the GPU. Single instance per process. Lazy-swap between TAIDE (chat) and
LLaVA (vision):

* On startup, ``load_taide()`` loads the chat model in 4-bit NF4.
* On a /vision call, ``swap_to('llava')`` unloads TAIDE and loads LLaVA.
* On a /chat call, ``swap_to('taide')`` swaps back (or no-op if already loaded).

Concurrent /chat + /vision are serialized through ``_swap_lock`` so two callers
never race a model swap. Each swap costs ~5-15s of wall clock and ~30s of disk
I/O when warm cache is cold.

Per-request timeout is implemented via ``asyncio.wait_for`` around a thread
wrapper of HF ``generate()`` — Transformers doesn't expose a clean cancel hook
without a custom ``StoppingCriteria``, so on timeout we return 504 and let
the orphaned thread finish in background. Documented in the README.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from typing import Literal

logger = logging.getLogger(__name__)

ModelName = Literal['taide', 'llava']


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
    # Loaders
    # ------------------------------------------------------------------
    def _release_model(self) -> None:
        with self._thread_lock:
            self._model = None
            self._tokenizer = None
            self._processor = None
            self._current = None
        try:
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def load_taide(self) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer

        t0 = time.monotonic()
        logger.info('Loading TAIDE chat model %s ...', self.taide_model_id)
        tokenizer = AutoTokenizer.from_pretrained(self.taide_model_id)
        kwargs = {'device_map': 'auto'}
        bnb = self._bnb_config()
        if bnb is not None:
            kwargs['quantization_config'] = bnb
        model = AutoModelForCausalLM.from_pretrained(self.taide_model_id, **kwargs)
        with self._thread_lock:
            self._model = model
            self._tokenizer = tokenizer
            self._processor = None
            self._current = 'taide'
        logger.info('TAIDE loaded in %.1fs', time.monotonic() - t0)

    def load_llava(self) -> None:
        from transformers import AutoProcessor, LlavaNextForConditionalGeneration

        t0 = time.monotonic()
        logger.info('Loading LLaVA vision model %s ...', self.llava_model_id)
        processor = AutoProcessor.from_pretrained(self.llava_model_id)
        kwargs = {'device_map': 'auto'}
        bnb = self._bnb_config()
        if bnb is not None:
            kwargs['quantization_config'] = bnb
        model = LlavaNextForConditionalGeneration.from_pretrained(self.llava_model_id, **kwargs)
        with self._thread_lock:
            self._model = model
            self._tokenizer = processor.tokenizer
            self._processor = processor
            self._current = 'llava'
        logger.info('LLaVA loaded in %.1fs', time.monotonic() - t0)

    async def swap_to(self, target: ModelName) -> None:
        """Async swap. Caller must already hold ``_swap_lock``."""
        if self._current == target:
            return
        # Run loaders in a thread to avoid blocking the event loop.
        self._release_model()
        loader = self.load_taide if target == 'taide' else self.load_llava
        await asyncio.to_thread(loader)

    # ------------------------------------------------------------------
    # Generation (chat)
    # ------------------------------------------------------------------
    def _build_chat_prompt(self, messages: list[dict]) -> str:
        """Use the model's chat template if present; otherwise plain concat."""
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
                content = ' '.join(b.get('text', '') for b in content if b.get('type') == 'text')
            parts.append(f"{m.get('role', 'user')}: {content}")
        parts.append('assistant:')
        return '\n'.join(parts)

    def _generate_chat_sync(
        self,
        messages: list[dict],
        *,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, int, int]:
        import torch

        with self._thread_lock:
            model = self._model
            tokenizer = self._tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError('no model loaded')

        prompt = self._build_chat_prompt(messages)
        inputs = tokenizer(prompt, return_tensors='pt', truncation=False).to(model.device)
        tokens_in = inputs.input_ids.shape[1]

        gen_kwargs = {
            'max_new_tokens': max_tokens,
            'do_sample': temperature > 0,
            'temperature': max(temperature, 1e-5),
            'top_p': 0.9,
            'repetition_penalty': 1.05,
            'pad_token_id': tokenizer.pad_token_id or tokenizer.eos_token_id,
        }
        with torch.inference_mode():
            output_ids = model.generate(**inputs, **gen_kwargs)

        full = tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # Strip the prompt prefix.
        if full.startswith(prompt):
            reply = full[len(prompt):].strip()
        else:
            # Fallback: take everything after the last 'assistant:' marker
            reply = full.split('assistant:')[-1].strip()
        tokens_out = output_ids.shape[1] - tokens_in
        return reply, int(tokens_in), int(tokens_out)

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
            try:
                reply, tokens_in, tokens_out = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generate_chat_sync, messages,
                        temperature=temperature, max_tokens=max_tokens,
                    ),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError as e:
                raise TimeoutError(f'chat generation exceeded {timeout_s}s') from e
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
        inputs = processor(text=prompt, images=images, return_tensors='pt').to(model.device)
        tokens_in = inputs.input_ids.shape[1] if hasattr(inputs, 'input_ids') else 0

        with torch.inference_mode():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=temperature > 0,
                temperature=max(temperature, 1e-5),
                top_p=0.9,
            )
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
            try:
                reply, tokens_in, tokens_out = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._generate_vision_sync,
                        messages=messages, images=images,
                        temperature=temperature, max_tokens=max_tokens,
                    ),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError as e:
                raise TimeoutError(f'vision generation exceeded {timeout_s}s') from e
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
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, json.JSONDecodeError):
            return None
    return None
