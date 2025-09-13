"""Authentication module for MCPAdapt.

This module provides OAuth, API Key, and Bearer token authentication support
for MCP servers.
"""

from .oauth import InMemoryTokenStorage, OAuthClientMetadata
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthToken,
    InvalidScopeError,
    OAuthClientMetadata as MCPOAuthClientMetadata,
    InvalidRedirectUriError,
    OAuthMetadata,
    ProtectedResourceMetadata,
)
from mcp.client.auth import TokenStorage, OAuthClientProvider
from .handlers import (
    BaseOAuthHandler,
    LocalBrowserOAuthHandler,
    LocalCallbackServer,
)
from .providers import (
    ApiKeyAuthProvider,
    BearerAuthProvider,
    OAuthProvider,
)
from .exceptions import (
    OAuthError,
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthConfigurationError,
    OAuthServerError,
    OAuthCallbackError,
)

__all__ = [
    # Handler classes
    "BaseOAuthHandler",
    "LocalBrowserOAuthHandler",
    "LocalCallbackServer",
    # Provider classes
    "ApiKeyAuthProvider",
    "BearerAuthProvider",
    "OAuthProvider",
    # Default implementations
    "InMemoryTokenStorage",
    # Exception classes
    "OAuthError",
    "OAuthTimeoutError",
    "OAuthCancellationError",
    "OAuthNetworkError",
    "OAuthConfigurationError",
    "OAuthServerError",
    "OAuthCallbackError",
    # Re-exported classes from mcp.client.auth
    "TokenStorage",
    "OAuthClientProvider",
    # Re-exported classes from mcp.shared.auth
    "OAuthClientInformationFull",
    "OAuthToken",
    "InvalidScopeError",
    "InvalidRedirectUriError",
    "OAuthMetadata",
    "ProtectedResourceMetadata",
    # Our OAuth classes
    "OAuthClientMetadata",
    "MCPOAuthClientMetadata",
]
