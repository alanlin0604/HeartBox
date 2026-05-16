"""HeartBox Machine Learning module.

Two-track AI strategy:
- OpenAI handles generative tasks (chat responses, personalized feedback,
  daily prompts) where natural-language generation is needed.
- Random Forest models in this module handle structured prediction
  (future mood, stress spike risk, churn likelihood) from time-series
  features the LLM can't see across.

Layout:
  ml/datasets/  — exported training CSVs (gitignored)
  ml/models/    — trained joblib snapshots (gitignored)
  ml/scripts/   — training & evaluation scripts (committed)
  ml/features.py — shared feature-extraction helpers
"""
