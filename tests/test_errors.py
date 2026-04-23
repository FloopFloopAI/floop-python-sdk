from floopfloop.errors import FloopError


def test_captures_code_status_message_and_request_id() -> None:
    err = FloopError(
        code="NOT_FOUND",
        message="project not found",
        status=404,
        request_id="req_abc",
    )
    assert isinstance(err, Exception)
    assert err.code == "NOT_FOUND"
    assert err.status == 404
    assert str(err) == "project not found"
    assert err.request_id == "req_abc"


def test_unknown_string_codes_pass_through() -> None:
    err = FloopError(code="SOMETHING_NEW", message="weird", status=418)
    assert err.code == "SOMETHING_NEW"


def test_retry_after_ms_optional() -> None:
    err = FloopError(
        code="RATE_LIMITED", message="slow down", status=429, retry_after_ms=4000
    )
    assert err.retry_after_ms == 4000
