"""Authentication utilities for pre-authenticating providers."""

from typing import Any

from mcp.client.auth import OAuthClientProvider

from .providers import ApiKeyAuthProvider, BearerAuthProvider, create_auth_provider
from .models import AuthConfig, OAuthConfig


async def authenticate(
    auth_config: AuthConfig, 
    server_url: str
) -> OAuthClientProvider | ApiKeyAuthProvider | BearerAuthProvider:
    """
    Create and prepare an auth provider for use with MCPAdapt.
    
    For OAuth: Creates a configured OAuth provider that will perform the OAuth flow
               (browser redirect, callback, token exchange) when first used by MCPAdapt
    For API Key/Bearer: Creates a ready-to-use provider (no additional flow needed)
    
    Args:
        auth_config: Authentication configuration
        server_url: Server URL (needed for OAuth server endpoint discovery)
        
    Returns:
        Auth provider ready to use with MCPAdapt
        
    Example:
        >>> # Prepare OAuth provider
        >>> oauth_config = OAuthConfig(client_metadata={...})
        >>> auth_provider = await authenticate(oauth_config, "https://mcp.canva.com/mcp")
        >>> 
        >>> # Use with MCPAdapt - OAuth flow will happen during connection
        >>> with MCPAdapt(server_config, adapter, auth_provider=auth_provider) as tools:
        >>>     print(tools)
        
    Note:
        For OAuth, the actual authentication flow (browser redirect, token exchange) 
        occurs when MCPAdapt makes its first connection to the MCP server. This function
        prepares the OAuth provider with all necessary configuration.
    """
    return await create_auth_provider(auth_config, server_url)
