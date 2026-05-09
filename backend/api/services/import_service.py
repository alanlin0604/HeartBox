"""Import service — CSV / JSON / Day One / Journey parsing + ingestion.

Both PreviewImportView and ImportCSVView share these helpers so the formats
they accept stay in lock-step. The big idea:

  parse_file(file) -> ('csv'|'json', [{<raw key>: <raw value>}, ...])

After parsing, downstream callers apply user-supplied column mapping (or fall
back to DEFAULT_COLUMN_MAP) and call ingest_rows(user, rows) to create the
actual MoodNote records. Tests for these helpers live in
backend/api/tests/test_import_service.py.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone as dt_tz

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from api.models import MoodNote

logger = logging.getLogger(__name__)

# Default column → standard field map, used when the user doesn't provide one.
# Standard fields the importer understands: date / content / mood / stress /
# tags / weather / temperature. Anything else lands in metadata.
DEFAULT_COLUMN_MAP = {
    'created': 'date',
    'created_at': 'date',
    'created_date': 'date',
    'creationdate': 'date',          # Day One
    'creation_date': 'date',
    'date_journal': 'date',          # Journey
    'date': 'date',
    'sentiment': 'mood',
    'mood': 'mood',
    'stress': 'stress',
    'stress_index': 'stress',
    'entry': 'content',
    'text': 'content',
    'body': 'content',
    'note': 'content',
    'content': 'content',
    'tags': 'tags',
    'weather': 'weather',
    'temperature': 'temperature',
}


# ---- Format detection / parsing ----


def detect_format(filename: str) -> str | None:
    """Return 'csv' or 'json' from filename suffix, or None if unsupported."""
    if not filename:
        return None
    lower = filename.lower()
    if lower.endswith('.csv'):
        return 'csv'
    if lower.endswith('.json'):
        return 'json'
    return None


def parse_csv(blob: bytes) -> tuple[list[str], list[dict]]:
    """Parse a CSV blob; return (column headers, list-of-row-dicts).

    Strips UTF-8 BOM, falls back to utf-8 decode errors with replacement so
    one weird character doesn't kill the whole import.
    """
    text = blob.decode('utf-8-sig', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    columns = reader.fieldnames or []
    rows = [dict(r) for r in reader]
    return columns, rows


def parse_json(blob: bytes) -> tuple[list[str], list[dict]]:
    """Parse JSON. Supports three shapes:

    1. Plain array of objects:           ``[{...}, {...}]``
    2. Day One export:                   ``{"entries": [{...}, ...]}``
    3. Journey single-entry:             ``{...}`` (treated as 1-entry array)

    Each entry is normalized to a flat ``{key: str}`` dict so downstream code
    can treat it like a CSV row. Day One's nested ``weather.conditionsDescription``
    is collapsed to ``weather``; tags are joined with commas.
    """
    text = blob.decode('utf-8-sig', errors='replace')
    data = json.loads(text)

    if isinstance(data, dict) and isinstance(data.get('entries'), list):
        raw = data['entries']
    elif isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = [data]
    else:
        raise ValueError(f'JSON root must be object or array, got {type(data).__name__}')

    rows: list[dict] = []
    column_set: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        flat = _flatten_json_entry(entry)
        rows.append(flat)
        column_set.update(flat.keys())

    # Stable column order: keys from the first row first, then any newcomers.
    columns: list[str] = []
    if rows:
        for k in rows[0]:
            if k not in columns:
                columns.append(k)
    for k in column_set:
        if k not in columns:
            columns.append(k)
    return columns, rows


def _flatten_json_entry(entry: dict) -> dict:
    """Collapse Day One / Journey nested fields into flat strings.

    - ``tags`` (list)              -> comma-joined string
    - ``weather`` (dict)           -> ``conditionsDescription`` string
    - ``date_journal`` (epoch ms)  -> ISO 8601 string under same key
    - everything else              -> str(value) for non-strings
    """
    flat: dict[str, str] = {}
    for key, val in entry.items():
        if val is None:
            continue
        if key == 'tags' and isinstance(val, list):
            flat[key] = ','.join(str(t) for t in val if t)
            continue
        if key == 'weather' and isinstance(val, dict):
            desc = val.get('conditionsDescription') or val.get('description')
            if desc:
                flat[key] = str(desc)
            temp = val.get('temperatureCelsius') or val.get('temperature')
            if temp is not None:
                flat['temperature'] = str(temp)
            continue
        if key == 'date_journal' and isinstance(val, (int, float)):
            # Journey ships epoch milliseconds. Convert to ISO so parse_datetime
            # works downstream.
            flat[key] = datetime.fromtimestamp(val / 1000, tz=dt_tz.utc).isoformat()
            continue
        if isinstance(val, (dict, list)):
            flat[key] = json.dumps(val, ensure_ascii=False)
        else:
            flat[key] = str(val)
    return flat


def parse_file(filename: str, blob: bytes) -> tuple[str, list[str], list[dict]]:
    """Dispatch to parse_csv / parse_json by filename suffix.

    Returns (fmt, columns, rows). Raises ValueError on unsupported format /
    parse errors so the view can return a clean 400.
    """
    fmt = detect_format(filename)
    if fmt == 'csv':
        cols, rows = parse_csv(blob)
        return 'csv', cols, rows
    if fmt == 'json':
        cols, rows = parse_json(blob)
        return 'json', cols, rows
    raise ValueError(f'Unsupported file format. Use .csv or .json.')


# ---- Mapping + ingestion ----


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    """Best-guess mapping for each user column → standard field, falling back
    to ``_ignore`` for anything we don't recognize. The frontend pre-fills its
    selectors from this so most users never have to touch them."""
    out = {}
    for col in columns:
        key = (col or '').strip().lower()
        out[col] = DEFAULT_COLUMN_MAP.get(key, '_ignore')
    return out


def normalize_row(row: dict, mapping: dict[str, str] | None) -> dict[str, str]:
    """Apply user (or default) mapping to a raw row.

    The user-supplied mapping comes in the shape ``{<original column>: <target>}``
    where target is one of the standard field names (date / content / etc.) or
    the sentinel ``_ignore``. When mapping is None we fall back to
    DEFAULT_COLUMN_MAP keyed off the lowercased original.
    """
    out: dict[str, str] = {}
    for k, v in row.items():
        if k is None or v is None:
            continue
        original = str(k).strip()
        text = str(v).strip()
        if not text:
            continue
        if mapping:
            target = mapping.get(original) or mapping.get(original.lower())
            if not target or target == '_ignore':
                continue
        else:
            target = DEFAULT_COLUMN_MAP.get(original.lower(), original.lower())
        out[target] = text
    return out


def ingest_rows(
    user,
    rows: list[dict],
    *,
    mapping: dict[str, str] | None = None,
    progress_cb=None,
) -> tuple[int, list[str]]:
    """Create MoodNote records from normalized rows. Returns (created, errors).

    ``progress_cb(processed, total)`` is invoked after each row for callers
    that want to report progress (e.g. the Celery task).
    """
    created = 0
    errors: list[str] = []
    total = len(rows)

    for i, raw in enumerate(rows, start=1):
        if progress_cb:
            try:
                progress_cb(i - 1, total)
            except Exception:  # pragma: no cover — never let a callback kill the import
                pass

        normalized = normalize_row(raw, mapping)
        content = normalized.get('content', '')
        if not content:
            errors.append(f'Row {i}: missing content')
            continue

        note = MoodNote(user=user)
        note.set_content(content)

        metadata: dict = {}
        mood_str = normalized.get('mood', '')
        if mood_str:
            metadata['imported_mood'] = mood_str
        tags = normalized.get('tags', '')
        if tags:
            metadata['tags'] = [t.strip() for t in tags.split(',') if t.strip()]
        weather = normalized.get('weather', '')
        if weather:
            metadata['weather'] = weather
        temperature = normalized.get('temperature', '')
        if temperature:
            metadata['temperature'] = temperature
        note.metadata = metadata

        stress = normalized.get('stress', '')
        if stress:
            try:
                stress_val = int(float(stress))
                if 0 <= stress_val <= 10:
                    note.stress_index = stress_val
            except ValueError:
                pass

        if mood_str:
            try:
                score = float(mood_str)
                if -1.0 <= score <= 1.0:
                    note.sentiment_score = score
            except ValueError:
                pass

        note.save()

        # MoodNote.created_at is auto_now_add — must update post-save to honor
        # the imported date.
        date_str = normalized.get('date', '')
        if date_str:
            try:
                parsed = parse_datetime(date_str) or parse_date(date_str)
                if parsed:
                    if hasattr(parsed, 'hour'):
                        if timezone.is_naive(parsed):
                            parsed = timezone.make_aware(parsed)
                        MoodNote.objects.filter(pk=note.pk).update(created_at=parsed)
                    else:
                        aware_dt = timezone.make_aware(
                            datetime.combine(parsed, datetime.min.time())
                        )
                        MoodNote.objects.filter(pk=note.pk).update(created_at=aware_dt)
            except Exception:
                logger.exception('Import: failed to parse date for row %d', i)

        created += 1

    if progress_cb:
        try:
            progress_cb(total, total)
        except Exception:
            # Final progress report shouldn't sink the whole import.
            logger.warning('Import: final progress_cb failed', exc_info=True)

    return created, errors
