# Quick Start Guide

Get authentication working quickly with these minimal examples.

## OAuth 2.0 with a provider like Canva

```python
from mcpadapt.auth import (
    OAuthProvider,
    OAuthClientMetadata,
    InMemoryTokenStorage,
    LocalBrowserOAuthHandler,
)
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Configure OAuth (no need to specify redirect_uris - handled automatically)
client_metadata = OAuthClientMetadata(
    client_name="My App",
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
)

# Create OAuth handler with metadata
oauth_handler = LocalBrowserOAuthHandler(
    client_metadata=client_metadata,
    callback_port=3030,
    timeout=300
)

token_storage = InMemoryTokenStorage()

# Create simplified OAuth provider
oauth_provider = OAuthProvider(
    server_url="https://mcp.canva.com",
    oauth_handler=oauth_handler,
    storage=token_storage,
)

# Use with MCPAdapt
with MCPAdapt(
    serverparams={"url": "https://mcp.canva.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=oauth_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

## API Key Authentication

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

## Bearer Token Authentication

```python
from mcpadapt.auth import BearerAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Create Bearer token provider
bearer_provider = BearerAuthProvider(token="your-bearer-token")

with MCPAdapt(
    serverparams={"url": "https://example.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=bearer_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

## Multiple Servers with Different Authentication

```python
from mcpadapt.auth import ApiKeyAuthProvider, BearerAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Different auth for each server
auth_providers = [
    ApiKeyAuthProvider("X-API-Key", "key1"),
    BearerAuthProvider("token2"),
    None,  # No auth for third server
]

server_configs = [
    {"url": "https://api1.com/mcp", "transport": "streamable-http"},
    {"url": "https://api2.com/mcp", "transport": "streamable-http"},
    {"url": "http://localhost:8000/sse"},
]

with MCPAdapt(
    serverparams=server_configs,
    adapter=SmolAgentsAdapter(),
    auth_provider=auth_providers,
) as tools:
    print(f"Connected to {len(server_configs)} servers with {len(tools)} total tools")
```

## Error Handling

```python
from mcpadapt.auth import (
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
)

try:
    with MCPAdapt(
        serverparams=server_config,
        adapter=SmolAgentsAdapter(),
        auth_provider=oauth_provider,
    ) as tools:
        # Use tools
        pass
except OAuthTimeoutError:
    print("Authentication timed out - try again")
except OAuthCancellationError:
    print("User cancelled authorization")
except OAuthNetworkError as e:
    print(f"Network error: {e}")
```
