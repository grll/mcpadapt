# Creating Custom Handlers

Custom OAuth handlers allow you to implement specialized authentication flows that are specific to how your application handles OAuth Redirects.

## BaseOAuthHandler Interface

All custom OAuth handlers must extend the `BaseOAuthHandler` abstract class and implement the required methods:

```python
from mcpadapt.auth import BaseOAuthHandler, OAuthClientMetadata
from typing import List
from pydantic import AnyUrl

class CustomOAuthHandler(BaseOAuthHandler):
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Return redirect URIs that this handler can process."""
        return [AnyUrl("http://localhost:8080/callback")]
    
    async def handle_redirect(self, authorization_url: str) -> None:
        """Handle OAuth redirect to authorization URL."""
        # Your custom redirect logic here
        pass
    
    async def handle_callback(self) -> tuple[str, str | None]:
        """Handle OAuth callback and return authorization code and state."""
        # Your custom callback logic here
        return authorization_code, state
```

## Headless Environment Handler

For server environments without a browser:

```python
from mcpadapt.auth import BaseOAuthHandler, OAuthClientMetadata
from typing import List
from pydantic import AnyUrl

class HeadlessOAuthHandler(BaseOAuthHandler):
    """OAuth handler for headless environments."""
    
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Return out-of-band redirect for headless environments."""
        return [AnyUrl("urn:ietf:wg:oauth:2.0:oob")]
    
    async def handle_redirect(self, authorization_url: str) -> None:
        print(f"Please open this URL in your browser:")
        print(f"{authorization_url}")
        print()
    
    async def handle_callback(self) -> tuple[str, str | None]:
        auth_code = input("Enter the authorization code from the callback URL: ")
        state = input("Enter the state parameter (or press Enter to skip): ").strip()
        return auth_code, state or None
```

## Custom Callback Handler

For applications with existing web servers:

```python
from mcpadapt.auth import BaseOAuthHandler, OAuthClientMetadata
from typing import List
from pydantic import AnyUrl
import asyncio

class CustomCallbackHandler(BaseOAuthHandler):
    """OAuth handler that integrates with existing web application."""
    
    def __init__(self, client_metadata: OAuthClientMetadata, callback_url: str):
        super().__init__(client_metadata)
        self.callback_url = callback_url
        self.callback_data = {}
        self.callback_received = asyncio.Event()
    
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Return custom callback URL."""
        return [AnyUrl(self.callback_url)]
    
    async def handle_redirect(self, authorization_url: str) -> None:
        # In a real app, you might redirect the user's current request
        print(f"Redirecting to: {authorization_url}")
        # Your web framework's redirect logic here
    
    async def handle_callback(self) -> tuple[str, str | None]:
        # Wait for callback to be received by your web server
        await self.callback_received.wait()
        
        auth_code = self.callback_data.get('code')
        state = self.callback_data.get('state')
        
        if not auth_code:
            raise ValueError("No authorization code received")
        
        return auth_code, state
    
    def receive_callback(self, code: str, state: str | None = None):
        """Call this method from your web server's callback endpoint."""
        self.callback_data = {'code': code, 'state': state}
        self.callback_received.set()
```

## CLI Integration Handler

For command-line applications:

```python
from mcpadapt.auth import BaseOAuthHandler, OAuthClientMetadata
from typing import List
from pydantic import AnyUrl
import webbrowser
import urllib.parse

class CLIHandler(BaseOAuthHandler):
    """OAuth handler optimized for CLI applications."""
    
    def __init__(self, client_metadata: OAuthClientMetadata, callback_port: int = 3030, auto_open_browser: bool = True):
        super().__init__(client_metadata)
        self.callback_port = callback_port
        self.auto_open_browser = auto_open_browser
    
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Return localhost callback URL."""
        return [AnyUrl(f"http://localhost:{self.callback_port}/callback")]
    
    async def handle_redirect(self, authorization_url: str) -> None:
        if self.auto_open_browser:
            try:
                webbrowser.open(authorization_url)
                print("Opening browser for authentication...")
            except Exception:
                print("Could not open browser automatically.")
                print(f"Please open: {authorization_url}")
        else:
            print(f"Please open: {authorization_url}")
    
    async def handle_callback(self) -> tuple[str, str | None]:
        print()
        print("After authorizing, copy the full callback URL from your browser.")
        callback_url = input("Callback URL: ").strip()
        
        # Parse the callback URL to extract code and state
        parsed = urllib.parse.urlparse(callback_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        if 'code' not in query_params:
            raise ValueError("No authorization code found in callback URL")
        
        auth_code = query_params['code'][0]
        state = query_params.get('state', [None])[0]
        
        return auth_code, state
```

## Using Custom Handlers

```python
from mcpadapt.auth import OAuthProvider, OAuthClientMetadata, InMemoryTokenStorage
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Create client metadata
client_metadata = OAuthClientMetadata(
    client_name="My Application",
    grant_types=["authorization_code", "refresh_token"],
    response_types=["code"],
    token_endpoint_auth_method="client_secret_post",
)

# Use your custom handler with the new interface
custom_handler = HeadlessOAuthHandler(client_metadata)

oauth_provider = OAuthProvider(
    server_url="https://oauth-server.com",
    oauth_handler=custom_handler,
    storage=InMemoryTokenStorage(),
)

with MCPAdapt(
    serverparams={"url": "https://oauth-server.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=oauth_provider,
) as tools:
    print(f"Connected with custom handler: {len(tools)} tools")
```
