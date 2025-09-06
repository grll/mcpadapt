# API Key Authentication

API Key authentication allows you to pass in an API Key as a header to the MCP server for authentication

## Basic Usage

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
    serverparams={"url": "https://api.example.com/mcp", "transport": "streamable-http"},
    adapter=SmolAgentsAdapter(),
    auth_provider=api_key_provider,
) as tools:
    print(f"Connected with {len(tools)} tools")
```

## Custom Header Names

Different APIs use different header names for API keys:

```python
from mcpadapt.auth import ApiKeyAuthProvider

# Common API key header variations
providers = [
    ApiKeyAuthProvider("X-API-Key", "key123"),           # Most common
    ApiKeyAuthProvider("Authorization", "key123"),       # Simple auth header
    ApiKeyAuthProvider("X-Auth-Token", "key123"),        # Auth token variant
    ApiKeyAuthProvider("X-Custom-Auth", "key123"),       # Custom header
]
```

## Environment Variables

Store API keys securely using environment variables:

```python
import os
from mcpadapt.auth import ApiKeyAuthProvider

# Load API key from environment
api_key = os.getenv("MY_API_KEY")
if not api_key:
    raise ValueError("MY_API_KEY environment variable is required")

api_key_provider = ApiKeyAuthProvider(
    header_name="X-API-Key",
    header_value=api_key
)
```

## Multiple APIs with Different Keys

Use different API keys for different MCP servers:

```python
import os
from mcpadapt.auth import ApiKeyAuthProvider
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter

# Different API keys for different services
auth_providers = [
    ApiKeyAuthProvider("X-API-Key", os.getenv("SERVICE_A_KEY")),
    ApiKeyAuthProvider("X-Auth-Token", os.getenv("SERVICE_B_KEY")),
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

## API Key Formats

### Simple API Key

```python
ApiKeyAuthProvider("X-API-Key", "abc123def456")
```

### Prefixed API Key

```python
ApiKeyAuthProvider("X-API-Key", "Bearer abc123def456")
ApiKeyAuthProvider("Authorization", "API-Key abc123def456")
```

### Base64 Encoded Credentials

```python
import base64

credentials = base64.b64encode(b"username:password").decode()
ApiKeyAuthProvider("Authorization", f"Basic {credentials}")
```

## Best Practices

### Security
- Never hard-code API keys in source code
- Use environment variables or secure configuration files
- Rotate API keys regularly
- Use the principle of least privilege for API key permissions

### Configuration
- Use descriptive environment variable names
- Document required API keys in your README
- Provide clear error messages for missing keys
- Validate API key format before using

## Integration Examples

### With Different Frameworks

```python
# SmolAgents
from mcpadapt.smolagents_adapter import SmolAgentsAdapter
adapter = SmolAgentsAdapter()

# CrewAI
from mcpadapt.crewai_adapter import CrewAIAdapter
adapter = CrewAIAdapter()

# LangChain
from mcpadapt.langchain_adapter import LangChainAdapter
adapter = LangChainAdapter()

# All use the same API key provider
api_key_provider = ApiKeyAuthProvider("X-API-Key", os.getenv("API_KEY"))
```
