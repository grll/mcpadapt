"""OAuth token storage and utility implementations."""

from typing import List, Optional, Literal
from pydantic import BaseModel, AnyUrl, AnyHttpUrl
from mcp.client.auth import TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class OAuthClientMetadata(BaseModel):
    """OAuth client metadata without required redirect_uris.

    This is our custom version that allows handlers to manage redirect URIs internally.
    """

    client_name: str
    grant_types: List[Literal["authorization_code", "refresh_token"]] = [
        "authorization_code",
        "refresh_token",
    ]
    response_types: List[Literal["code"]] = ["code"]
    token_endpoint_auth_method: Literal["none", "client_secret_post"] = (
        "client_secret_post"
    )
    redirect_uris: Optional[List[AnyUrl]] = None
    scope: Optional[str] = None
    client_uri: Optional[AnyHttpUrl] = None
    logo_uri: Optional[AnyHttpUrl] = None
    tos_uri: Optional[AnyHttpUrl] = None
    policy_uri: Optional[AnyHttpUrl] = None


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
