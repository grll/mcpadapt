"""Authentication provider classes for MCPAdapt."""

from typing import Any, Callable, Generator, Union
import httpx
from mcp.client.auth import OAuthClientProvider, TokenStorage
from .handlers import BaseOAuthHandler


class ApiKeyAuthProvider(httpx.Auth):
    """Simple API key authentication provider."""

    def __init__(self, header_name: str, header_value: str):
        """Initialize with API key configuration.

        Args:
            header_name: Name of the header to send the API key in
            header_value: The API key value
        """
        self.header_name = header_name
        self.header_value = header_value

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Execute the authentication flow by adding the API key header.

        Args:
            request: The request to authenticate

        Yields:
            The authenticated request
        """
        request.headers[self.header_name] = self.header_value
        yield request



class BearerAuthProvider(httpx.Auth):
    """Simple Bearer token authentication provider.
    
    Supports both static tokens (strings) and dynamic tokens (callables that return strings).
    """

    def __init__(self, token: Union[str, Callable[[], str]]):
        """Initialize with Bearer token configuration.

        Args:
            token: The bearer token (string) or a callable that returns the token
        """
        self._token = token

    def _get_token_value(self) -> str:
        """Get the current token value.
        
        Returns:
            The token value, calling the token if it's callable
        """
        return self._token() if callable(self._token) else self._token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        """Execute the authentication flow by adding the Bearer token header.

        Args:
            request: The request to authenticate

        Yields:
            The authenticated request
        """
        token_value = self._get_token_value()
        request.headers["Authorization"] = f"Bearer {token_value}"
        yield request



class OAuthProvider(OAuthClientProvider):
    """OAuth provider that accepts a handler directly.

    This class simplifies OAuth configuration by taking an OAuthHandler
    and internally extracting the client metadata and callback handlers.
    """

    def __init__(
        self, server_url: str, oauth_handler: BaseOAuthHandler, storage: TokenStorage
    ):
        """Initialize OAuth provider with handler.

        Args:
            server_url: MCP server URL
            oauth_handler: OAuth handler containing all configuration
            storage: Token storage implementation
        """
        super().__init__(
            server_url=server_url,
            client_metadata=oauth_handler.get_client_metadata(),
            storage=storage,
            redirect_handler=oauth_handler.handle_redirect,
            callback_handler=oauth_handler.handle_callback,
        )
