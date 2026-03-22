#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone

COG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'hsm-predictions', 'cog'))
OUTPUT_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'hsm_index.json'))


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


def build_index():
    files = list_cog_files(COG_DIR)
    items = []
    species_set = set()
    activity_set = set()
    by_species = {}

    for fname in files:
        species, activity = parse_filename(fname)
        if not species or not activity:
            continue

        species_set.add(species)
        activity_set.add(activity)

        cog_path = f"/data/hsm-predictions/cog/{fname}"
        items.append({
            'species': species,
            'activity': activity,
            'cog_path': cog_path,
        })

        by_species.setdefault(species, {})[activity] = cog_path

    index = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'species': sorted(species_set),
        'activities': sorted(activity_set),
        'items': items,
        'by_species': by_species,
    }
    return index


def main():
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    index = build_index()
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"Wrote index with {len(index['items'])} item(s) → {OUTPUT_JSON}")


if __name__ == '__main__':
    main()


