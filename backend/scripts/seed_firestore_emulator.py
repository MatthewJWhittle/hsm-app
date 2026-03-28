#!/usr/bin/env python3
"""Seed the Firestore emulator `models` collection from the local JSON snapshot.

Reads the same shape as ``data/catalog/firestore_models.json`` (``documents[]``).
Implementation: ``firestore_seed_catalog.py`` (dev tooling, not part of ``backend_api``).
Requires ``google-cloud-firestore`` (included in backend deps).

Usage (emulators running, default ports):

  # From repo root, emulators published on localhost (e.g. docker compose)
  cd backend && uv run python scripts/seed_firestore_emulator.py \\
    --catalog ../data/catalog/firestore_models.json

  Env:
    FIRESTORE_EMULATOR_HOST=127.0.0.1:8085
    GOOGLE_CLOUD_PROJECT=hsm-dashboard   # must match .firebaserc

Inside the backend container (catalog at /data/...):

  docker compose exec backend sh -c \\
    'export FIRESTORE_EMULATOR_HOST=firebase-emulators:8085 GOOGLE_CLOUD_PROJECT=hsm-dashboard \\
     && uv run python scripts/seed_firestore_emulator.py --catalog /data/catalog/firestore_models.json'
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from firestore_seed_catalog import seed_models_from_catalog_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(
            os.environ.get("CATALOG_PATH", "data/catalog/firestore_models.json")
        ),
        help="Path to Firestore-shaped JSON with a documents[] array.",
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or "hsm-dashboard",
        help="Firebase/GCP project id (default: env or hsm-dashboard).",
    )
    parser.add_argument(
        "--collection",
        default=os.environ.get("FIRESTORE_MODELS_COLLECTION", "models"),
        help="Firestore collection id (default: models).",
    )
    args = parser.parse_args()

    if not os.environ.get("FIRESTORE_EMULATOR_HOST"):
        print(
            "ERROR: FIRESTORE_EMULATOR_HOST is not set.\n"
            "Example: export FIRESTORE_EMULATOR_HOST=127.0.0.1:8085\n"
            "In Docker backend: FIRESTORE_EMULATOR_HOST=firebase-emulators:8085",
            file=sys.stderr,
        )
        return 1

    try:
        count = seed_models_from_catalog_json(
            catalog_path=args.catalog,
            project=args.project,
            collection=args.collection,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Seeded {count} document(s) into {args.collection!r} (project={args.project}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
