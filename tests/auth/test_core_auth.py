"""Tests for authentication integration with MCPAdapt core."""

import pytest
from typing import Any, Callable, Coroutine
from unittest.mock import Mock, patch, AsyncMock

from mcpadapt.core import MCPAdapt, mcptools, ToolAdapter
from mcpadapt.auth.providers import ApiKeyAuthProvider, BearerAuthProvider


class DummyAdapter(ToolAdapter):
    """Dummy adapter for testing."""

    def adapt(self, func: Callable[[dict[str, Any] | None], Any], mcp_tool: Any) -> Any:
        return func

    def async_adapt(
        self,
        afunc: Callable[[dict[str, Any] | None], Coroutine[Any, Any, Any]],
        mcp_tool: Any,
    ) -> Any:
        return afunc


class TestMCPAdaptAuthIntegration:
    """Test authentication integration with MCPAdapt."""

    def test_api_key_auth_provider_sync(self):
        """Test API key authentication with sync MCPAdapt."""
        auth_provider = ApiKeyAuthProvider("X-API-Key", "test-key-123")

        # Mock server parameters for streamable-http
        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        # Mock the mcptools function to verify auth headers are passed
        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            # Verify auth provider is stored
            assert adapter.auth_providers[0] is auth_provider

    def test_bearer_auth_provider_sync(self):
        """Test Bearer token authentication with sync MCPAdapt."""
        auth_provider = BearerAuthProvider("bearer-token-456")

        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            assert adapter.auth_providers[0] is auth_provider

    def test_multiple_servers_different_auth(self):
        """Test multiple servers with different authentication."""
        api_key_provider = ApiKeyAuthProvider("X-API-Key", "api-key")
        bearer_provider = BearerAuthProvider("bearer-token")

        server_params = [
            {"url": "https://api1.example.com/mcp", "transport": "streamable-http"},
            {"url": "https://api2.example.com/mcp", "transport": "streamable-http"},
        ]

        auth_providers = [api_key_provider, bearer_provider]

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_providers,
            )

            assert len(adapter.auth_providers) == 2
            assert adapter.auth_providers[0] is api_key_provider
            assert adapter.auth_providers[1] is bearer_provider

    def test_auth_provider_list_length_mismatch(self):
        """Test auth provider list length mismatch raises error."""
        server_params = [
            {"url": "https://api1.example.com/mcp", "transport": "streamable-http"},
            {"url": "https://api2.example.com/mcp", "transport": "streamable-http"},
        ]

        # Only one auth provider for two servers
        auth_providers = [ApiKeyAuthProvider("X-API-Key", "key")]

        with pytest.raises(ValueError) as exc_info:
            MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_providers,
            )

        assert (
            "auth_provider list length (1) must match serverparams length (2)"
            in str(exc_info.value)
        )

    def test_single_auth_provider_for_multiple_servers(self):
        """Test single auth provider applied to multiple servers."""
        auth_provider = ApiKeyAuthProvider("X-API-Key", "shared-key")

        server_params = [
            {"url": "https://api1.example.com/mcp", "transport": "streamable-http"},
            {"url": "https://api2.example.com/mcp", "transport": "streamable-http"},
        ]

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            # Should replicate auth provider for each server
            assert len(adapter.auth_providers) == 2
            assert adapter.auth_providers[0] is auth_provider
            assert adapter.auth_providers[1] is auth_provider

    def test_no_auth_provider(self):
        """Test MCPAdapt without authentication."""
        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(serverparams=server_params, adapter=DummyAdapter())

            # Should have None for auth providers
            assert len(adapter.auth_providers) == 1
            assert adapter.auth_providers[0] is None


class TestMCPToolsAuthIntegration:
    """Test authentication integration with mcptools function."""

    @pytest.mark.asyncio
    async def test_mcptools_with_api_key_auth(self):
        """Test mcptools with API key authentication."""
        auth_provider = ApiKeyAuthProvider("X-API-Key", "test-key")

        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                async with mcptools(server_params, auth_provider=auth_provider) as (
                    session,
                    tools,
                ):
                    assert session is mock_session
                    assert tools == []

                    # Verify auth provider was used in client setup
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]
                    assert "headers" in call_kwargs
                    assert call_kwargs["headers"]["X-API-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_mcptools_with_bearer_auth(self):
        """Test mcptools with Bearer token authentication."""
        auth_provider = BearerAuthProvider("test-token")

        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                async with mcptools(server_params, auth_provider=auth_provider) as (
                    session,
                    tools,
                ):
                    assert session is mock_session
                    assert tools == []

                    # Verify auth provider was used
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]
                    assert "headers" in call_kwargs
                    assert (
                        call_kwargs["headers"]["Authorization"] == "Bearer test-token"
                    )

    @pytest.mark.asyncio
    async def test_mcptools_oauth_provider(self, mock_oauth_client_provider):
        """Test mcptools with OAuth provider."""
        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                async with mcptools(
                    server_params, auth_provider=mock_oauth_client_provider
                ) as (session, tools):
                    assert session is mock_session
                    assert tools == []

                    # Verify OAuth provider was passed to auth parameter
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]
                    assert call_kwargs["auth"] is mock_oauth_client_provider

    @pytest.mark.asyncio
    async def test_mcptools_sse_transport_with_auth(self):
        """Test mcptools with SSE transport and authentication."""
        auth_provider = ApiKeyAuthProvider("X-API-Key", "sse-key")

        server_params = {"url": "https://example.com/sse", "transport": "sse"}

        with patch("mcpadapt.core.sse_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                async with mcptools(server_params, auth_provider=auth_provider) as (
                    session,
                    tools,
                ):
                    assert session is mock_session

                    # Verify SSE client was used with auth headers
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]
                    assert "headers" in call_kwargs
                    assert call_kwargs["headers"]["X-API-Key"] == "sse-key"


