"""Custom exceptions for OAuth authentication errors."""


class OAuthError(Exception):
    """Base class for all OAuth authentication errors."""

    def __init__(
        self, message: str, error_code: str | None = None, context: dict | None = None
    ):
        """Initialize OAuth error.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (optional)
            context: Additional context about the error (optional)
        """
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}


class OAuthTimeoutError(OAuthError):
    """Raised when OAuth callback doesn't arrive within the specified timeout."""

    def __init__(self, timeout_seconds: int, context: dict | None = None):
        message = (
            f"OAuth authentication timed out after {timeout_seconds} seconds. "
            f"The user may have closed the browser window or the OAuth server may be unreachable. "
            f"Try refreshing the browser or check your network connection."
        )
        super().__init__(message, "oauth_timeout", context)
        self.timeout_seconds = timeout_seconds


class OAuthCancellationError(OAuthError):
    """Raised when the user cancels or denies the OAuth authorization."""

    def __init__(self, error_details: str | None = None, context: dict | None = None):
        base_message = "OAuth authorization was cancelled or denied by the user."
        if error_details:
            message = f"{base_message} Details: {error_details}"
        else:
            message = base_message
        super().__init__(message, "oauth_cancelled", context)
        self.error_details = error_details


class OAuthNetworkError(OAuthError):
    """Raised when network-related issues prevent OAuth completion."""

    def __init__(self, original_error: Exception, context: dict | None = None):
        message = (
            f"OAuth authentication failed due to network error: {str(original_error)}. "
            f"Check your internet connection and try again."
        )
        super().__init__(message, "oauth_network_error", context)
        self.original_error = original_error


class OAuthConfigurationError(OAuthError):
    """Raised when OAuth configuration is invalid or incomplete."""

    def __init__(self, config_issue: str, context: dict | None = None):
        message = f"OAuth configuration error: {config_issue}"
        super().__init__(message, "oauth_config_error", context)
        self.config_issue = config_issue


class OAuthServerError(OAuthError):
    """Raised when the OAuth server returns an error response."""

    def __init__(
        self,
        server_error: str,
        error_description: str | None = None,
        context: dict | None = None,
    ):
        message = f"OAuth server error: {server_error}"
        if error_description:
            message += f" - {error_description}"
        super().__init__(message, "oauth_server_error", context)
        self.server_error = server_error
        self.error_description = error_description


class OAuthCallbackError(OAuthError):
    """Raised when there's an issue with the OAuth callback handling."""

    def __init__(self, callback_issue: str, context: dict | None = None):
        message = f"OAuth callback error: {callback_issue}"
        super().__init__(message, "oauth_callback_error", context)
        self.callback_issue = callback_issue
