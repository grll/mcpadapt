"""Shared fixtures for authentication tests."""

import pytest
from unittest.mock import Mock, AsyncMock
from mcp.shared.auth import OAuthClientMetadata, OAuthToken, OAuthClientInformationFull
from pydantic import HttpUrl


@pytest.fixture
def mock_oauth_client_metadata():
    """Mock OAuth client metadata."""
    return OAuthClientMetadata(
        client_name="Test App",
        redirect_uris=[HttpUrl("http://localhost:3030/callback")],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
    )


@pytest.fixture
def mock_oauth_token():
    """Mock OAuth token."""
    return OAuthToken(
        access_token="test_access_token",
        token_type="Bearer",
        expires_in=3600,
        refresh_token="test_refresh_token",
        scope="read write",
    )


@pytest.fixture
def mock_oauth_client_info():
    """Mock OAuth client information."""
    return OAuthClientInformationFull(
        client_id="test_client_id",
        client_secret="test_client_secret",
        client_id_issued_at=1234567890,
        client_secret_expires_at=0,
        redirect_uris=[HttpUrl("http://localhost:3030/callback")],
    )


@pytest.fixture
def mock_webbrowser(mocker):
    """Mock webbrowser module."""
    return mocker.patch("mcpadapt.auth.handlers.webbrowser")


@pytest.fixture
def mock_http_server(mocker):
    """Mock HTTPServer."""
    mock_server = Mock()
    mock_server.serve_forever = Mock()
    mock_server.shutdown = Mock()
    mock_server.server_close = Mock()

    mock_server_class = mocker.patch("mcpadapt.auth.handlers.HTTPServer")
    mock_server_class.return_value = mock_server

    return mock_server, mock_server_class


@pytest.fixture
def mock_threading(mocker):
    """Mock threading module."""
    mock_thread = Mock()
    mock_thread.start = Mock()
    mock_thread.join = Mock()

    mock_thread_class = mocker.patch("mcpadapt.auth.handlers.threading.Thread")
    mock_thread_class.return_value = mock_thread

    return mock_thread, mock_thread_class


@pytest.fixture
def mock_time(mocker):
    """Mock time module."""
    return mocker.patch("mcpadapt.auth.handlers.time")


@pytest.fixture
def callback_data_success():
    """Mock successful callback data."""
    return {
        "authorization_code": "test_auth_code",
        "state": "test_state",
        "error": None,
    }


@pytest.fixture
def callback_data_error():
    """Mock error callback data."""
    return {"authorization_code": None, "state": None, "error": "access_denied"}


@pytest.fixture
def mock_mcp_client_session():
    """Mock MCP ClientSession."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock()
    session.call_tool = AsyncMock()
    return session


@pytest.fixture
def mock_oauth_client_provider():
    """Mock OAuthClientProvider."""
    provider = Mock()
    provider.get_headers = Mock(return_value={"Authorization": "Bearer test_token"})
    return provider
