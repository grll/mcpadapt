"""Authentication module for MCPAdapt.

This module provides OAuth, API Key, and Bearer token authentication support
for MCP servers.

Example usage with OAuth:

```python
from mcp.client.auth import OAuthClientProvider
from mcp.shared.auth import OAuthClientMetadata
from pydantic import HttpUrl

from mcpadapt.auth import (
    InMemoryTokenStorage, 
    LocalBrowserOAuthHandler
)
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Create OAuth provider directly
client_metadata = OAuthClientMetadata(
    client_name="My App",
    redirect_uris=[HttpUrl("http://localhost:3030/callback")],
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
)

oauth_handler = LocalBrowserOAuthHandler(callback_port=3030)
token_storage = InMemoryTokenStorage()

oauth_provider = OAuthClientProvider(
    server_url="https://example.com",
    client_metadata=client_metadata,
    storage=token_storage,
    redirect_handler=oauth_handler.handle_redirect,
    callback_handler=oauth_handler.handle_callback,
)

# Use with MCPAdapt
with MCPAdapt(
    serverparams={"url": "https://example.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=oauth_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

Example usage with API Key:

```python
from mcpadapt.auth import ApiKeyAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Create API Key provider
api_key_provider = ApiKeyAuthProvider(
    header_name="X-API-Key",
    header_value="your-api-key-here"
)

with MCPAdapt(
    serverparams={"url": "https://example.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=api_key_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

For custom implementations, extend BaseOAuthHandler:

```python
from mcpadapt.auth import BaseOAuthHandler

class CustomOAuthHandler(BaseOAuthHandler):
    async def handle_redirect(self, authorization_url: str) -> None:
        # Custom redirect logic (e.g., print URL for headless environments)
        print(f"Please open: {authorization_url}")
    
    async def handle_callback(self) -> tuple[str, str | None]:
        # Custom callback logic (e.g., manual code input)
        auth_code = input("Enter authorization code: ")
        return auth_code, None
```
"""

from .oauth import InMemoryTokenStorage
from .handlers import (
    BaseOAuthHandler,
    LocalBrowserOAuthHandler,
    LocalCallbackServer,
)
from .providers import (
    ApiKeyAuthProvider,
    BearerAuthProvider,
    get_auth_headers,
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
    # Default implementations
    "InMemoryTokenStorage",
    # Provider functions
    "get_auth_headers",
    # Exception classes
    "OAuthError",
    "OAuthTimeoutError",
    "OAuthCancellationError",
    "OAuthNetworkError",
    "OAuthConfigurationError",
    "OAuthServerError",
    "OAuthCallbackError",
]
