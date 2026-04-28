"""Smoke tests across every resource — one request per method."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from floopfloop import FloopClient, FloopError


def test_projects_create_posts_and_returns_project(
    httpx_mock: HTTPXMock, client: FloopClient
) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects",
        method="POST",
        json={
            "data": {
                "project": {"id": "p1", "name": "n", "subdomain": "s", "status": "queued"},
                "deployment": {"id": "d1", "status": "queued", "version": 1},
            }
        },
    )
    out = client.projects.create(prompt="hi", name="n", subdomain="s")
    assert out["project"]["id"] == "p1"


def test_projects_list_with_team_id(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects?teamId=team_42",
        json={"data": []},
    )
    assert client.projects.list(team_id="team_42") == []


def test_projects_get_filters_list(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects",
        json={
            "data": [
                {"id": "p1", "subdomain": "foo", "status": "live"},
                {"id": "p2", "subdomain": "bar", "status": "live"},
            ]
        },
    )
    got = client.projects.get("bar")
    assert got["id"] == "p2"


def test_projects_get_raises_not_found(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects",
        json={"data": []},
    )
    with pytest.raises(FloopError) as exc:
        client.projects.get("nope")
    assert exc.value.code == "NOT_FOUND"


def test_projects_cancel(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p1/cancel",
        method="POST",
        json={"data": {"success": True}},
    )
    client.projects.cancel("p1")


def test_secrets_flow(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p1/secrets",
        method="GET",
        json={"data": {"secrets": [{"key": "K", "lastFour": "abcd", "createdAt": "", "updatedAt": ""}]}},
    )
    assert client.secrets.list("p1")[0]["key"] == "K"

    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p1/secrets",
        method="POST",
        json={"data": {"secret": {"key": "K", "lastFour": "wxyz", "createdAt": "", "updatedAt": ""}}},
    )
    assert client.secrets.set("p1", "K", "v")["lastFour"] == "wxyz"

    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/projects/p1/secrets/K",
        method="DELETE",
        json={"data": {"success": True, "existed": True}},
    )
    assert client.secrets.remove("p1", "K")["existed"] is True


def test_api_keys_remove_by_name(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/api-keys",
        method="GET",
        json={"data": {"keys": [{"id": "k9", "name": "ci", "keyPrefix": "flp_ab", "scopes": [], "lastUsedAt": None, "createdAt": ""}]}},
    )
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/api-keys/k9",
        method="DELETE",
        json={"data": {"success": True}},
    )
    client.api_keys.remove("ci")


def test_api_keys_remove_not_found(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/api-keys",
        method="GET",
        json={"data": {"keys": []}},
    )
    with pytest.raises(FloopError) as exc:
        client.api_keys.remove("nope")
    assert exc.value.code == "NOT_FOUND"


def test_library_list_paged_wrapper(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/library",
        json={"data": {"items": [{"id": "l2", "name": "B", "description": None, "subdomain": "b", "botType": None, "cloneCount": 1, "createdAt": ""}], "total": 1}},
    )
    assert client.library.list()[0]["id"] == "l2"


def test_library_clone(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/library/l2/clone",
        method="POST",
        json={"data": {"id": "p9", "name": "B", "subdomain": "my-b", "status": "queued"}},
    )
    assert client.library.clone("l2", subdomain="my-b")["id"] == "p9"


def test_subdomains_check(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subdomains/check?subdomain=taken",
        json={"data": {"valid": True, "available": False}},
    )
    assert client.subdomains.check("taken")["available"] is False


def test_subdomains_suggest(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subdomains/suggest?prompt=a+joyful+panda+blog",
        json={"data": {"suggestion": "joyful-panda-42"}},
    )
    assert client.subdomains.suggest("a joyful panda blog")["suggestion"] == "joyful-panda-42"


def test_usage_summary(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/usage/summary",
        json={"data": {"plan": {"name": "free", "displayName": "Free", "monthlyCredits": 10, "maxProjects": 3, "maxStorageMb": 50, "maxBandwidthMb": 500}, "credits": {"currentCredits": 8, "rolledOverCredits": 0, "lifetimeCreditsUsed": 2, "rolloverExpiresAt": None}, "currentPeriod": {"start": "", "end": "", "projectsCreated": 1, "buildsUsed": 2, "refinementsUsed": 0, "storageUsedMb": 1, "bandwidthUsedMb": 5}}},
    )
    assert client.usage.summary()["plan"]["name"] == "free"


def test_subscriptions_current_populated(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subscriptions/current",
        json={
            "data": {
                "subscription": {
                    "status": "active",
                    "billingPeriod": "monthly",
                    "currentPeriodStart": "2026-04-01T00:00:00Z",
                    "currentPeriodEnd": "2026-05-01T00:00:00Z",
                    "canceledAt": None,
                    "planName": "pro",
                    "planDisplayName": "Pro",
                    "priceMonthly": 29,
                    "priceAnnual": 290,
                    "monthlyCredits": 500,
                    "maxProjects": 50,
                    "maxStorageMb": 5000,
                    "maxBandwidthMb": 50000,
                    "creditRolloverMonths": 1,
                    "features": {"teams": True},
                },
                "credits": {
                    "current": 423,
                    "rolledOver": 50,
                    "total": 473,
                    "rolloverExpiresAt": "2026-05-01T00:00:00Z",
                    "lifetimeUsed": 1234,
                },
            }
        },
    )
    out = client.subscriptions.current()
    assert out["subscription"]["planName"] == "pro"
    assert out["credits"]["total"] == 473


def test_subscriptions_current_both_null(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/subscriptions/current",
        json={"data": {"subscription": None, "credits": None}},
    )
    out = client.subscriptions.current()
    assert out["subscription"] is None
    assert out["credits"] is None


def test_user_me(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/user/me",
        json={"data": {"user": {"id": "u1", "email": "a@b", "role": "member"}, "source": "api_key"}},
    )
    assert client.user.me()["user"]["id"] == "u1"


def test_uploads_validation_unknown_ext(client: FloopClient) -> None:
    with pytest.raises(FloopError) as exc:
        client.uploads.create(file_name="weird.xyz", content=b"")
    assert exc.value.code == "VALIDATION_ERROR"


def test_uploads_validation_oversized(client: FloopClient) -> None:
    with pytest.raises(FloopError) as exc:
        client.uploads.create(file_name="big.png", content=b"\0" * (6 * 1024 * 1024))
    assert exc.value.code == "VALIDATION_ERROR"


def test_uploads_happy_path(httpx_mock: HTTPXMock, client: FloopClient) -> None:
    httpx_mock.add_response(
        url="https://www.floopfloop.com/api/v1/uploads",
        method="POST",
        json={"data": {"uploadUrl": "https://s3.example/upload", "key": "k1", "fileId": "f1"}},
    )
    httpx_mock.add_response(
        url="https://s3.example/upload",
        method="PUT",
        status_code=200,
    )
    out = client.uploads.create(file_name="hi.txt", content=b"hello")
    assert out == {"key": "k1", "fileName": "hi.txt", "fileType": "text/plain", "fileSize": 5}


def test_client_wires_all_resources(client: FloopClient) -> None:
    for name in [
        "projects",
        "secrets",
        "api_keys",
        "library",
        "subdomains",
        "subscriptions",
        "uploads",
        "usage",
        "user",
    ]:
        assert getattr(client, name) is not None
