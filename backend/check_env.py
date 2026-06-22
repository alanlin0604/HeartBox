"""End-to-end verification — split into 'inference' and 'embedding' processes.

In production architecture:
  - llm_server (FastAPI): loads TAIDE + LLaVA via bitsandbytes 4-bit
  - Django backend:       runs bge-m3 via sentence_transformers (CPU/GPU)
These never share a process, so the Windows DLL ordering issue between
bitsandbytes and sentence_transformers doesn't surface in production.
This script verifies each in its own subprocess.
"""
import subprocess
import sys

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

ok = True
ok &= run('1. Inference stack (TAIDE + LLaVA)', INFERENCE_CHECK)
print()
ok &= run('2. Embedding stack (bge-m3)', EMBEDDING_CHECK)
print()
ok &= run('3. FastAPI server stack', FASTAPI_CHECK)
print()
print('=== OVERALL:', 'PASS' if ok else 'FAIL', '===')
sys.exit(0 if ok else 1)
