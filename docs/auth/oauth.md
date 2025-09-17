# OAuth 2.0 Authentication

OAuth 2.0 provides secure authorization for MCP servers requiring user consent. MCPAdapt implements the authorization code flow with automatic token refresh.

## How OAuth Works with MCPAdapt

The built in provider helps you perform the following sequence:

1. **Dynamic Client Registration**: Register your application with the OAuth server (if supported)
    - If your OAuth Server does not support Dynamic Client Registration, be sure to populate the client credentials manually
2. **Authorization Flow**: User authorizes your application in their browser
3. **Token Exchange**: Exchange authorization code for access tokens
4. **Automatic Refresh**: Tokens are refreshed automatically when needed

## Basic OAuth Setup

```python
from mcpadapt.auth import (
    OAuthProvider,
    OAuthClientMetadata,
    InMemoryTokenStorage,
    LocalBrowserOAuthHandler,
)
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Configure client metadata (no need to specify redirect_uris - handled automatically)
client_metadata = OAuthClientMetadata(
    client_name="My Application",
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

# Set up token storage
token_storage = InMemoryTokenStorage()

# Create simplified OAuth provider
oauth_provider = OAuthProvider(
    server_url="https://oauth-server.com",
    oauth_handler=oauth_handler,
    storage=token_storage,
)

# Use with MCPAdapt
with MCPAdapt(
    serverparams={"url": "https://oauth-server.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=oauth_provider,
) as tools:
    # OAuth flow happens automatically
    print(f"Authenticated with {len(tools)} tools")
```

## OAuth Components

### OAuthClientMetadata

Configure your application's OAuth settings

```python
from pydantic import HttpUrl
from mcpadapt.auth import OAuthClientMetadata

client_metadata = OAuthClientMetadata(
    client_name="Your App Name",
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
    # Optional fields:
    client_uri=HttpUrl("https://yourapp.com"),
    tos_uri=HttpUrl("https://yourapp.com/terms"),
    policy_uri=HttpUrl("https://yourapp.com/privacy"),
)
```

### LocalBrowserOAuthHandler

Handles the OAuth flow using the user's browser (now requires client metadata):

```python
from mcpadapt.auth import LocalBrowserOAuthHandler, OAuthClientMetadata

# Create client metadata first
client_metadata = OAuthClientMetadata(
    client_name="Your App Name",
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
)

# Default configuration
oauth_handler = LocalBrowserOAuthHandler(client_metadata)

# Custom configuration
oauth_handler = LocalBrowserOAuthHandler(
    client_metadata,
    callback_port=8080,  # Custom port
    timeout=600,         # 10 minute timeout
)
```

### InMemoryTokenStorage

Simple token storage for development and testing:

```python
from mcpadapt.auth import InMemoryTokenStorage

token_storage = InMemoryTokenStorage()
```

## Using Pre-configured OAuth Credentials

When the OAuth server doesn't support Dynamic Client Registration (DCR), or when you have existing OAuth application credentials, you can pre-configure the token storage with your client information to skip the registration step.

### Basic Pre-configured Setup

```python
import os
from pydantic import HttpUrl
from mcp.shared.auth import OAuthClientInformationFull

from mcpadapt.auth import (
    OAuthProvider,
    OAuthClientMetadata,
    InMemoryTokenStorage,
    LocalBrowserOAuthHandler,
)

# Get your OAuth app credentials (from environment variables or secure storage)
CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:3030/callback"

# Create pre-configured client information
client_info = OAuthClientInformationFull(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uris=[HttpUrl(REDIRECT_URI)]
)

# Create token storage with pre-configured credentials
token_storage = InMemoryTokenStorage(client_info=client_info)

# Configure client metadata (still needed for OAuth flow)
client_metadata = OAuthClientMetadata(
    client_name="My Pre-configured App",
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

# Create simplified OAuth provider
oauth_provider = OAuthProvider(
    server_url="https://oauth-server.com",
    oauth_handler=oauth_handler,
    storage=token_storage,  # Contains pre-configured credentials
)

# Use with MCPAdapt - DCR will be skipped
with MCPAdapt(
    serverparams={"url": "https://oauth-server.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=oauth_provider,
) as tools:
    print(f"Authenticated with pre-configured credentials: {len(tools)} tools")
```

