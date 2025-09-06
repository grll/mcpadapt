"""Authentication configuration types and protocols for MCPAdapt."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Protocol, Union

from mcp.shared.auth import OAuthClientMetadata


class AuthConfigBase(ABC):
    """Base class for all authentication configurations."""

    @abstractmethod
    def get_auth_type(self) -> str:
        """Return the authentication type identifier."""
        pass


class OAuthConfig(AuthConfigBase):
    """OAuth authentication configuration."""

    def __init__(
        self,
        client_metadata: OAuthClientMetadata | dict[str, Any],
        callback_handler: "CallbackHandler | None" = None,
        redirect_handler: "RedirectHandler | None" = None,
    ):
        """Initialize OAuth configuration.
        
        Args:
            client_metadata: OAuth client metadata or dict representation
            callback_handler: Optional custom callback handler
            redirect_handler: Optional custom redirect handler
        """
        if isinstance(client_metadata, dict):
            self.client_metadata = OAuthClientMetadata.model_validate(client_metadata)
        else:
            self.client_metadata = client_metadata
        self.callback_handler = callback_handler
        self.redirect_handler = redirect_handler

    def get_auth_type(self) -> str:
        """Return OAuth auth type."""
        return "oauth"


class ApiKeyConfig(AuthConfigBase):
    """API Key authentication configuration."""

    def __init__(self, header_name: str, header_value: str):
        """Initialize API key configuration.
        
        Args:
            header_name: Name of the header to send the API key in
            header_value: The API key value
        """
        self.header_name = header_name
        self.header_value = header_value

    def get_auth_type(self) -> str:
        """Return API key auth type."""
        return "api_key"


class BearerAuthConfig(AuthConfigBase):
    """Bearer token authentication configuration."""

    def __init__(self, token: str):
        """Initialize bearer auth configuration.
        
        Args:
            token: The bearer token
        """
        self.token = token

    def get_auth_type(self) -> str:
        """Return bearer auth type."""
        return "bearer"


# Union type for all auth configurations
AuthConfig = Union[OAuthConfig, ApiKeyConfig, BearerAuthConfig]


class CallbackHandler(Protocol):
    """Protocol for OAuth callback handlers."""

    async def __call__(self) -> tuple[str, str | None]:
        """Handle OAuth callback and return authorization code and state.
        
        Returns:
            Tuple of (authorization_code, state)
        """
        ...


class RedirectHandler(Protocol):
    """Protocol for OAuth redirect handlers."""

    async def __call__(self, authorization_url: str) -> None:
        """Handle OAuth redirect by opening authorization URL.
        
        Args:
            authorization_url: The OAuth authorization URL to redirect to
        """
        ...
