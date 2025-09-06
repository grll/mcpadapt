"""Authentication provider classes for MCPAdapt."""

from typing import Any


class ApiKeyAuthProvider:
    """Simple API key authentication provider."""

    def __init__(self, header_name: str, header_value: str):
        """Initialize with API key configuration.
        
        Args:
            header_name: Name of the header to send the API key in
            header_value: The API key value
        """
        self.header_name = header_name
        self.header_value = header_value

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.
        
        Returns:
            Dictionary of headers to add to requests
        """
        return {self.header_name: self.header_value}


class BearerAuthProvider:
    """Simple Bearer token authentication provider."""

    def __init__(self, token: str):
        """Initialize with Bearer token configuration.
        
        Args:
            token: The bearer token
        """
        self.token = token

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers.
        
        Returns:
            Dictionary of headers to add to requests
        """
        return {"Authorization": f"Bearer {self.token}"}


def get_auth_headers(auth_provider: Any) -> dict[str, str]:
    """Get authentication headers from provider.
    
    Args:
        auth_provider: Authentication provider instance
        
    Returns:
        Dictionary of headers to add to requests
    """
    if isinstance(auth_provider, (ApiKeyAuthProvider, BearerAuthProvider)):
        return auth_provider.get_headers()
    return {}