### When to Use Pre-configured Credentials

Use pre-configured credentials when:

- **Server doesn't support DCR**: Some OAuth servers don't implement Dynamic Client Registration
- **Existing OAuth app**: You already have a registered OAuth application with client credentials
- **Compliance requirements**: Your organization requires using specific pre-registered applications

### Complete Example

See `examples/oauth_with_credentials_example.py` for a complete working example of using pre-configured OAuth credentials.

## Custom OAuth Handlers

Create custom OAuth handlers for production environments or when you are integrating into a larger app:

```python
from mcpadapt.auth import BaseOAuthHandler, OAuthProvider, OAuthClientMetadata
from typing import List
from pydantic import HttpUrl

class CustomOAuthHandler(BaseOAuthHandler):
    """Custom OAuth handler with different callback port."""
    
    def __init__(self, client_metadata: OAuthClientMetadata, callback_port: int = 8080):
        super().__init__(client_metadata)
        self.callback_port = callback_port
    
    def get_redirect_uris(self) -> List[HttpUrl]:
        """Return redirect URIs for this handler."""
        return [HttpUrl(f"http://localhost:{self.callback_port}/oauth/callback")]
    
    async def handle_redirect(self, authorization_url: str) -> None:
        print(f"Please open this URL in your browser: {authorization_url}")
        # Custom logging or integration logic here
    
    async def handle_callback(self) -> tuple[str, str | None]:
        # Custom callback handling logic
        print("Waiting for OAuth callback...")
        # In a real implementation, you'd set up your own server or integration
        auth_code = input("Enter the authorization code from the callback: ")
        return auth_code, None

# Create client metadata
client_metadata = OAuthClientMetadata(
    client_name="Custom OAuth App",
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
)

# Use custom handler with the new interface
custom_handler = CustomOAuthHandler(client_metadata, callback_port=8080)
oauth_provider = OAuthProvider(
    server_url="https://oauth-server.com",
    oauth_handler=custom_handler,
    storage=token_storage,
)
```

## Token Storage Options

### In-Memory Storage (Development)

```python
from mcpadapt.auth import InMemoryTokenStorage

# Simple in-memory storage - tokens lost when application exits
storage = InMemoryTokenStorage()
```

### Custom Persistent Storage

```python
from mcpadapt.auth import TokenStorage, OAuthClientInformationFull, OAuthToken
import json

class FileTokenStorage(TokenStorage):
    """File-based token storage."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    async def get_tokens(self) -> OAuthToken | None:
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                return OAuthToken(**data['tokens'])
        except FileNotFoundError:
            return None
    
    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = {'tokens': tokens.model_dump()}
        with open(self.filepath, 'w') as f:
            json.dump(data, f)
    
    async def get_client_info(self) -> OAuthClientInformationFull | None:
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                return OAuthClientInformationFull(**data['client_info'])
        except (FileNotFoundError, KeyError):
            return None
    
    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        
        data['client_info'] = client_info.model_dump()
        with open(self.filepath, 'w') as f:
            json.dump(data, f)

# Use custom storage
storage = FileTokenStorage("oauth_tokens.json")
```

## Error Handling

Handle OAuth-specific errors gracefully:

```python
from mcpadapt.auth import (
    OAuthError,
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthConfigurationError,
    OAuthServerError,
)

try:
    with MCPAdapt(
        serverparams=server_config,
        adapter=adapter,
        auth_provider=oauth_provider,
    ) as tools:
        # Use tools
        pass

except OAuthTimeoutError as e:
    print(f"Authentication timed out after {e.timeout_seconds} seconds")
    
except OAuthCancellationError as e:
    print(f"User cancelled authorization: {e.error_details}")
    
except OAuthNetworkError as e:
    print(f"Network error during OAuth: {e.original_error}")
    
except OAuthConfigurationError as e:
    print(f"OAuth configuration error: {e.config_issue}")
    
except OAuthServerError as e:
    print(f"OAuth server error: {e.server_error}")
    if e.error_description:
        print(f"Description: {e.error_description}")
        
except OAuthError as e:
    print(f"General OAuth error: {e}")
    if e.context:
        print(f"Context: {e.context}")
```