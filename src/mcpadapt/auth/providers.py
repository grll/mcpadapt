"""Authentication provider factory and integration logic."""

from typing import Any
from urllib.parse import urlparse

from mcp.client.auth import OAuthClientProvider

from .handlers import default_callback_handler, default_redirect_handler
from .oauth import InMemoryTokenStorage
from .models import ApiKeyConfig, AuthConfig, BearerAuthConfig, OAuthConfig


class ApiKeyAuthProvider:
    """Simple API key authentication provider."""

    def __init__(self, config: ApiKeyConfig):
        """Initialize with API key configuration.
        
        Args:
            config: API key configuration
        """
        self.config = config

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.
        
        Returns:
            Dictionary of headers to add to requests
        """
        return {self.config.header_name: self.config.header_value}


class BearerAuthProvider:
    """Simple Bearer token authentication provider."""

    def __init__(self, config: BearerAuthConfig):
        """Initialize with Bearer token configuration.
        
        Args:
            config: Bearer token configuration
        """
        self.config = config

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.
        
        Returns:
            Dictionary of headers to add to requests
        """
        return {"Authorization": f"Bearer {self.config.token}"}


async def create_auth_provider(
    auth_config: AuthConfig, server_url: str
) -> OAuthClientProvider | ApiKeyAuthProvider | BearerAuthProvider:
    """Factory function to create appropriate auth provider from config.
    
    Args:
        auth_config: Authentication configuration
        server_url: Server URL for OAuth (needed to determine OAuth server endpoint)
        
    Returns:
        Appropriate auth provider instance
        
    Raises:
        ValueError: If auth configuration type is not supported
    """
    if isinstance(auth_config, OAuthConfig):
        # Use provided handlers or default ones
        callback_handler = auth_config.callback_handler or default_callback_handler
        redirect_handler = auth_config.redirect_handler or default_redirect_handler
        
        # Create OAuth provider with domain root only
        parsed_url = urlparse(server_url)
        oauth_server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        return OAuthClientProvider(
            server_url=oauth_server_url,
            client_metadata=auth_config.client_metadata,
            storage=InMemoryTokenStorage(),
            redirect_handler=redirect_handler,
            callback_handler=callback_handler,
        )
    
    elif isinstance(auth_config, ApiKeyConfig):
        return ApiKeyAuthProvider(auth_config)
    
    elif isinstance(auth_config, BearerAuthConfig):
        return BearerAuthProvider(auth_config)
    
    else:
        raise ValueError(f"Unsupported auth configuration type: {type(auth_config)}")


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
