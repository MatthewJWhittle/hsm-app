#!/usr/bin/env python3
"""Apply PATCH …/environmental-band-definitions/labels from a JSON file (machine name -> label fields).

  export HSM_API_BASE=http://127.0.0.1:8000
  export HSM_PROJECT_ID=<uuid>
  export HSM_ID_TOKEN=<Firebase ID token with admin>
  # Obtain a token: POST /auth/token with email/password and "admin_only": true, then use id_token.

  python3 scripts/apply_band_label_updates.py scripts/data/environmental_band_label_updates.json
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: apply_band_label_updates.py <updates.json>", file=sys.stderr)
        raise SystemExit(2)
    path = sys.argv[1]
    api_base = os.environ.get("HSM_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    project_id = os.environ.get("HSM_PROJECT_ID")
    token = os.environ.get("HSM_ID_TOKEN")
    if not project_id or not token:
        print("Set HSM_PROJECT_ID and HSM_ID_TOKEN.", file=sys.stderr)
        raise SystemExit(1)

    with open(path, encoding="utf-8") as f:
        updates = json.load(f)
    if not isinstance(updates, dict) or not updates:
        raise SystemExit("JSON must be a non-empty object")

    body = json.dumps(updates).encode("utf-8")
    req = urllib.request.Request(
        f"{api_base}/projects/{project_id}/environmental-band-definitions/labels",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req) as r:
            project = json.load(r)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"PATCH failed {e.code}: {err}") from e

    n = len(project.get("environmental_band_definitions") or [])
    print(f"OK: project {project_id!r} now has {n} band definition(s).")


if __name__ == "__main__":
    main()
