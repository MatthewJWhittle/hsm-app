"""Re-export settings from shared core (API and worker use the same config model)."""

from hsm_core.settings import Settings

__all__ = ["Settings"]
