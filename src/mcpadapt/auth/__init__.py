"""Authentication module for MCPAdapt."""

from .handlers import default_callback_handler, default_redirect_handler
from .oauth import InMemoryTokenStorage
from .providers import (
    ApiKeyAuthProvider,
    BearerAuthProvider,
    create_auth_provider,
    get_auth_headers,
)
from .models import (
    ApiKeyConfig,
    AuthConfig,
    AuthConfigBase,
    BearerAuthConfig,
    CallbackHandler,
    OAuthConfig,
    RedirectHandler,
)

__all__ = [
    # Types
    "AuthConfig",
    "AuthConfigBase",
    "OAuthConfig",
    "ApiKeyConfig",
    "BearerAuthConfig",
    "CallbackHandler",
    "RedirectHandler",
    # OAuth utilities
    "InMemoryTokenStorage",
    # Handlers
    "default_callback_handler",
    "default_redirect_handler",
    # Providers
    "ApiKeyAuthProvider",
    "BearerAuthProvider",
    "create_auth_provider",
    "get_auth_headers",
]
