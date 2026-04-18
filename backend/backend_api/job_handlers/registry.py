"""Dispatch table: :class:`JobKind` → async handler (typed input)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from backend_api.job_handlers.context import JobRunContext

from . import environmental_cog_replace
from . import explainability_background
from . import model_create_upload
from . import model_replace_cog
from . import project_create_env
from backend_api.schemas_job import JobKind, parse_job_input_payload

_HandlerFn = Callable[..., Awaitable[None]]

_HANDLERS: dict[JobKind, _HandlerFn] = {
    JobKind.ENVIRONMENTAL_COG_REPLACE: environmental_cog_replace.run,
    JobKind.PROJECT_CREATE_WITH_ENV_UPLOAD: project_create_env.run,
    JobKind.MODEL_CREATE_WITH_UPLOAD: model_create_upload.run,
    JobKind.MODEL_REPLACE_SUITABILITY_COG: model_replace_cog.run,
    JobKind.EXPLAINABILITY_BACKGROUND_REGENERATE: explainability_background.run,
}


def get_job_handler(kind: JobKind) -> _HandlerFn | None:
    return _HANDLERS.get(kind)


async def run_job_handler(
    ctx: JobRunContext,
    kind: JobKind,
    raw_input: dict[str, Any],
    handler: _HandlerFn,
) -> None:
    """Parse ``raw_input`` for ``kind`` and invoke ``handler`` (:func:`get_job_handler` in :mod:`job_runner`)."""
    payload = parse_job_input_payload(kind, raw_input)
    await handler(ctx, payload)
