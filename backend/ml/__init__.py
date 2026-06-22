"""HeartBox Machine Learning module.

Two-track AI strategy (post-Phase-0b):
- Self-hosted TAIDE-LX-7B-Chat (via the FastAPI ``llm_server/``) handles
  generative tasks: chat responses, personalized feedback, daily prompts.
  Routed through ``backend/api/services/llm/`` provider seam so the model
  identity is one config flip away.
- Random Forest models in THIS module handle structured prediction
  (future mood, stress spike risk, churn likelihood) from time-series
  features the LLM cannot see across.

Layout:
  ml/datasets/  — exported training CSVs (gitignored)
  ml/models/    — trained joblib snapshots (gitignored)
  ml/scripts/   — training & evaluation scripts (committed)
  ml/features.py — shared feature-extraction helpers
"""
