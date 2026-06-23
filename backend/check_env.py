"""End-to-end verification — split into 'inference' and 'embedding' processes.

In production architecture:
  - llm_server (FastAPI): loads TAIDE + LLaVA via bitsandbytes 4-bit
  - Django backend:       runs bge-m3 via sentence_transformers (CPU/GPU)
These never share a process, so the Windows DLL ordering issue between
bitsandbytes and sentence_transformers doesn't surface in production.
This script verifies each in its own subprocess, plus reports on the
configuration env vars the backend will read at startup.
"""
import os
import subprocess
import sys
from pathlib import Path

INFERENCE_CHECK = """
import torch
print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(), '|', torch.cuda.get_device_name(0))
total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
print(f'VRAM total {total_gb:.1f} GB')

import transformers
from transformers import BitsAndBytesConfig
print('transformers', transformers.__version__)

import bitsandbytes as bnb
print('bitsandbytes', bnb.__version__)

# Smoke: instantiate a 4-bit config (no model load)
cfg = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16)
print('4-bit config OK')
print('=== inference stack: PASS ===')
"""

EMBEDDING_CHECK = """
from sentence_transformers import SentenceTransformer
import sentence_transformers
print('sentence_transformers', sentence_transformers.__version__)
print('=== embedding stack: PASS ===')
"""

FASTAPI_CHECK = """
import fastapi, uvicorn, huggingface_hub
print('fastapi', fastapi.__version__)
print('uvicorn', uvicorn.__version__)
print('huggingface_hub', huggingface_hub.__version__)
print('=== api stack: PASS ===')
"""

def run(label, code):
    print(f'--- {label} ---', flush=True)
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    print(r.stdout, end='')
    if r.returncode != 0:
        print('STDERR:', r.stderr)
        return False
    return True

def check_env_vars():
    """Report which Phase 0b configuration vars are set.

    Does NOT validate that values are correct — just that they exist and
    are non-empty. The actual `is_configured()` check happens at
    provider construction time inside the Django app.
    """
    print('--- 4. Configuration env vars ---', flush=True)

    llm_env_file = Path(os.environ.get('USERPROFILE', str(Path.home()))) / '.heartbox-llm.env'
    if llm_env_file.exists():
        with open(llm_env_file, encoding='utf-8') as f:
            content = f.read()
        api_key_set = 'API_KEY=' in content and len(content.split('API_KEY=', 1)[1].split('\n', 1)[0].strip()) >= 32
        print(f'  llm_server  ~/.heartbox-llm.env exists, API_KEY set: {api_key_set}')
    else:
        print(f'  llm_server  ~/.heartbox-llm.env MISSING ({llm_env_file})')

    # Backend-side env vars (read from process env or backend/.env)
    backend_vars = [
        ('LLM_PROVIDER', 'Required: remote_taide or mock'),
        ('LLM_SERVER_URL', 'Required for remote_taide'),
        ('LLM_SERVER_API_KEY', 'Required for remote_taide'),
        ('LLM_MODEL', 'Optional, default taide-lx-7b-chat'),
        ('CHROMA_COLLECTION_NAME', 'Optional, default psychology_kb_bgem3'),
        ('SENTRY_DSN', 'Optional, enables error tracking'),
        ('CRON_SECRET', 'Required for /api/cron/* endpoints'),
    ]
    backend_env = Path(__file__).parent / '.env'
    backend_env_content = backend_env.read_text(encoding='utf-8') if backend_env.exists() else ''
    print(f'  backend     .env exists: {backend_env.exists()}')
    for key, note in backend_vars:
        in_env = key in os.environ and bool(os.environ[key])
        in_file = (key + '=') in backend_env_content
        status = 'set' if in_env else ('in .env' if in_file else 'NOT SET')
        print(f'    {key:30} {status:10}  ({note})')

    print('=== env config: REPORTED ===')
    return True


ok = True
ok &= run('1. Inference stack (TAIDE + LLaVA)', INFERENCE_CHECK)
print()
ok &= run('2. Embedding stack (bge-m3)', EMBEDDING_CHECK)
print()
ok &= run('3. FastAPI server stack', FASTAPI_CHECK)
print()
ok &= check_env_vars()
print()
print('=== OVERALL:', 'PASS' if ok else 'FAIL', '===')
sys.exit(0 if ok else 1)
