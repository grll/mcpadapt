"""Tests for authentication exception classes."""

from mcpadapt.auth.exceptions import (
    OAuthError,
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthConfigurationError,
    OAuthServerError,
    OAuthCallbackError,
)


class TestOAuthError:
    """Test base OAuth error class."""

    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = OAuthError("Test message")
        assert str(error) == "Test message"
        assert error.error_code is None
        assert error.context == {}

    def test_initialization_with_code(self):
        """Test error initialization with error code."""
        error = OAuthError("Test message", "test_code")
        assert str(error) == "Test message"
        assert error.error_code == "test_code"
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test error initialization with context."""
        context = {"key": "value", "number": 42}
        error = OAuthError("Test message", "test_code", context)
        assert str(error) == "Test message"
        assert error.error_code == "test_code"
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthError inherits from Exception."""
        error = OAuthError("Test message")
        assert isinstance(error, Exception)


class TestOAuthTimeoutError:
    """Test OAuth timeout error class."""

    def test_basic_initialization(self):
        """Test basic timeout error initialization."""
        error = OAuthTimeoutError(300)
        expected_message = (
            "OAuth authentication timed out after 300 seconds. "
            "The user may have closed the browser window or the OAuth server may be unreachable. "
            "Try refreshing the browser or check your network connection."
        )
        assert str(error) == expected_message
        assert error.error_code == "oauth_timeout"
        assert error.timeout_seconds == 300
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test timeout error initialization with context."""
        context = {"port": 3030}
        error = OAuthTimeoutError(120, context)
        expected_message = (
            "OAuth authentication timed out after 120 seconds. "
            "The user may have closed the browser window or the OAuth server may be unreachable. "
            "Try refreshing the browser or check your network connection."
        )
        assert str(error) == expected_message
        assert error.error_code == "oauth_timeout"
        assert error.timeout_seconds == 120
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthTimeoutError inherits from OAuthError."""
        error = OAuthTimeoutError(300)
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestOAuthCancellationError:
    """Test OAuth cancellation error class."""

    def test_basic_initialization(self):
        """Test basic cancellation error initialization."""
        error = OAuthCancellationError()
        expected_message = "OAuth authorization was cancelled or denied by the user."
        assert str(error) == expected_message
        assert error.error_code == "oauth_cancelled"
        assert error.error_details is None
        assert error.context == {}

    def test_initialization_with_details(self):
        """Test cancellation error initialization with details."""
        error = OAuthCancellationError("access_denied")
        expected_message = "OAuth authorization was cancelled or denied by the user. Details: access_denied"
        assert str(error) == expected_message
        assert error.error_code == "oauth_cancelled"
        assert error.error_details == "access_denied"
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test cancellation error initialization with context."""
        context = {"port": 3030}
        error = OAuthCancellationError("user_cancelled", context)
        expected_message = "OAuth authorization was cancelled or denied by the user. Details: user_cancelled"
        assert str(error) == expected_message
        assert error.error_code == "oauth_cancelled"
        assert error.error_details == "user_cancelled"
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthCancellationError inherits from OAuthError."""
        error = OAuthCancellationError()
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestOAuthNetworkError:
    """Test OAuth network error class."""

    def test_basic_initialization(self):
        """Test basic network error initialization."""
        original_error = ConnectionError("Network unreachable")
        error = OAuthNetworkError(original_error)
        expected_message = (
            "OAuth authentication failed due to network error: Network unreachable. "
            "Check your internet connection and try again."
        )
        assert str(error) == expected_message
        assert error.error_code == "oauth_network_error"
        assert error.original_error is original_error
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test network error initialization with context."""
        original_error = TimeoutError("Connection timed out")
        context = {"host": "example.com", "port": 443}
        error = OAuthNetworkError(original_error, context)
        expected_message = (
            "OAuth authentication failed due to network error: Connection timed out. "
            "Check your internet connection and try again."
        )
        assert str(error) == expected_message
        assert error.error_code == "oauth_network_error"
        assert error.original_error is original_error
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthNetworkError inherits from OAuthError."""
        original_error = Exception("Test error")
        error = OAuthNetworkError(original_error)
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestOAuthConfigurationError:
    """Test OAuth configuration error class."""

    def test_basic_initialization(self):
        """Test basic configuration error initialization."""
        error = OAuthConfigurationError("Invalid client ID")
        expected_message = "OAuth configuration error: Invalid client ID"
        assert str(error) == expected_message
        assert error.error_code == "oauth_config_error"
        assert error.config_issue == "Invalid client ID"
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test configuration error initialization with context."""
        context = {"client_id": "invalid_id"}
        error = OAuthConfigurationError("Missing redirect URI", context)
        expected_message = "OAuth configuration error: Missing redirect URI"
        assert str(error) == expected_message
        assert error.error_code == "oauth_config_error"
        assert error.config_issue == "Missing redirect URI"
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthConfigurationError inherits from OAuthError."""
        error = OAuthConfigurationError("Test config issue")
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestOAuthServerError:
    """Test OAuth server error class."""

    def test_basic_initialization(self):
        """Test basic server error initialization."""
        error = OAuthServerError("invalid_request")
        expected_message = "OAuth server error: invalid_request"
        assert str(error) == expected_message
        assert error.error_code == "oauth_server_error"
        assert error.server_error == "invalid_request"
        assert error.error_description is None
        assert error.context == {}

    def test_initialization_with_description(self):
        """Test server error initialization with description."""
        error = OAuthServerError(
            "invalid_grant", "The provided authorization grant is invalid"
        )
        expected_message = "OAuth server error: invalid_grant - The provided authorization grant is invalid"
        assert str(error) == expected_message
        assert error.error_code == "oauth_server_error"
        assert error.server_error == "invalid_grant"
        assert error.error_description == "The provided authorization grant is invalid"
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test server error initialization with context."""
        context = {"endpoint": "/oauth/token"}
        error = OAuthServerError("server_error", "Internal server error", context)
        expected_message = "OAuth server error: server_error - Internal server error"
        assert str(error) == expected_message
        assert error.error_code == "oauth_server_error"
        assert error.server_error == "server_error"
        assert error.error_description == "Internal server error"
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthServerError inherits from OAuthError."""
        error = OAuthServerError("test_error")
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestOAuthCallbackError:
    """Test OAuth callback error class."""

    def test_basic_initialization(self):
        """Test basic callback error initialization."""
        error = OAuthCallbackError("Port already in use")
        expected_message = "OAuth callback error: Port already in use"
        assert str(error) == expected_message
        assert error.error_code == "oauth_callback_error"
        assert error.callback_issue == "Port already in use"
        assert error.context == {}

    def test_initialization_with_context(self):
        """Test callback error initialization with context."""
        context = {"port": 3030, "pid": 12345}
        error = OAuthCallbackError("Failed to start server", context)
        expected_message = "OAuth callback error: Failed to start server"
        assert str(error) == expected_message
        assert error.error_code == "oauth_callback_error"
        assert error.callback_issue == "Failed to start server"
        assert error.context == context

    def test_inheritance(self):
        """Test that OAuthCallbackError inherits from OAuthError."""
        error = OAuthCallbackError("Test callback issue")
        assert isinstance(error, OAuthError)
        assert isinstance(error, Exception)


class TestExceptionContext:
    """Test exception context handling across all error types."""

    def test_context_preservation(self):
        """Test that context is preserved across different error types."""
        context = {"request_id": "req_123", "timestamp": 1234567890}

        errors = [
            OAuthError("Test", "code", context),
            OAuthTimeoutError(300, context),
            OAuthCancellationError("details", context),
            OAuthNetworkError(Exception("test"), context),
            OAuthConfigurationError("issue", context),
            OAuthServerError("error", "desc", context),
            OAuthCallbackError("issue", context),
        ]

        for error in errors:
            assert error.context == context
            assert error.context["request_id"] == "req_123"
            assert error.context["timestamp"] == 1234567890

    def test_empty_context_default(self):
        """Test that context defaults to empty dict when not provided."""
        errors = [
            OAuthError("Test"),
            OAuthTimeoutError(300),
            OAuthCancellationError(),
            OAuthNetworkError(Exception("test")),
            OAuthConfigurationError("issue"),
            OAuthServerError("error"),
            OAuthCallbackError("issue"),
        ]

        for error in errors:
            assert error.context == {}
            assert isinstance(error.context, dict)
