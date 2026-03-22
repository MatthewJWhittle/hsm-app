#!/usr/bin/env python3
"""
Scan `data/hsm-predictions/cog/` and write a Firestore-shaped local catalog:
`data/catalog/firestore_models.json` (collection `models`, one document per Model).

See docs/data-models.md (Catalog storage). Legacy `hsm_index.json` is no longer written.
"""
import json
import os
import re
from datetime import datetime, timezone

COG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'hsm-predictions', 'cog'))
OUTPUT_JSON = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'catalog', 'firestore_models.json')
)

_SLUG_RE = re.compile(r'[^a-z0-9]+')


def slug_segment(name: str) -> str:
    s = name.lower().strip()
    s = _SLUG_RE.sub('-', s)
    return s.strip('-')


def stable_model_id(species: str, activity: str) -> str:
    """Match backend_api.catalog.stable_model_id (document id base)."""
    return f'{slug_segment(species)}--{slug_segment(activity)}'


def list_cog_files(directory: str):
    if not os.path.isdir(directory):
        return []
    return [
        f for f in sorted(os.listdir(directory))
        if f.lower().endswith('_cog.tif')
    ]


def parse_filename(filename: str):
    # Example: "Myotis daubentonii_In flight_cog.tif"
    name = filename[:-8] if filename.lower().endswith('_cog.tif') else os.path.splitext(filename)[0]
    if '_' not in name:
        return None, None
    species, activity = name.rsplit('_', 1)
    return species, activity


def species_display_from_slug(slug: str) -> str:
    """Turn myotis_daubentonii → Myotis daubentonii (binomial-style)."""
    parts = slug.split('_')
    if not parts:
        return slug
    if len(parts) == 1:
        return parts[0].capitalize()
    return parts[0].capitalize() + ' ' + ' '.join(parts[1:])


def parse_lowercase_snake_filename(filename: str):
    """
    Example: myotis_daubentonii_in_flight_cog.tif → (Myotis daubentonii, In flight).
    Activity must be exactly _in_flight or _roost before _cog.tif.
    """
    lower = filename.lower()
    if not lower.endswith('_cog.tif'):
        return None, None
    base = filename[: -len('_cog.tif')]
    if base.endswith('_in_flight'):
        slug = base[: -len('_in_flight')].rstrip('_')
        if not slug:
            return None, None
        return species_display_from_slug(slug), 'In flight'
    if base.endswith('_roost'):
        slug = base[: -len('_roost')].rstrip('_')
        if not slug:
            return None, None
        return species_display_from_slug(slug), 'Roost'
    return None, None


def build_items():
    items = []
    for fname in list_cog_files(COG_DIR):
        species, activity = parse_lowercase_snake_filename(fname)
        if not species or not activity:
            species, activity = parse_filename(fname)
        if not species or not activity:
            continue
        cog_path = f'/data/hsm-predictions/cog/{fname}'
        items.append({
            'species': species,
            'activity': activity,
            'cog_path': cog_path,
        })
    return items


def items_to_firestore_documents(items: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    documents = []
    for it in items:
        species = it['species']
        activity = it['activity']
        cog_path = it['cog_path']
        base = stable_model_id(species, activity)
        n = seen.get(base, 0)
        doc_id = f'{base}--{n + 1}' if n else base
        seen[base] = n + 1
        root = os.path.dirname(cog_path) or '/data'
        basename = os.path.basename(cog_path)
        documents.append({
            'id': doc_id,
            'species': species,
            'activity': activity,
            'artifact_root': root,
            'suitability_cog_path': basename,
        })
    return documents


def build_firestore_snapshot():
    items = build_items()
    return {
        'collection_id': 'models',
        'description': (
            'Local snapshot of the Firestore `models` collection (see docs/data-models.md). '
            'Each entry is one document; `id` is the Firestore document id.'
        ),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'documents': items_to_firestore_documents(items),
    }


def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    snapshot = build_firestore_snapshot()
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    n = len(snapshot['documents'])
    print(f'Wrote Firestore catalog with {n} document(s) → {OUTPUT_JSON}')


if __name__ == '__main__':
    main()
