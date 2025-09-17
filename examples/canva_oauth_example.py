"""Example demonstrating OAuth authentication with Canva MCP server.

This example shows how to connect to the Canva MCP server (https://mcp.canva.com/mcp)
using OAuth authentication through MCPAdapt.

The Canva MCP server provides tools for creating and managing Canva designs.
It fully complies with OAuth 2.0 Dynamic Client Registration
"""

from mcpadapt.auth import (
    InMemoryTokenStorage,
    LocalBrowserOAuthHandler,
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthConfigurationError,
    OAuthProvider,
    OAuthClientMetadata,
)
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter


def main():
    """Main example function demonstrating Canva OAuth connection."""
    print("Canva MCP OAuth Example")
    print("=" * 40)

    # Create OAuth client metadata
    client_metadata = OAuthClientMetadata(
        client_name="MCPAdapt Canva Example",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
    )

    # Create OAuth handler and token storage
    oauth_handler = LocalBrowserOAuthHandler(
        client_metadata=client_metadata, callback_port=3030, timeout=300
    )
    token_storage = InMemoryTokenStorage()

    # Create OAuth provider
    oauth_provider = OAuthProvider(
        server_url="https://mcp.canva.com",
        oauth_handler=oauth_handler,
        storage=token_storage,
    )

    # Server configuration for Canva MCP
    server_config = {
        "url": "https://mcp.canva.com/mcp",
        "transport": "streamable-http",
    }

    print("Connecting to Canva MCP server with OAuth...")
    print("This will open your browser for OAuth authorization")
    print()

    try:
        # Connect to Canva MCP server with OAuth authentication (sync)
        with MCPAdapt(
            serverparams=server_config,
            adapter=SmolAgentsAdapter(),
            auth_provider=oauth_provider,
        ) as tools:
            print("Successfully connected to Canva MCP server!")
            print(f"Found {len(tools)} available tools:")
            print()

            # List available tools
            for i, tool in enumerate(tools, 1):
                print(f"{i}. {tool.name}")
                if hasattr(tool, "description") and tool.description:
                    print(f"   Description: {tool.description}")
                print()

            print("Connection successful! Tools are ready to use.")

    except OAuthTimeoutError as e:
        print(f"OAuth authentication timed out: {e}")
        print("Try again and complete the authorization in your browser quickly.")
    except OAuthCancellationError as e:
        print(f"OAuth authorization was cancelled: {e}")
        print("You need to authorize the application to access Canva.")
    except OAuthNetworkError as e:
        print(f"Network error during OAuth: {e}")
        print("Check your internet connection and try again.")
    except OAuthConfigurationError as e:
        print(f"OAuth configuration error: {e}")
        print("Please check your OAuth settings.")
    except Exception as e:
        print(f"Failed to connect to Canva MCP server: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExample cancelled by user")
    except Exception as e:
        print(f"Example failed: {e}")
