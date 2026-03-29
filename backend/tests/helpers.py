"""Test helpers (Firestore client mocks)."""

from __future__ import annotations

from unittest.mock import MagicMock


def mock_firestore_client_for_documents(documents: list[dict]) -> MagicMock:
    """Build a MagicMock ``firestore.Client`` that streams docs from ``documents`` (each with ``id``)."""
    mock_coll = MagicMock()
    mock_docs = []
    for row in documents:
        doc = MagicMock()
        doc.id = row["id"]
        payload = {k: v for k, v in row.items() if k != "id"}
        doc.to_dict.return_value = payload
        mock_docs.append(doc)
    mock_coll.stream.return_value = iter(mock_docs)
    mock_client = MagicMock()
    mock_client.collection.return_value = mock_coll
    return mock_client
