"""Initialize Firebase Admin SDK (Auth token verification)."""

from __future__ import annotations

import logging
import os

import firebase_admin
from firebase_admin import App

from backend_api.settings import Settings

logger = logging.getLogger(__name__)


def init_firebase_admin(settings: Settings) -> App | None:
    """Initialize the default app once. Uses Auth emulator when host is set."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    project_id = settings.google_cloud_project
    if settings.firebase_auth_emulator_host:
        os.environ.setdefault(
            "FIREBASE_AUTH_EMULATOR_HOST",
            settings.firebase_auth_emulator_host,
        )

    try:
        app = firebase_admin.initialize_app(options={"projectId": project_id})
    except ValueError as e:
        # Already initialized (e.g. tests double-import).
        logger.debug("firebase_admin.initialize_app skipped: %s", e)
        return firebase_admin.get_app()

    logger.info("Firebase Admin initialized for project %r", project_id)
    return app
