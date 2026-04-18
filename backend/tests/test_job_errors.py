"""Job retryable error classification."""

from __future__ import annotations

import pytest

from backend_api.job_errors import (
    JobRetryableError,
    is_retryable_infra_error,
    wrap_pipeline_infra_errors,
)


def test_job_retryable_error_code():
    e = JobRetryableError("x", code="CUSTOM")
    assert e.code == "CUSTOM"


def test_is_retryable_google_unavailable():
    try:
        from google.api_core import exceptions as gexc

        assert is_retryable_infra_error(gexc.ServiceUnavailable("x"))
    except ImportError:
        pytest.skip("google-api-core not available")


def test_wrap_raises_job_retryable_for_service_unavailable():
    try:
        from google.api_core import exceptions as gexc

        with pytest.raises(JobRetryableError) as ei:
            wrap_pipeline_infra_errors(gexc.ServiceUnavailable("down"))
        assert "down" in str(ei.value)
    except ImportError:
        pytest.skip("google-api-core not available")


def test_wrap_reraises_non_infra():
    with pytest.raises(ValueError, match="bad"):
        wrap_pipeline_infra_errors(ValueError("bad"))
