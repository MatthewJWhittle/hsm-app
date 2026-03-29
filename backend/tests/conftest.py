"""Pytest hooks: env so Firebase Admin can init without GCP credentials."""

import os

# Tests run without GCP ADC; Auth emulator host lets Admin SDK initialize for verify_id_token mocks.
os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
