import httpx
import pytest

from python_backend.services.ai import spartan_auth_service


def make_response(json_payload, status_code=200):
    request = httpx.Request("GET", "http://spartan/test")
    return httpx.Response(status_code, json=json_payload, request=request)


def test_get_gemini_provider_status_normalizes_spartan_contract(monkeypatch):
    def fake_request(method, url, timeout):
        assert method == "GET"
        assert url == "http://spartan/auth/gemini/status"
        assert timeout == 5
        return make_response(
            {
                "connected": False,
                "reconnectRequired": True,
                "message": "Provider is not connected",
                "reason": "not_connected",
                "connection": None,
            }
        )

    monkeypatch.setattr(httpx, "request", fake_request)

    result = spartan_auth_service.get_provider_status(
        "gemini",
        spartan_auth_service.SpartanAuthConfig(base_url="http://spartan", timeout_seconds=5),
    )

    assert result == {
        "provider": "gemini",
        "connected": False,
        "reconnect_required": True,
        "message": "Provider is not connected",
        "reason": "not_connected",
        "connection": None,
    }


def test_start_codex_connection_uses_legacy_oauth_callback(monkeypatch):
    requested_urls = []

    def fake_request(method, url, timeout):
        requested_urls.append(url)
        if url == "http://spartan/providers":
            return make_response(
                [
                    {
                        "id": "codex-provider-id",
                        "providerType": "codex_subscription",
                        "isEnabled": True,
                    }
                ]
            )
        if url == "http://spartan/providers/codex-provider-id/oauth/start":
            return make_response(
                {
                    "authorizationUrl": "https://auth.openai.com/oauth/authorize?redirect_uri=http%3A%2F%2Flocalhost%3A1455%2Fauth%2Fcallback",
                    "state": "abc",
                }
            )
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(httpx, "request", fake_request)

    result = spartan_auth_service.start_provider_connection(
        "codex",
        spartan_auth_service.SpartanAuthConfig(base_url="http://spartan"),
    )

    assert requested_urls == [
        "http://spartan/providers",
        "http://spartan/providers/codex-provider-id/oauth/start",
    ]
    assert result["provider"] == "codex"
    assert "localhost%3A1455" in result["authorization_url"]


def test_start_gemini_provider_connection_returns_authorization_url(monkeypatch):
    def fake_request(method, url, timeout):
        assert method == "GET"
        assert url == "http://spartan/auth/gemini/start"
        return make_response({"authorizationUrl": "https://accounts.google.com/oauth", "state": "abc"})

    monkeypatch.setattr(httpx, "request", fake_request)

    result = spartan_auth_service.start_provider_connection(
        "gemini",
        spartan_auth_service.SpartanAuthConfig(base_url="http://spartan"),
    )

    assert result == {
        "provider": "gemini",
        "authorization_url": "https://accounts.google.com/oauth",
        "state": "abc",
    }


def test_start_provider_connection_requires_authorization_url(monkeypatch):
    def fake_request(method, url, timeout):
        if url.endswith("/providers"):
            return make_response(
                [{"id": "codex-provider-id", "providerType": "codex_subscription", "isEnabled": True}]
            )
        return make_response({})

    monkeypatch.setattr(httpx, "request", fake_request)

    with pytest.raises(spartan_auth_service.SpartanAuthServiceError, match="authorizationUrl"):
        spartan_auth_service.start_provider_connection("codex")


def test_provider_validation_rejects_unknown_provider():
    with pytest.raises(spartan_auth_service.SpartanAuthServiceError, match="no soportado"):
        spartan_auth_service.get_provider_status("openai")


def test_list_provider_statuses_is_resilient(monkeypatch):
    def fake_get_provider_status(provider, config=None):
        if provider == "codex":
            raise spartan_auth_service.SpartanAuthServiceError("spartan caído")
        return {
            "provider": provider,
            "connected": True,
            "reconnect_required": False,
            "message": "Connected",
            "reason": "",
            "connection": {},
        }

    monkeypatch.setattr(spartan_auth_service, "get_provider_status", fake_get_provider_status)

    result = spartan_auth_service.list_provider_statuses()

    assert result[0]["provider"] == "codex"
    assert result[0]["reconnect_required"] is True
    assert result[1]["provider"] == "gemini"
    assert result[1]["connected"] is True


def test_codex_legacy_status_with_expired_token_requires_reconnect(monkeypatch):
    def fake_request(method, url, timeout):
        if url == "http://spartan/providers":
            return make_response(
                [{"id": "codex-provider-id", "providerType": "codex_subscription", "isEnabled": True}]
            )
        if url == "http://spartan/providers/codex-provider-id/auth/status":
            return make_response(
                {
                    "id": "credential-id",
                    "loginStatus": "authenticated",
                    "refreshTokenExists": True,
                    "tokenExpiresAt": "2026-07-19T01:58:57.929Z",
                }
            )
        raise AssertionError(f"unexpected url {url}")

    monkeypatch.setattr(httpx, "request", fake_request)

    result = spartan_auth_service.get_provider_status(
        "codex",
        spartan_auth_service.SpartanAuthConfig(base_url="http://spartan"),
    )

    assert result["connected"] is False
    assert result["reconnect_required"] is True
    assert result["reason"] == "token_expired"
    assert "reautenticación" in result["message"]
