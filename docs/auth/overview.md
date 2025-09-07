# Authentication Overview

MCPAdapt builds upon the offical MCP python SDK and provides authentication support for connecting to secure MCP servers that require access control, rate limiting, or premium features.

## Supported Authentication Methods

### OAuth 2.0
Secure authorization code flow with automatic token refresh. Best for production applications and user-facing services requiring consent.

### API Key
Header-based authentication using API keys. Ideal for server-to-server communication and development environments.

### Bearer Token
Standard Bearer token authentication for JWT-based systems and modern API patterns.

## Core Components

**Authentication Providers:**
- `OAuthProvider` - OAuth 2.0 authentication 
- `ApiKeyAuthProvider` - API key authentication  
- `BearerAuthProvider` - Bearer token authentication

**OAuth Handlers:**
- `LocalBrowserOAuthHandler` - Browser-based OAuth flow
- `BaseOAuthHandler` - Base class for custom implementations

**Token Storage:**
- `InMemoryTokenStorage` - In-memory token storage
- `TokenStorage` - Base class for custom implementations

**Error Handling:**
- `OAuthTimeoutError` - Authentication timeout
- `OAuthCancellationError` - User cancelled authorization
- `OAuthNetworkError` - Network issues
- `OAuthConfigurationError` - Configuration problems
- `OAuthServerError` - Server-side errors
- `OAuthCallbackError` - Callback handling issues

## Basic Usage

Authentication integrates transparently into MCPAdapt:

```python
with MCPAdapt(
    serverparams=server_config,
    adapter=YourAdapter(),
    auth_provider=your_auth_provider,
) as tools:
    # Authentication handled automatically
    result = tools[0]({"param": "value"})
```
