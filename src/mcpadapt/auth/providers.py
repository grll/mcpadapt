"""Authentication provider classes for MCPAdapt."""

from typing import Any
from mcp.client.auth import OAuthClientProvider, TokenStorage
from .handlers import BaseOAuthHandler


class ApiKeyAuthProvider:
    """Simple API key authentication provider."""

    def __init__(self, header_name: str, header_value: str):
        """Initialize with API key configuration.

        Args:
            header_name: Name of the header to send the API key in
            header_value: The API key value
        """
        self.header_name = header_name
        self.header_value = header_value

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.

        Returns:
            Dictionary of headers to add to requests
        """
        return {self.header_name: self.header_value}


class BearerAuthProvider:
    """Simple Bearer token authentication provider."""

    def __init__(self, token: str):
        """Initialize with Bearer token configuration.

        Args:
            token: The bearer token
        """
        self.token = token

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.

        Returns:
            Dictionary of headers to add to requests
        """
        return {"Authorization": f"Bearer {self.token}"}


class OAuthProvider(OAuthClientProvider):
    """OAuth provider that accepts a handler directly.
    
    This class simplifies OAuth configuration by taking an OAuthHandler
    and internally extracting the client metadata and callback handlers.
    """
    
    def __init__(self, server_url: str, oauth_handler: BaseOAuthHandler, storage: TokenStorage):
        """Initialize OAuth provider with handler.
        
        Args:
            server_url: MCP server URL
            oauth_handler: OAuth handler containing all configuration
            storage: Token storage implementation
        """
        super().__init__(
            server_url=server_url,
            client_metadata=oauth_handler.get_client_metadata(),
            storage=storage,
            redirect_handler=oauth_handler.handle_redirect,
            callback_handler=oauth_handler.handle_callback,
        )


def get_auth_headers(auth_provider: Any) -> dict[str, str]:
    """Get authentication headers from provider.

    Args:
        auth_provider: Authentication provider instance

    Returns:
        Dictionary of headers to add to requests
    """
    if isinstance(auth_provider, (ApiKeyAuthProvider, BearerAuthProvider)):
        return auth_provider.get_headers()
    return {}
