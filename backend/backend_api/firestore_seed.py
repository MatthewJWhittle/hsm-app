"""Write Firestore-shaped JSON (``documents[]``) into a Firestore ``models`` collection."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def seed_models_from_catalog_json(
    *,
    catalog_path: Path,
    project: str,
    collection: str = "models",
) -> int:
    """
    Read ``documents[]`` from ``catalog_path`` and ``set`` each document (id from ``id`` field).

    Requires ``FIRESTORE_EMULATOR_HOST`` (or credentials) to be configured before creating the client.
    Returns the number of documents written.
    """
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    docs = raw.get("documents")
    if not isinstance(docs, list):
        raise ValueError("catalog JSON must contain a documents array")

    from google.cloud import firestore

    client = firestore.Client(project=project)
    coll = client.collection(collection)
    count = 0
    for row in docs:
        if not isinstance(row, dict) or "id" not in row:
            logger.warning("SKIP invalid document entry: %r", row)
            continue
        doc_id = row["id"]
        payload = {k: v for k, v in row.items() if k != "id"}
        coll.document(doc_id).set(payload)
        count += 1
    return count
