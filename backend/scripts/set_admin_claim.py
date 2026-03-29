#!/usr/bin/env python3
"""Set or clear the Firebase custom claim ``admin`` for a user (bootstrap / dev).

Requires Firebase Admin SDK. For the **Auth emulator**, set
``FIREBASE_AUTH_EMULATOR_HOST`` (e.g. ``127.0.0.1:9099``) before running so
``set_custom_user_claims`` targets the emulator.

After changing claims, the user must obtain a **fresh ID token** (sign out/in or
``getIdToken(true)`` in the web app).

Usage::

    cd backend && uv run python scripts/set_admin_claim.py <uid>
    cd backend && uv run python scripts/set_admin_claim.py <uid> --revoke

Environment:

- ``GOOGLE_CLOUD_PROJECT`` / ``GCLOUD_PROJECT`` — Firebase project id (default in
  settings: ``hsm-dashboard``).
- ``FIREBASE_AUTH_EMULATOR_HOST`` — optional; use when working against the Auth emulator.
- ``GOOGLE_APPLICATION_CREDENTIALS`` — service account JSON for **production** (not
  required for emulator-only local runs if the Admin SDK can start).
"""

from __future__ import annotations

import argparse
import os
import sys

# Allow running as ``uv run python scripts/set_admin_claim.py`` from ``backend/``.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import firebase_admin  # noqa: E402
from firebase_admin import auth  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Set admin custom claim for a Firebase user uid.")
    parser.add_argument("uid", help="Firebase Auth user uid (see Emulator UI or Firebase Console)")
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Remove all custom claims for this user",
    )
    args = parser.parse_args()

    from backend_api.settings import Settings

    settings = Settings()
    project_id = settings.google_cloud_project

    if settings.firebase_auth_emulator_host:
        os.environ.setdefault(
            "FIREBASE_AUTH_EMULATOR_HOST",
            settings.firebase_auth_emulator_host,
        )

    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": project_id})

    if args.revoke:
        auth.set_custom_user_claims(args.uid, {})
        print(f"Cleared custom claims for uid={args.uid!r} (project={project_id})")
    else:
        auth.set_custom_user_claims(args.uid, {"admin": True})
        print(
            f"Set admin=true for uid={args.uid!r} (project={project_id}). "
            "User must refresh ID token before calling admin APIs."
        )


if __name__ == "__main__":
    main()
