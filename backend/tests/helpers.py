"""Test helpers (Firestore client mocks)."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend_api.catalog_service import MODELS_COLLECTION_ID, PROJECTS_COLLECTION_ID


def mock_firestore_client_for_documents(
    documents: list[dict],
    *,
    project_documents: list[dict] | None = None,
) -> MagicMock:
    """
    Build a MagicMock ``firestore.Client`` that streams ``documents`` from ``models``
    and ``project_documents`` from ``projects`` (defaults to empty projects).
    """
    project_documents = project_documents if project_documents is not None else []

    def _make_stream(rows: list[dict]) -> MagicMock:
        mock_docs = []
        for row in rows:
            doc = MagicMock()
            doc.id = row["id"]
            payload = {k: v for k, v in row.items() if k != "id"}
            doc.to_dict.return_value = payload
            mock_docs.append(doc)
        mock_coll = MagicMock()
        mock_coll.stream.return_value = iter(mock_docs)
        return mock_coll

    def collection(name: str) -> MagicMock:
        if name == PROJECTS_COLLECTION_ID:
            return _make_stream(project_documents)
        if name == MODELS_COLLECTION_ID:
            return _make_stream(documents)
        return _make_stream([])

    mock_client = MagicMock()
    mock_client.collection.side_effect = collection
    return mock_client
