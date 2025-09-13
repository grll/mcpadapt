"""Tests for authentication provider classes."""

import httpx
from unittest.mock import Mock, patch
from mcpadapt.auth.providers import (
    ApiKeyAuthProvider,
    BearerAuthProvider,
    OAuthProvider,
)
from mcpadapt.auth.handlers import BaseOAuthHandler
from mcpadapt.auth.oauth import OAuthClientMetadata
from mcpadapt.auth import InMemoryTokenStorage
from pydantic import AnyUrl
from typing import List


class MockOAuthHandler(BaseOAuthHandler):
    """Mock OAuth handler for testing."""

    def get_redirect_uris(self) -> List[AnyUrl]:
        return [AnyUrl("http://localhost:3030/callback")]

    async def handle_redirect(self, authorization_url: str) -> None:
        pass

    async def handle_callback(self) -> tuple[str, str | None]:
        return "test_code", "test_state"


class TestApiKeyAuthProvider:
    """Test API key authentication provider."""

    def test_initialization(self):
        """Test basic initialization."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key-123")
        assert provider.header_name == "X-API-Key"
        assert provider.header_value == "test-key-123"

    def test_initialization_different_header(self):
        """Test initialization with different header name."""
        provider = ApiKeyAuthProvider("Authorization", "ApiKey test-key-456")
        assert provider.header_name == "Authorization"
        assert provider.header_value == "ApiKey test-key-456"

    def test_initialization_empty_values(self):
        """Test initialization with empty values."""
        provider = ApiKeyAuthProvider("", "")
        assert provider.header_name == ""
        assert provider.header_value == ""

    def test_httpx_auth_inheritance(self):
        """Test that ApiKeyAuthProvider inherits from httpx.Auth."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")
        assert isinstance(provider, httpx.Auth)

    def test_auth_flow_basic(self):
        """Test auth_flow method."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key-123")
        request = httpx.Request("GET", "https://example.com")
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["X-API-Key"] == "test-key-123"

    def test_auth_flow_different_header(self):
        """Test auth_flow with different header name."""
        provider = ApiKeyAuthProvider("Custom-Auth", "custom-value")
        request = httpx.Request("GET", "https://example.com")
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["Custom-Auth"] == "custom-value"

    def test_auth_flow_preserves_existing_headers(self):
        """Test that auth_flow preserves existing headers."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")
        request = httpx.Request("GET", "https://example.com", headers={"User-Agent": "test"})
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["X-API-Key"] == "test-key"
        assert authenticated_request.headers["User-Agent"] == "test"

    def test_auth_flow_multiple_calls(self):
        """Test multiple calls to auth_flow return consistent results."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")

        for _ in range(5):
            request = httpx.Request("GET", "https://example.com")
            auth_gen = provider.auth_flow(request)
            authenticated_request = next(auth_gen)
            assert authenticated_request.headers["X-API-Key"] == "test-key"

    def test_auth_flow_with_special_characters(self):
        """Test auth_flow with special characters in values."""
        provider = ApiKeyAuthProvider("X-API-Key", "key!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`")
        request = httpx.Request("GET", "https://example.com")
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["X-API-Key"] == "key!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"


class TestBearerAuthProvider:
    """Test Bearer token authentication provider."""

    def test_initialization_with_string_token(self):
        """Test basic initialization with string token."""
        provider = BearerAuthProvider("test-token-123")
        assert provider._token == "test-token-123"

    def test_initialization_with_callable_token(self):
        """Test initialization with callable token."""
        def get_token():
            return "dynamic-token"
        
        provider = BearerAuthProvider(get_token)
        assert provider._token == get_token
        assert callable(provider._token)

    def test_httpx_auth_inheritance(self):
        """Test that BearerAuthProvider inherits from httpx.Auth."""
        provider = BearerAuthProvider("test-token")
        assert isinstance(provider, httpx.Auth)

    def test_auth_flow_with_string_token(self):
        """Test auth_flow with string token."""
        provider = BearerAuthProvider("test-token-123")
        request = httpx.Request("GET", "https://example.com")
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["Authorization"] == "Bearer test-token-123"

    def test_auth_flow_with_callable_token(self):
        """Test auth_flow with callable token."""
        call_count = 0
        
        def get_token():
            nonlocal call_count
            call_count += 1
            return f"dynamic-token-{call_count}"
        
        provider = BearerAuthProvider(get_token)
        
        # First call
        request1 = httpx.Request("GET", "https://example.com")
        auth_gen1 = provider.auth_flow(request1)
        authenticated_request1 = next(auth_gen1)
        assert authenticated_request1.headers["Authorization"] == "Bearer dynamic-token-1"
        
        # Second call should get a new token
        request2 = httpx.Request("GET", "https://example.com")
        auth_gen2 = provider.auth_flow(request2)
        authenticated_request2 = next(auth_gen2)
        assert authenticated_request2.headers["Authorization"] == "Bearer dynamic-token-2"

    def test_auth_flow_preserves_existing_headers(self):
        """Test that auth_flow preserves existing headers."""
        provider = BearerAuthProvider("test-token")
        request = httpx.Request("GET", "https://example.com", headers={"User-Agent": "test"})
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["Authorization"] == "Bearer test-token"
        assert authenticated_request.headers["User-Agent"] == "test"

    def test_get_token_value_with_string(self):
        """Test _get_token_value with string token."""
        provider = BearerAuthProvider("static-token")
        assert provider._get_token_value() == "static-token"

    def test_get_token_value_with_callable(self):
        """Test _get_token_value with callable token."""
        def get_token():
            return "callable-token"
        
        provider = BearerAuthProvider(get_token)
        assert provider._get_token_value() == "callable-token"

    def test_auth_flow_with_complex_tokens(self):
        """Test auth_flow with complex token formats."""
        test_tokens = [
            "simple_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",  # JWT-like
            "ghp_1234567890abcdef1234567890abcdef12345678",  # GitHub token-like
            "sk-1234567890abcdef1234567890abcdef1234567890abcdef1234567890",  # OpenAI-like
        ]

        for token in test_tokens:
            provider = BearerAuthProvider(token)
            request = httpx.Request("GET", "https://example.com")
            
            auth_gen = provider.auth_flow(request)
            authenticated_request = next(auth_gen)
            
            assert authenticated_request.headers["Authorization"] == f"Bearer {token}"

    def test_auth_flow_with_empty_token(self):
        """Test auth_flow with empty token."""
        provider = BearerAuthProvider("")
        request = httpx.Request("GET", "https://example.com")
        
        auth_gen = provider.auth_flow(request)
        authenticated_request = next(auth_gen)
        
        assert authenticated_request.headers["Authorization"] == "Bearer "

    def test_callable_token_exception_handling(self):
        """Test that exceptions in callable tokens are not caught by provider."""
        def failing_token():
            raise ValueError("Token generation failed")
        
        provider = BearerAuthProvider(failing_token)
        request = httpx.Request("GET", "https://example.com")
        
        # Should raise the exception from the callable
        try:
            auth_gen = provider.auth_flow(request)
            next(auth_gen)
            assert False, "Expected ValueError to be raised"
        except ValueError as e:
            assert str(e) == "Token generation failed"


class TestProviderIntegration:
    """Test provider integration scenarios."""

    def test_api_key_provider_with_httpx_client(self):
        """Test that ApiKeyAuthProvider works with httpx client."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key-123")
        
        # This would normally make a real request, but we're just testing the auth setup
        client = httpx.Client(auth=provider)
        assert client._auth is provider

    def test_bearer_provider_with_httpx_client(self):
        """Test that BearerAuthProvider works with httpx client."""
        provider = BearerAuthProvider("test-token-123")
        
        # This would normally make a real request, but we're just testing the auth setup
        client = httpx.Client(auth=provider)
        assert client._auth is provider

    def test_both_providers_are_httpx_auth_instances(self):
        """Test that both providers are proper httpx.Auth instances."""
        api_provider = ApiKeyAuthProvider("X-API-Key", "key")
        bearer_provider = BearerAuthProvider("token")
        
        assert isinstance(api_provider, httpx.Auth)
        assert isinstance(bearer_provider, httpx.Auth)

    def test_providers_with_real_world_scenarios(self):
        """Test providers with realistic scenarios."""
        # API Key scenario
        api_provider = ApiKeyAuthProvider("X-RapidAPI-Key", "your-rapidapi-key-here")
        api_request = httpx.Request("GET", "https://api.example.com/data")
        api_auth_gen = api_provider.auth_flow(api_request)
        api_authenticated = next(api_auth_gen)
        assert api_authenticated.headers["X-RapidAPI-Key"] == "your-rapidapi-key-here"
        
        # Bearer token scenario
        bearer_provider = BearerAuthProvider("your-jwt-token-here")
        bearer_request = httpx.Request("POST", "https://api.example.com/users")
        bearer_auth_gen = bearer_provider.auth_flow(bearer_request)
        bearer_authenticated = next(bearer_auth_gen)
        assert bearer_authenticated.headers["Authorization"] == "Bearer your-jwt-token-here"

    def test_callable_token_refresh_scenario(self):
        """Test callable token for token refresh scenarios."""
        refresh_count = 0
        
        def refresh_token():
            nonlocal refresh_count
            refresh_count += 1
            return f"refreshed-token-{refresh_count}"
        
        provider = BearerAuthProvider(refresh_token)
        
        # Simulate multiple API calls that would refresh the token
        for i in range(3):
            request = httpx.Request("GET", "https://api.example.com")
            auth_gen = provider.auth_flow(request)
            authenticated_request = next(auth_gen)
            expected_token = f"refreshed-token-{i + 1}"
            assert authenticated_request.headers["Authorization"] == f"Bearer {expected_token}"


