"""OAuth token storage and utility implementations."""

from mcp.client.auth import TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class InMemoryTokenStorage(TokenStorage):
    """Simple in-memory token storage implementation."""

    def __init__(self, client_info: OAuthClientInformationFull | None = None):
        """Initialize token storage, optionally with pre-configured client credentials.

        Args:
            client_info: Optional OAuth client information to pre-configure.
                         If provided, skips Dynamic Client Registration.
        """
        self._tokens: OAuthToken | None = None
        self._client_info = client_info

    async def get_tokens(self) -> OAuthToken | None:
        """Get stored OAuth tokens.

        Returns:
            Stored OAuth tokens or None if not available
        """
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Store OAuth tokens.

        Args:
            tokens: OAuth tokens to store
        """
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """Get stored OAuth client information.

        Returns:
            Stored OAuth client information or None if not available
        """
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Store OAuth client information.

        Args:
            client_info: OAuth client information to store
        """
        self._client_info = client_info
