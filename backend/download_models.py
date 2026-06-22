"""Background-friendly model downloader. Runs each model in its own try/except
so one failure (e.g. TAIDE License not yet approved) doesn't stop the others.
Prints progress with flush=True so PowerShell can show live status.
"""
import os
import sys
import time
# Force UTF-8 stdout so Windows cp950 console doesn't choke on log glyphs.
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass
from huggingface_hub import snapshot_download
from huggingface_hub.errors import GatedRepoError, RepositoryNotFoundError, HfHubHTTPError

MODELS = [
    # Embeddings — no license required, smallest, do first
    ('BAAI/bge-m3', 'bge-m3 multilingual embeddings (2.3GB)'),
    # Vision — open license
    ('llava-hf/llava-v1.6-mistral-7b-hf', 'LLaVA 1.6 vision model (~14GB)'),
    # Chat — TAIDE License required (apply if 403)
    ('taide/TAIDE-LX-7B-Chat', 'TAIDE Llama-3 Chinese (~14GB) — needs license'),
    # Fallback if TAIDE not yet approved — Apache 2.0, community fine-tune
    ('yentinglin/Llama-3-Taiwan-8B-Instruct', 'Llama-3-Taiwan fallback (Apache 2.0, ~16GB)'),
]

print(f'Starting downloads of {len(MODELS)} models. Each runs to completion before next starts.', flush=True)
print('Cache dir: ~/.cache/huggingface/hub', flush=True)
print('=' * 70, flush=True)

results = []
for idx, (model_id, desc) in enumerate(MODELS, 1):
    print(f'\n[{idx}/{len(MODELS)}] {desc}', flush=True)
    print(f'  -> {model_id}', flush=True)
    t0 = time.time()
    try:
        path = snapshot_download(
            repo_id=model_id,
            # Skip unnecessary files: original .pth weights when .safetensors exist,
            # any optimizer states, training artifacts
            ignore_patterns=['*.pth', '*.bin.index.json.lock', 'optimizer.pt', 'training_args.bin'],
        )
        elapsed = time.time() - t0
        print(f'  [OK] done in {elapsed:.0f}s -> {path}', flush=True)
        results.append((model_id, 'OK', f'{elapsed:.0f}s'))
    except GatedRepoError as e:
        print(f'  [FAIL] GATED — License not approved yet: {model_id}', flush=True)
        print(f'    -> Apply at https://huggingface.co/{model_id}', flush=True)
        results.append((model_id, 'GATED', 'apply license'))
    except RepositoryNotFoundError as e:
        print(f'  [FAIL] NOT FOUND — repo may have moved: {model_id}', flush=True)
        results.append((model_id, 'NOT_FOUND', str(e)[:100]))
    except HfHubHTTPError as e:
        code = getattr(e.response, 'status_code', '?')
        print(f'  [FAIL] HTTP {code} — {str(e)[:200]}', flush=True)
        results.append((model_id, f'HTTP_{code}', str(e)[:100]))
    except Exception as e:
        print(f'  [FAIL] ERROR — {type(e).__name__}: {str(e)[:200]}', flush=True)
        results.append((model_id, 'ERROR', f'{type(e).__name__}: {str(e)[:80]}'))

print('\n' + '=' * 70, flush=True)
print('SUMMARY', flush=True)
print('=' * 70, flush=True)
for model_id, status, info in results:
    print(f'  {status:12s} {model_id:50s} {info}', flush=True)

ok_count = sum(1 for _, status, _ in results if status == 'OK')
print(f'\n{ok_count}/{len(results)} models downloaded successfully.', flush=True)
sys.exit(0 if ok_count > 0 else 1)
