"""Tests for the Kimi provider's transport behaviour: retries and diagnostics."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from oi.providers.model_client import ExtractedFields, ExtractionError

pytest.importorskip("openai")

from oi.providers.kimi import (  # noqa: E402
    MAX_ATTEMPTS,
    REQUEST_TIMEOUT_SECONDS,
    KimiClient,
)

CV_TEXT = "Giulia Rossi\nSkills: Python\n"

VALID_REPLY = json.dumps(
    {
        "skills": [{"value": "Python", "quote": "Skills: Python"}],
        "education": [],
        "experience": [],
        "languages": [],
    }
)

#: Stands in for model output that must never reach an error message.
SECRET_REASONING = "Giulia Rossi reasoning text that must not leak"


def reply(
    content: str | None,
    finish_reason: str = "stop",
    reasoning_content: str | None = None,
    completion_tokens: int | None = 32,
) -> Any:
    message = SimpleNamespace(content=content, reasoning_content=reasoning_content)
    usage = (
        None
        if completion_tokens is None
        else SimpleNamespace(completion_tokens=completion_tokens)
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=usage,
    )


def kimi_with_replies(*replies: Any) -> Any:
    """A KimiClient whose endpoint returns `replies` in order, one per call."""
    client = KimiClient(api_key="test-key")
    pending = list(replies)
    requests: list[dict[str, Any]] = []

    def create(**kwargs: Any) -> Any:
        requests.append(kwargs)
        return pending.pop(0)

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    client.requests = requests
    return client


def test_successful_reply_is_requested_once() -> None:
    client = kimi_with_replies(reply(VALID_REPLY))

    fields = client.extract_candidate_fields(CV_TEXT)

    assert fields == ExtractedFields.model_validate_json(VALID_REPLY)
    assert len(client.requests) == 1
    assert client.requests[0]["response_format"]["json_schema"]["strict"] is True


@pytest.mark.parametrize("empty", [None, "", "  \n"])
def test_empty_reply_is_retried_until_content_arrives(empty: str | None) -> None:
    client = kimi_with_replies(reply(empty), reply(empty), reply(VALID_REPLY))

    fields = client.extract_candidate_fields(CV_TEXT)

    assert fields == ExtractedFields.model_validate_json(VALID_REPLY)
    assert len(client.requests) == 3
    # Every retry sends the identical request.
    assert all(request == client.requests[0] for request in client.requests)


def test_empty_reply_on_every_attempt_raises_extraction_error() -> None:
    client = kimi_with_replies(*[reply(None) for _ in range(MAX_ATTEMPTS)])

    with pytest.raises(ExtractionError, match="empty response body on all 3"):
        client.extract_candidate_fields(CV_TEXT)

    assert len(client.requests) == MAX_ATTEMPTS == 3


def test_final_failure_reports_diagnostics_of_last_attempt() -> None:
    client = kimi_with_replies(
        reply(None, completion_tokens=5),
        reply(None, completion_tokens=7),
        reply(None, reasoning_content="!!!!", completion_tokens=32),
    )

    with pytest.raises(ExtractionError) as excinfo:
        client.extract_candidate_fields(CV_TEXT)

    message = str(excinfo.value)
    assert "finish_reason='stop'" in message
    assert "completion_tokens=32" in message
    assert "reasoning_content=present" in message


def test_final_failure_handles_missing_usage_and_reasoning() -> None:
    client = kimi_with_replies(
        *[reply(None, completion_tokens=None) for _ in range(MAX_ATTEMPTS)]
    )

    with pytest.raises(ExtractionError) as excinfo:
        client.extract_candidate_fields(CV_TEXT)

    message = str(excinfo.value)
    assert "completion_tokens=unknown" in message
    assert "reasoning_content=absent" in message


def test_diagnostics_do_not_leak_model_output_or_cv() -> None:
    client = kimi_with_replies(
        *[reply("", reasoning_content=SECRET_REASONING) for _ in range(MAX_ATTEMPTS)]
    )

    with pytest.raises(ExtractionError) as excinfo:
        client.extract_candidate_fields(CV_TEXT)

    message = str(excinfo.value)
    assert SECRET_REASONING not in message
    assert "Giulia" not in message
    assert "Python" not in message


def test_invalid_json_is_not_retried() -> None:
    client = kimi_with_replies(reply("not json"), reply(VALID_REPLY))

    with pytest.raises(ExtractionError, match="valid JSON"):
        client.extract_candidate_fields(CV_TEXT)

    assert len(client.requests) == 1


def test_request_failure_is_not_retried() -> None:
    from openai import APIConnectionError

    client = KimiClient(api_key="test-key")
    calls = 0

    def create(**kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise APIConnectionError(request=None)  # type: ignore[arg-type]

    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    with pytest.raises(ExtractionError, match="request failed"):
        client.extract_candidate_fields(CV_TEXT)

    assert calls == 1


def test_client_uses_explicit_request_timeout() -> None:
    client = KimiClient(api_key="test-key")

    assert REQUEST_TIMEOUT_SECONDS == 120.0
    assert client._client.timeout == REQUEST_TIMEOUT_SECONDS
