"""Tests for authentication provider classes."""

from unittest.mock import Mock, AsyncMock, patch
from mcpadapt.auth.providers import (
    ApiKeyAuthProvider,
    BearerAuthProvider,
    OAuthProvider,
    get_auth_headers,
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

    def test_get_headers_basic(self):
        """Test get_headers method."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key-123")
        headers = provider.get_headers()

        assert isinstance(headers, dict)
        assert headers == {"X-API-Key": "test-key-123"}

    def test_get_headers_different_header(self):
        """Test get_headers with different header name."""
        provider = ApiKeyAuthProvider("Custom-Auth", "custom-value")
        headers = provider.get_headers()

        assert isinstance(headers, dict)
        assert headers == {"Custom-Auth": "custom-value"}

    def test_get_headers_returns_new_dict(self):
        """Test that get_headers returns a new dict instance each time."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")
        headers1 = provider.get_headers()
        headers2 = provider.get_headers()

        assert headers1 == headers2
        assert headers1 is not headers2  # Different instances

    def test_get_headers_multiple_calls(self):
        """Test multiple calls to get_headers return consistent results."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")

        for _ in range(5):
            headers = provider.get_headers()
            assert headers == {"X-API-Key": "test-key"}


class TestBearerAuthProvider:
    """Test Bearer token authentication provider."""

    def test_initialization(self):
        """Test basic initialization."""
        provider = BearerAuthProvider("test-token-123")
        assert provider.token == "test-token-123"

    def test_initialization_empty_token(self):
        """Test initialization with empty token."""
        provider = BearerAuthProvider("")
        assert provider.token == ""

    def test_initialization_complex_token(self):
        """Test initialization with complex token."""
        complex_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        provider = BearerAuthProvider(complex_token)
        assert provider.token == complex_token

    def test_get_headers_basic(self):
        """Test get_headers method."""
        provider = BearerAuthProvider("test-token-123")
        headers = provider.get_headers()

        assert isinstance(headers, dict)
        assert headers == {"Authorization": "Bearer test-token-123"}

    def test_get_headers_empty_token(self):
        """Test get_headers with empty token."""
        provider = BearerAuthProvider("")
        headers = provider.get_headers()

        assert isinstance(headers, dict)
        assert headers == {"Authorization": "Bearer "}

    def test_get_headers_returns_new_dict(self):
        """Test that get_headers returns a new dict instance each time."""
        provider = BearerAuthProvider("test-token")
        headers1 = provider.get_headers()
        headers2 = provider.get_headers()

        assert headers1 == headers2
        assert headers1 is not headers2  # Different instances

    def test_get_headers_multiple_calls(self):
        """Test multiple calls to get_headers return consistent results."""
        provider = BearerAuthProvider("test-token")

        for _ in range(5):
            headers = provider.get_headers()
            assert headers == {"Authorization": "Bearer test-token"}

    def test_bearer_format_consistency(self):
        """Test that Bearer format is consistent."""
        tokens = [
            "simple",
            "complex.token.here",
            "token-with-dashes",
            "token_with_underscores",
        ]

        for token in tokens:
            provider = BearerAuthProvider(token)
            headers = provider.get_headers()
            assert headers["Authorization"] == f"Bearer {token}"
            assert headers["Authorization"].startswith("Bearer ")


class TestGetAuthHeaders:
    """Test get_auth_headers utility function."""

    def test_with_api_key_provider(self):
        """Test with ApiKeyAuthProvider."""
        provider = ApiKeyAuthProvider("X-API-Key", "test-key")
        headers = get_auth_headers(provider)

        assert isinstance(headers, dict)
        assert headers == {"X-API-Key": "test-key"}

    def test_with_bearer_provider(self):
        """Test with BearerAuthProvider."""
        provider = BearerAuthProvider("test-token")
        headers = get_auth_headers(provider)

        assert isinstance(headers, dict)
        assert headers == {"Authorization": "Bearer test-token"}

    def test_with_unknown_provider(self):
        """Test with unknown provider type."""
        unknown_provider = Mock()
        headers = get_auth_headers(unknown_provider)

        assert isinstance(headers, dict)
        assert headers == {}

    def test_with_none_provider(self):
        """Test with None provider."""
        headers = get_auth_headers(None)

        assert isinstance(headers, dict)
        assert headers == {}

    def test_with_provider_without_get_headers(self):
        """Test with object that doesn't have get_headers method."""
        fake_provider = object()
        headers = get_auth_headers(fake_provider)

        assert isinstance(headers, dict)
        assert headers == {}

    def test_with_string_provider(self):
        """Test with string instead of provider object."""
        headers = get_auth_headers("not-a-provider")

        assert isinstance(headers, dict)
        assert headers == {}

    def test_with_dict_provider(self):
        """Test with dict instead of provider object."""
        headers = get_auth_headers({"key": "value"})

        assert isinstance(headers, dict)
        assert headers == {}

    def test_multiple_provider_types(self):
        """Test with multiple different provider types in sequence."""
        api_key_provider = ApiKeyAuthProvider("X-API-Key", "api-key")
        bearer_provider = BearerAuthProvider("bearer-token")

        api_headers = get_auth_headers(api_key_provider)
        bearer_headers = get_auth_headers(bearer_provider)
        none_headers = get_auth_headers(None)

        assert api_headers == {"X-API-Key": "api-key"}
        assert bearer_headers == {"Authorization": "Bearer bearer-token"}
        assert none_headers == {}

    def test_provider_inheritance_check(self):
        """Test that the function properly checks instance types."""

        # Create a class that has get_headers but isn't a known provider
        class FakeProvider:
            def get_headers(self):
                return {"Fake": "header"}

        fake = FakeProvider()
        headers = get_auth_headers(fake)

        # Should return empty dict since it's not an ApiKeyAuthProvider or BearerAuthProvider
        assert headers == {}


