# Bearer Token Authentication

Bearer token authentication uses standard Authorization headers with Bearer tokens for MCP server authentication.

## Basic Usage

```python
from mcpadapt.auth import BearerAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Create Bearer token provider
bearer_provider = BearerAuthProvider(token="your-bearer-token")

with MCPAdapt(
    serverparams={"url": "https://api.example.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=bearer_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

## JWT Tokens

Bearer tokens are commonly used with JWT (JSON Web Tokens):

```python
from mcpadapt.auth import BearerAuthProvider

# JWT token example
jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
bearer_provider = BearerAuthProvider(token=jwt_token)
```

## Environment Variables

Store bearer tokens securely:

```python
import os
from mcpadapt.auth import BearerAuthProvider

# Load token from environment
bearer_token = os.getenv("BEARER_TOKEN")
if not bearer_token:
    raise ValueError("BEARER_TOKEN environment variable is required")

bearer_provider = BearerAuthProvider(token=bearer_token)
```

## Multiple Services

Use different bearer tokens for different MCP servers:

```python
import os
from mcpadapt.auth import BearerAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Different tokens for different services
auth_providers = [
    BearerAuthProvider(os.getenv("SERVICE_A_TOKEN")),
    BearerAuthProvider(os.getenv("SERVICE_B_TOKEN")),
    None,  # No authentication for third service
]

server_configs = [
    {"url": "https://service-a.com/mcp", "transport": "streamable-http"},
    {"url": "https://service-b.com/mcp", "transport": "streamable-http"},
    {"url": "http://localhost:8000/sse"},
]

with MCPAdapt(
    serverparams=server_configs,
    adapter=SmolAgentsAdapter(),
    auth_provider=auth_providers,
) as tools:
    print(f"Connected to {len(server_configs)} servers")
```

## Token Formats

Bearer tokens can have different formats:

```python
from mcpadapt.auth import BearerAuthProvider

# Standard JWT
BearerAuthProvider("eyJhbGciOiJIUzI1NiIs...")

# Simple token
BearerAuthProvider("abc123def456ghi789")

# API-specific format
BearerAuthProvider("sk-1234567890abcdef")
```

## Best Practices

### Security
- Never hard-code bearer tokens in source code
- Use environment variables or secure configuration management
- Implement token rotation when possible
- Monitor token expiration and refresh as needed

### Configuration
- Use descriptive environment variable names
- Validate token format before using
- Handle token expiration gracefully
- Log authentication failures for debugging

## Integration Examples

### With Different Frameworks

```python
from mcpadapt.auth import BearerAuthProvider
import os

# Same bearer provider works with all frameworks
bearer_provider = BearerAuthProvider(os.getenv("BEARER_TOKEN"))

# SmolAgents
from mcpadapt.smolagents_adapter import SmolAgentsAdapter
adapter = SmolAgentsAdapter()

# CrewAI
from mcpadapt.crewai_adapter import CrewAIAdapter
adapter = CrewAIAdapter()

# LangChain
from mcpadapt.langchain_adapter import LangChainAdapter
adapter = LangChainAdapter()
```