class TestAuthErrorHandling:
    """Test error handling in authentication scenarios."""

    def test_invalid_transport_with_auth(self):
        """Test invalid transport parameter with authentication."""
        # Note: MCPAdapt doesn't validate transport until connection time
        # So this test should verify the auth provider is stored correctly even with invalid transport
        auth_provider = ApiKeyAuthProvider("X-API-Key", "key")

        server_params = {
            "url": "https://example.com/mcp",
            "transport": "invalid-transport",
        }

        # MCPAdapt should accept any transport type - validation happens later
        with patch("mcpadapt.core.streamablehttp_client"):
            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            # Verify auth provider is stored correctly
            assert adapter.auth_providers[0] is auth_provider

    @pytest.mark.asyncio
    async def test_auth_provider_header_merge(self):
        """Test that auth headers are properly merged with existing headers."""
        auth_provider = ApiKeyAuthProvider("X-API-Key", "merge-test")

        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
            "headers": {"User-Agent": "TestAgent", "Accept": "application/json"},
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                async with mcptools(server_params, auth_provider=auth_provider) as (
                    session,
                    tools,
                ):
                    # Verify headers were merged correctly
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]

                    expected_headers = {
                        "User-Agent": "TestAgent",
                        "Accept": "application/json",
                        "X-API-Key": "merge-test",
                    }
                    assert call_kwargs["headers"] == expected_headers


class TestAuthProviderEdgeCases:
    """Test edge cases with auth providers."""

    def test_mixed_auth_provider_list(self):
        """Test mixed list of auth providers and None values."""
        api_provider = ApiKeyAuthProvider("X-API-Key", "key1")
        bearer_provider = BearerAuthProvider("token2")

        server_params = [
            {"url": "https://api1.example.com/mcp", "transport": "streamable-http"},
            {"url": "https://api2.example.com/mcp", "transport": "streamable-http"},
            {"url": "https://api3.example.com/mcp", "transport": "streamable-http"},
        ]

        # Mixed auth providers with None
        auth_providers = [api_provider, None, bearer_provider]

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider=auth_providers,
            )

            assert len(adapter.auth_providers) == 3
            assert adapter.auth_providers[0] is api_provider
            assert adapter.auth_providers[1] is None
            assert adapter.auth_providers[2] is bearer_provider

    def test_auth_with_stdio_server(self):
        """Test that auth providers work with stdio servers."""
        from mcp import StdioServerParameters

        auth_provider = ApiKeyAuthProvider("X-API-Key", "stdio-key")

        # For stdio servers, auth should be stored but not used
        with patch("mcpadapt.core.stdio_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            adapter = MCPAdapt(
                serverparams=StdioServerParameters(command="echo", args=["test"]),
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            # Auth provider should be stored even for stdio
            assert adapter.auth_providers[0] is auth_provider


class TestAuthenticationFlowIntegration:
    """Test complete authentication flows with MCPAdapt."""

    @pytest.mark.asyncio
    async def test_complete_oauth_flow_mock(self):
        """Test complete OAuth flow integration (mocked)."""
        # This would be used with a real OAuth provider in practice
        mock_oauth_provider = Mock()
        mock_oauth_provider.get_headers = Mock(
            return_value={"Authorization": "Bearer oauth_token"}
        )

        server_params = {
            "url": "https://oauth.example.com/mcp",
            "transport": "streamable-http",
        }

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()

            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            with patch("mcpadapt.core.ClientSession") as mock_session_class:
                mock_session_class.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_class.return_value.__aexit__ = AsyncMock()

                mock_session.initialize = AsyncMock()
                mock_session.list_tools = AsyncMock()
                mock_session.list_tools.return_value.tools = []

                # Use OAuth provider that looks like an OAuthClientProvider
                async with mcptools(
                    server_params, auth_provider=mock_oauth_provider
                ) as (session, tools):
                    # Since it's not a real OAuthClientProvider, it should be treated as unknown
                    # and passed to the auth parameter
                    mock_client.assert_called_once()
                    call_kwargs = mock_client.call_args[1]
                    assert call_kwargs["auth"] is mock_oauth_provider

    def test_auth_provider_parameter_validation(self):
        """Test auth provider parameter validation."""
        server_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
        }

        # Test with invalid auth provider type
        with patch("mcpadapt.core.streamablehttp_client"):
            # String should not cause error, just be ignored
            adapter = MCPAdapt(
                serverparams=server_params,
                adapter=DummyAdapter(),
                auth_provider="invalid",
            )
            assert adapter.auth_providers[0] == "invalid"

    def test_auth_deep_copy_serverparams(self):
        """Test that serverparams are deep copied when adding auth."""
        original_params = {
            "url": "https://example.com/mcp",
            "transport": "streamable-http",
            "headers": {"Original": "Header"},
        }

        auth_provider = ApiKeyAuthProvider("X-API-Key", "test-key")

        with patch("mcpadapt.core.streamablehttp_client") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=(Mock(), Mock())
            )
            mock_client.return_value.__aexit__ = AsyncMock()

            MCPAdapt(
                serverparams=original_params,
                adapter=DummyAdapter(),
                auth_provider=auth_provider,
            )

            # Original params should be unchanged
            assert "X-API-Key" not in original_params.get("headers", {})
            assert original_params["headers"] == {"Original": "Header"}
