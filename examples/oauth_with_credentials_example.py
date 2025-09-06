"""Example demonstrating OAuth with pre-configured client credentials.

This example shows how to use your own OAuth client credentials
instead of relying on Dynamic Client Registration (DCR). This is useful when:
- The server doesn't support DCR
- You have a pre-registered OAuth application
- You want to use specific client credentials
"""

import os
from pydantic import HttpUrl

from mcpadapt.auth import (
    InMemoryTokenStorage,
    LocalBrowserOAuthHandler,
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthConfigurationError,
    OAuthClientProvider,
    OAuthClientMetadata,
)
from mcpadapt.core import MCPAdapt
from mcpadapt.smolagents_adapter import SmolAgentsAdapter
from mcp.shared.auth import OAuthClientInformationFull


def main():
    """Main example function demonstrating OAuth with pre-configured credentials."""
    print("OAuth with Pre-configured Credentials Example")
    print("=" * 40)

    # Get credentials from environment variables
    CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "your-client-id")
    CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "your-client-secret")
    REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:3030/callback")

    print(f"Using client ID: {CLIENT_ID}")
    print(f"Using redirect URI: {REDIRECT_URI}")
    print()

    # Create pre-configured client information
    client_info = OAuthClientInformationFull(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uris=[HttpUrl(REDIRECT_URI)],
    )

    # Create OAuth client metadata (still needed for the OAuth flow)
    client_metadata = OAuthClientMetadata(
        client_name="MCPAdapt Pre-configured OAuth Example",
        redirect_uris=[HttpUrl(REDIRECT_URI)],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        token_endpoint_auth_method="client_secret_post",
    )

    # Create OAuth handler
    oauth_handler = LocalBrowserOAuthHandler(callback_port=3030, timeout=300)

    # Create token storage WITH pre-configured client information
    # This is the key difference - we pass the client_info object
    token_storage = InMemoryTokenStorage(client_info=client_info)

    # Create OAuth provider
    oauth_provider = OAuthClientProvider(
        server_url="https://api.example.com",
        client_metadata=client_metadata,
        storage=token_storage,  # Storage contains pre-configured credentials
        redirect_handler=oauth_handler.handle_redirect,
        callback_handler=oauth_handler.handle_callback,
    )

    # Server configuration
    server_config = {
        "url": "https://api.example.com/mcp",
        "transport": "streamable-http",
    }

    print("Connecting with pre-configured OAuth credentials...")
    print("This will skip Dynamic Client Registration and use your credentials")
    print("This will open your browser for OAuth authorization")
    print()

    try:
        # Connect to MCP server with pre-configured OAuth credentials
        with MCPAdapt(
            serverparams=server_config,
            adapter=SmolAgentsAdapter(),
            auth_provider=oauth_provider,
        ) as tools:
            print("Successfully connected with pre-configured credentials!")
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
        print("You need to authorize the application to access the service.")
    except OAuthNetworkError as e:
        print(f"Network error during OAuth: {e}")
        print("Check your internet connection and try again.")
    except OAuthConfigurationError as e:
        print(f"OAuth configuration error: {e}")
        print("Please check your OAuth settings and credentials.")
    except Exception as e:
        print(f"Failed to connect: {e}")


if __name__ == "__main__":
    print("Set environment variables for your OAuth credentials:")
    print("export OAUTH_CLIENT_ID='your-client-id'")
    print("export OAUTH_CLIENT_SECRET='your-client-secret'")
    print("export OAUTH_REDIRECT_URI='http://localhost:3030/callback'")
    print()

    try:
        main()
    except KeyboardInterrupt:
        print("\nExample cancelled by user")
    except Exception as e:
        print(f"Example failed: {e}")