class TestOAuthProvider:
    """Test OAuthProvider class."""

    def test_initialization(self):
        """Test OAuthProvider initialization."""
        client_metadata = OAuthClientMetadata(
            client_name="Test App",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="client_secret_post",
        )

        oauth_handler = MockOAuthHandler(client_metadata)
        storage = InMemoryTokenStorage()

        provider = OAuthProvider(
            server_url="https://test-server.com",
            oauth_handler=oauth_handler,
            storage=storage,
        )

        # Verify the provider was created successfully
        assert provider is not None

    def test_oauth_provider_extracts_metadata(self):
        """Test that OAuthProvider properly extracts metadata from handler."""
        client_metadata = OAuthClientMetadata(
            client_name="Test App",
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="client_secret_post",
        )

        oauth_handler = MockOAuthHandler(client_metadata)
        storage = InMemoryTokenStorage()

        with patch("mcp.client.auth.OAuthClientProvider.__init__") as mock_init:
            mock_init.return_value = None

            OAuthProvider(
                server_url="https://test-server.com",
                oauth_handler=oauth_handler,
                storage=storage,
            )

            # Verify parent constructor was called with correct parameters
            mock_init.assert_called_once()
            call_args = mock_init.call_args

            assert call_args[1]["server_url"] == "https://test-server.com"
            assert call_args[1]["storage"] == storage
            assert call_args[1]["redirect_handler"] == oauth_handler.handle_redirect
            assert call_args[1]["callback_handler"] == oauth_handler.handle_callback

            # Verify client_metadata was properly constructed
            client_metadata_arg = call_args[1]["client_metadata"]
            assert client_metadata_arg.client_name == "Test App"
            assert len(client_metadata_arg.redirect_uris) == 1
            assert (
                str(client_metadata_arg.redirect_uris[0])
                == "http://localhost:3030/callback"
            )

    def test_oauth_provider_with_custom_handler(self):
        """Test OAuthProvider with custom handler that has different redirect URIs."""

        class CustomTestHandler(BaseOAuthHandler):
            def get_redirect_uris(self) -> List[AnyUrl]:
                return [AnyUrl("http://localhost:8080/auth/callback")]

            async def handle_redirect(self, authorization_url: str) -> None:
                pass

            async def handle_callback(self) -> tuple[str, str | None]:
                return "custom_code", "custom_state"

        client_metadata = OAuthClientMetadata(
            client_name="Custom Test App",
            grant_types=["authorization_code"],
            response_types=["code"],
            token_endpoint_auth_method="client_secret_post",
        )

        custom_handler = CustomTestHandler(client_metadata)
        storage = InMemoryTokenStorage()

        with patch("mcp.client.auth.OAuthClientProvider.__init__") as mock_init:
            mock_init.return_value = None

            OAuthProvider(
                server_url="https://custom-server.com",
                oauth_handler=custom_handler,
                storage=storage,
            )

            # Verify the custom redirect URI was used
            call_args = mock_init.call_args
            client_metadata_arg = call_args[1]["client_metadata"]
            assert len(client_metadata_arg.redirect_uris) == 1
            assert (
                str(client_metadata_arg.redirect_uris[0])
                == "http://localhost:8080/auth/callback"
            )