class TestProviderIntegration:
    """Test provider integration scenarios."""

    def test_api_key_provider_real_world_headers(self):
        """Test API key provider with real-world header names."""
        test_cases = [
            ("X-API-Key", "sk-1234567890abcdef"),
            ("Authorization", "ApiKey sk-abcdef1234567890"),
            ("X-RapidAPI-Key", "rapidapi-key-here"),
            ("Ocp-Apim-Subscription-Key", "azure-key"),
            ("x-api-key", "lowercase-header"),
        ]

        for header_name, header_value in test_cases:
            provider = ApiKeyAuthProvider(header_name, header_value)
            headers = provider.get_headers()
            assert headers == {header_name: header_value}

    def test_bearer_provider_real_world_tokens(self):
        """Test Bearer provider with real-world token formats."""
        test_tokens = [
            "simple_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature",  # JWT-like
            "ghp_1234567890abcdef1234567890abcdef12345678",  # GitHub token-like
            "sk-1234567890abcdef1234567890abcdef1234567890abcdef1234567890",  # OpenAI-like
            "xoxb-1234567890-1234567890-abcdefghijklmnopqrstuvwx",  # Slack-like
        ]

        for token in test_tokens:
            provider = BearerAuthProvider(token)
            headers = provider.get_headers()
            assert headers == {"Authorization": f"Bearer {token}"}

    def test_providers_with_special_characters(self):
        """Test providers with special characters in values."""
        # API Key with special characters
        api_provider = ApiKeyAuthProvider(
            "X-API-Key", "key!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"
        )
        api_headers = api_provider.get_headers()
        assert "X-API-Key" in api_headers
        assert api_headers["X-API-Key"] == "key!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"

        # Bearer token with special characters
        bearer_provider = BearerAuthProvider("token!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`")
        bearer_headers = bearer_provider.get_headers()
        assert (
            bearer_headers["Authorization"]
            == "Bearer token!@#$%^&*()_+-={}[]|\\:;\"'<>,.?/~`"
        )

    def test_providers_immutability(self):
        """Test that providers don't modify their internal state."""
        # Test API Key provider
        api_provider = ApiKeyAuthProvider("X-API-Key", "original-key")
        original_name = api_provider.header_name
        original_value = api_provider.header_value

        # Get headers multiple times
        for _ in range(3):
            headers = api_provider.get_headers()
            headers["X-API-Key"] = "modified-key"  # Try to modify returned dict

        # Verify original values unchanged
        assert api_provider.header_name == original_name
        assert api_provider.header_value == original_value

        # Test Bearer provider
        bearer_provider = BearerAuthProvider("original-token")
        original_token = bearer_provider.token

        # Get headers multiple times
        for _ in range(3):
            headers = bearer_provider.get_headers()
            headers["Authorization"] = (
                "Bearer modified-token"  # Try to modify returned dict
            )

        # Verify original token unchanged
        assert bearer_provider.token == original_token


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
        
        with patch('mcp.client.auth.OAuthClientProvider.__init__') as mock_init:
            mock_init.return_value = None
            
            OAuthProvider(
                server_url="https://test-server.com",
                oauth_handler=oauth_handler,
                storage=storage,
            )
            
            # Verify parent constructor was called with correct parameters
            mock_init.assert_called_once()
            call_args = mock_init.call_args
            
            assert call_args[1]['server_url'] == "https://test-server.com"
            assert call_args[1]['storage'] == storage
            assert call_args[1]['redirect_handler'] == oauth_handler.handle_redirect
            assert call_args[1]['callback_handler'] == oauth_handler.handle_callback
            
            # Verify client_metadata was properly constructed
            client_metadata_arg = call_args[1]['client_metadata']
            assert client_metadata_arg.client_name == "Test App"
            assert len(client_metadata_arg.redirect_uris) == 1
            assert str(client_metadata_arg.redirect_uris[0]) == "http://localhost:3030/callback"

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
        
        with patch('mcp.client.auth.OAuthClientProvider.__init__') as mock_init:
            mock_init.return_value = None
            
            OAuthProvider(
                server_url="https://custom-server.com",
                oauth_handler=custom_handler,
                storage=storage,
            )
            
            # Verify the custom redirect URI was used
            call_args = mock_init.call_args
            client_metadata_arg = call_args[1]['client_metadata']
            assert len(client_metadata_arg.redirect_uris) == 1
            assert str(client_metadata_arg.redirect_uris[0]) == "http://localhost:8080/auth/callback"
