"""Tests for OAuth handler classes."""

import pytest
from unittest.mock import Mock, patch
from mcpadapt.auth.handlers import (
    CallbackHandler,
    LocalCallbackServer,
    LocalBrowserOAuthHandler,
)
from mcpadapt.auth.exceptions import (
    OAuthTimeoutError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthCallbackError,
    OAuthServerError,
)


class TestCallbackHandler:
    """Test OAuth callback HTTP handler."""

    def test_callback_handler_success(self):
        """Test successful OAuth callback handling."""
        callback_data = {"authorization_code": None, "state": None, "error": None}

        # Mock request and server components
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        # Create handler with callback data
        with patch(
            "mcpadapt.auth.handlers.BaseHTTPRequestHandler.__init__"
        ) as mock_init:
            mock_init.return_value = None
            handler = CallbackHandler(
                mock_request, mock_client_address, mock_server, callback_data
            )

            # Mock the required attributes
            handler.path = "/callback?code=test_auth_code&state=test_state"
            handler.send_response = Mock()
            handler.send_header = Mock()
            handler.end_headers = Mock()
            handler.wfile = Mock()
            handler.wfile.write = Mock()

            # Call do_GET
            handler.do_GET()

            # Verify callback data was set
            assert callback_data["authorization_code"] == "test_auth_code"
            assert callback_data["state"] == "test_state"
            assert callback_data["error"] is None

            # Verify HTTP response
            handler.send_response.assert_called_once_with(200)
            handler.send_header.assert_called_with("Content-type", "text/html")
            handler.end_headers.assert_called_once()
            handler.wfile.write.assert_called_once()

    def test_callback_handler_error(self):
        """Test OAuth callback handling with error."""
        callback_data = {"authorization_code": None, "state": None, "error": None}

        # Mock request and server components
        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        with patch(
            "mcpadapt.auth.handlers.BaseHTTPRequestHandler.__init__"
        ) as mock_init:
            mock_init.return_value = None
            handler = CallbackHandler(
                mock_request, mock_client_address, mock_server, callback_data
            )

            # Mock the required attributes
            handler.path = "/callback?error=access_denied&error_description=user_denied"
            handler.send_response = Mock()
            handler.send_header = Mock()
            handler.end_headers = Mock()
            handler.wfile = Mock()
            handler.wfile.write = Mock()

            # Call do_GET
            handler.do_GET()

            # Verify callback data was set
            assert callback_data["authorization_code"] is None
            assert callback_data["state"] is None
            assert callback_data["error"] == "access_denied"

            # Verify HTTP error response
            handler.send_response.assert_called_once_with(400)

    def test_callback_handler_no_params(self):
        """Test callback handler with no parameters."""
        callback_data = {"authorization_code": None, "state": None, "error": None}

        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        with patch(
            "mcpadapt.auth.handlers.BaseHTTPRequestHandler.__init__"
        ) as mock_init:
            mock_init.return_value = None
            handler = CallbackHandler(
                mock_request, mock_client_address, mock_server, callback_data
            )

            handler.path = "/callback"
            handler.send_response = Mock()
            handler.end_headers = Mock()

            handler.do_GET()

            # Verify no data was set
            assert callback_data["authorization_code"] is None
            assert callback_data["state"] is None
            assert callback_data["error"] is None

            # Verify 404 response
            handler.send_response.assert_called_once_with(404)

    def test_callback_handler_log_message_suppressed(self):
        """Test that log messages are suppressed."""
        callback_data = {"authorization_code": None, "state": None, "error": None}

        mock_request = Mock()
        mock_client_address = ("127.0.0.1", 12345)
        mock_server = Mock()

        with patch(
            "mcpadapt.auth.handlers.BaseHTTPRequestHandler.__init__"
        ) as mock_init:
            mock_init.return_value = None
            handler = CallbackHandler(
                mock_request, mock_client_address, mock_server, callback_data
            )

            # log_message should do nothing (return None)
            result = handler.log_message("test %s", "message")
            assert result is None


class TestLocalCallbackServer:
    """Test local OAuth callback server."""

    def test_initialization(self):
        """Test server initialization."""
        server = LocalCallbackServer(port=3030)
        assert server.port == 3030
        assert server.server is None
        assert server.thread is None
        assert server.callback_data == {
            "authorization_code": None,
            "state": None,
            "error": None,
        }

    def test_initialization_default_port(self):
        """Test server initialization with default port."""
        server = LocalCallbackServer()
        assert server.port == 3030

    def test_start_success(self, mock_http_server, mock_threading):
        """Test successful server start."""
        mock_server, mock_server_class = mock_http_server
        mock_thread, mock_thread_class = mock_threading

        server = LocalCallbackServer(port=3030)
        server.start()

        # Verify HTTPServer creation
        mock_server_class.assert_called_once()
        args, kwargs = mock_server_class.call_args
        assert args[0] == ("localhost", 3030)

        # Verify thread creation and start
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

        assert server.server is mock_server
        assert server.thread is mock_thread

    def test_start_port_in_use(self, mock_http_server):
        """Test server start with port already in use."""
        mock_server, mock_server_class = mock_http_server

        # Configure mock to raise "Address already in use" error
        os_error = OSError()
        os_error.errno = 48  # EADDRINUSE
        mock_server_class.side_effect = os_error

        server = LocalCallbackServer(port=3030)

        with pytest.raises(OAuthCallbackError) as exc_info:
            server.start()

        assert "Port 3030 is already in use" in str(exc_info.value)
        assert exc_info.value.context["port"] == 3030

    def test_start_other_os_error(self, mock_http_server):
        """Test server start with other OS error."""
        mock_server, mock_server_class = mock_http_server

        # Configure mock to raise different OS error
        os_error = OSError("Permission denied")
        os_error.errno = 13  # EACCES
        mock_server_class.side_effect = os_error

        server = LocalCallbackServer(port=3030)

        with pytest.raises(OAuthCallbackError) as exc_info:
            server.start()

        assert "Failed to start OAuth callback server" in str(exc_info.value)
        assert "Permission denied" in str(exc_info.value)

    def test_start_unexpected_error(self, mock_http_server):
        """Test server start with unexpected error."""
        mock_server, mock_server_class = mock_http_server

        mock_server_class.side_effect = ValueError("Unexpected error")

        server = LocalCallbackServer(port=3030)

        with pytest.raises(OAuthCallbackError) as exc_info:
            server.start()

        assert "Unexpected error starting OAuth callback server" in str(exc_info.value)

    def test_stop(self, mock_http_server, mock_threading):
        """Test server stop."""
        mock_server, mock_server_class = mock_http_server
        mock_thread, mock_thread_class = mock_threading

        server = LocalCallbackServer(port=3030)
        server.start()

        # Stop the server
        server.stop()

        # Verify shutdown calls
        mock_server.shutdown.assert_called_once()
        mock_server.server_close.assert_called_once()
        mock_thread.join.assert_called_once_with(timeout=1)

    def test_stop_no_server(self):
        """Test stop when no server is running."""
        server = LocalCallbackServer(port=3030)

        # Should not raise an error
        server.stop()

    def test_wait_for_callback_success(self, mock_time):
        """Test successful callback waiting."""
        # Configure mock time to return increasing values
        mock_time.time.side_effect = [0, 1, 2, 3]  # Simulate time progression

        server = LocalCallbackServer(port=3030)
        # Type ignore needed for test - callback_data values can change during runtime
        server.callback_data["authorization_code"] = "test_code"  # type: ignore[assignment]

        result = server.wait_for_callback(timeout=300)

        assert result == "test_code"

    def test_wait_for_callback_timeout(self, mock_time):
        """Test callback waiting timeout."""
        # Configure mock time to simulate timeout
        mock_time.time.side_effect = [0, 100, 200, 300, 400]  # Exceed timeout

        server = LocalCallbackServer(port=3030)

        with pytest.raises(OAuthTimeoutError) as exc_info:
            server.wait_for_callback(timeout=300)

        assert exc_info.value.timeout_seconds == 300
        assert exc_info.value.context["port"] == 3030

    def test_wait_for_callback_access_denied(self, mock_time):
        """Test callback waiting with access denied error."""
        mock_time.time.side_effect = [0, 1]

        server = LocalCallbackServer(port=3030)
        server.callback_data["error"] = "access_denied"  # type: ignore[assignment]

        with pytest.raises(OAuthCancellationError) as exc_info:
            server.wait_for_callback(timeout=300)

        assert exc_info.value.error_details == "access_denied"

    def test_wait_for_callback_server_error(self, mock_time):
        """Test callback waiting with server error."""
        mock_time.time.side_effect = [0, 1]

        server = LocalCallbackServer(port=3030)
        server.callback_data["error"] = "invalid_request"  # type: ignore[assignment]

        with pytest.raises(OAuthServerError) as exc_info:
            server.wait_for_callback(timeout=300)

        assert exc_info.value.server_error == "invalid_request"

    def test_get_state(self):
        """Test getting OAuth state parameter."""
        server = LocalCallbackServer(port=3030)

        # Initially None
        assert server.get_state() is None

        # Set state
        server.callback_data["state"] = "test_state"  # type: ignore[assignment]
        assert server.get_state() == "test_state"


class TestLocalBrowserOAuthHandler:
    """Test local browser OAuth handler."""

    def test_initialization(self):
        """Test handler initialization."""
        handler = LocalBrowserOAuthHandler(callback_port=3030, timeout=300)
        assert handler.callback_port == 3030
        assert handler.timeout == 300
        assert handler.callback_server is None

    def test_initialization_defaults(self):
        """Test handler initialization with defaults."""
        handler = LocalBrowserOAuthHandler()
        assert handler.callback_port == 3030
        assert handler.timeout == 300

    @pytest.mark.asyncio
    async def test_handle_redirect_success(self, mock_webbrowser):
        """Test successful redirect handling."""
        mock_webbrowser.open.return_value = True

        handler = LocalBrowserOAuthHandler()

        # Should not raise
        await handler.handle_redirect("https://example.com/oauth/authorize")

        mock_webbrowser.open.assert_called_once_with(
            "https://example.com/oauth/authorize"
        )

    @pytest.mark.asyncio
    async def test_handle_redirect_browser_fail(self, mock_webbrowser):
        """Test redirect handling when browser fails to open."""
        mock_webbrowser.open.return_value = False

        handler = LocalBrowserOAuthHandler()

        with pytest.raises(OAuthNetworkError) as exc_info:
            await handler.handle_redirect("https://example.com/oauth/authorize")

        assert "Failed to open browser" in str(exc_info.value.original_error)

    @pytest.mark.asyncio
    async def test_handle_redirect_browser_exception(self, mock_webbrowser):
        """Test redirect handling when browser raises exception."""
        mock_webbrowser.open.side_effect = Exception("Browser error")

        handler = LocalBrowserOAuthHandler()

        with pytest.raises(OAuthNetworkError) as exc_info:
            await handler.handle_redirect("https://example.com/oauth/authorize")

        assert "Browser error" in str(exc_info.value.original_error)

    @pytest.mark.asyncio
    async def test_handle_callback_success(self):
        """Test successful callback handling."""
        handler = LocalBrowserOAuthHandler(callback_port=3030, timeout=300)

        # Mock LocalCallbackServer
        mock_server = Mock()
        mock_server.wait_for_callback.return_value = "test_auth_code"
        mock_server.get_state.return_value = "test_state"

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            auth_code, state = await handler.handle_callback()

            assert auth_code == "test_auth_code"
            assert state == "test_state"

            # Verify server lifecycle
            mock_server_class.assert_called_once_with(port=3030)
            mock_server.start.assert_called_once()
            mock_server.wait_for_callback.assert_called_once_with(timeout=300)
            mock_server.get_state.assert_called_once()
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_timeout(self):
        """Test callback handling with timeout."""
        handler = LocalBrowserOAuthHandler(callback_port=3030, timeout=60)

        mock_server = Mock()
        mock_server.wait_for_callback.side_effect = OAuthTimeoutError(60)

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            with pytest.raises(OAuthTimeoutError):
                await handler.handle_callback()

            # Verify cleanup
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_cancellation(self):
        """Test callback handling with user cancellation."""
        handler = LocalBrowserOAuthHandler()

        mock_server = Mock()
        mock_server.wait_for_callback.side_effect = OAuthCancellationError(
            "access_denied"
        )

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            with pytest.raises(OAuthCancellationError):
                await handler.handle_callback()

            # Verify cleanup
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_server_error(self):
        """Test callback handling with server error."""
        handler = LocalBrowserOAuthHandler()

        mock_server = Mock()
        mock_server.wait_for_callback.side_effect = OAuthServerError("invalid_request")

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            with pytest.raises(OAuthServerError):
                await handler.handle_callback()

            # Verify cleanup
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_unexpected_error(self):
        """Test callback handling with unexpected error."""
        handler = LocalBrowserOAuthHandler()

        mock_server = Mock()
        mock_server.start.side_effect = ValueError("Unexpected error")

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            with pytest.raises(OAuthCallbackError) as exc_info:
                await handler.handle_callback()

            assert "Unexpected error during OAuth callback handling" in str(
                exc_info.value
            )
            assert "Unexpected error" in str(exc_info.value)

            # Verify cleanup attempt
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_callback_cleanup_on_success(self):
        """Test that cleanup always happens even on success."""
        handler = LocalBrowserOAuthHandler()

        mock_server = Mock()
        mock_server.wait_for_callback.return_value = "auth_code"
        mock_server.get_state.return_value = "state"

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            await handler.handle_callback()

            # Verify cleanup always happens
            mock_server.stop.assert_called_once()


class TestLocalBrowserOAuthHandlerIntegration:
    """Test integration scenarios for LocalBrowserOAuthHandler."""

    @pytest.mark.asyncio
    async def test_full_oauth_flow_simulation(self, mock_webbrowser):
        """Test complete OAuth flow simulation."""
        mock_webbrowser.open.return_value = True

        handler = LocalBrowserOAuthHandler(callback_port=4040, timeout=120)

        # Mock server for callback
        mock_server = Mock()
        mock_server.wait_for_callback.return_value = "final_auth_code"
        mock_server.get_state.return_value = "final_state"

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            # Step 1: Handle redirect
            await handler.handle_redirect(
                "https://oauth.example.com/authorize?client_id=123"
            )

            # Step 2: Handle callback
            auth_code, state = await handler.handle_callback()

            # Verify results
            assert auth_code == "final_auth_code"
            assert state == "final_state"

            # Verify browser was opened
            mock_webbrowser.open.assert_called_once_with(
                "https://oauth.example.com/authorize?client_id=123"
            )

            # Verify server operations
            mock_server_class.assert_called_once_with(port=4040)
            mock_server.start.assert_called_once()
            mock_server.wait_for_callback.assert_called_once_with(timeout=120)
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_handlers_independent(self, mock_webbrowser):
        """Test that multiple handler instances are independent."""
        mock_webbrowser.open.return_value = True

        handler1 = LocalBrowserOAuthHandler(callback_port=3030, timeout=100)
        handler2 = LocalBrowserOAuthHandler(callback_port=4040, timeout=200)

        # Mock servers
        mock_server1 = Mock()
        mock_server1.wait_for_callback.return_value = "code1"
        mock_server1.get_state.return_value = "state1"

        mock_server2 = Mock()
        mock_server2.wait_for_callback.return_value = "code2"
        mock_server2.get_state.return_value = "state2"

        def server_factory(port):
            if port == 3030:
                return mock_server1
            else:
                return mock_server2

        with patch(
            "mcpadapt.auth.handlers.LocalCallbackServer", side_effect=server_factory
        ):
            # Use handlers independently
            code1, state1 = await handler1.handle_callback()
            code2, state2 = await handler2.handle_callback()

            # Verify independence
            assert code1 == "code1"
            assert state1 == "state1"
            assert code2 == "code2"
            assert state2 == "state2"

            # Verify both servers were used
            mock_server1.start.assert_called_once()
            mock_server1.stop.assert_called_once()
            mock_server2.start.assert_called_once()
            mock_server2.stop.assert_called_once()


class TestHandlerErrorScenarios:
    """Test comprehensive error scenarios across handlers."""

    @pytest.mark.asyncio
    async def test_network_failure_during_redirect(self, mock_webbrowser):
        """Test network failure during redirect."""
        mock_webbrowser.open.side_effect = ConnectionError("Network unreachable")

        handler = LocalBrowserOAuthHandler()

        with pytest.raises(OAuthNetworkError) as exc_info:
            await handler.handle_redirect("https://example.com/oauth")

        assert isinstance(exc_info.value.original_error, ConnectionError)
        assert "Network unreachable" in str(exc_info.value.original_error)

    def test_callback_server_edge_cases(self):
        """Test callback server edge cases."""
        server = LocalCallbackServer(port=0)  # Invalid port

        # Should still initialize
        assert server.port == 0
        assert server.callback_data is not None

    @pytest.mark.asyncio
    async def test_handler_state_consistency(self):
        """Test handler state remains consistent across operations."""
        handler = LocalBrowserOAuthHandler(callback_port=5050, timeout=150)

        # Verify initial state
        assert handler.callback_port == 5050
        assert handler.timeout == 150
        assert handler.callback_server is None

        # Mock callback operation
        mock_server = Mock()
        mock_server.wait_for_callback.return_value = "test_code"
        mock_server.get_state.return_value = None

        with patch("mcpadapt.auth.handlers.LocalCallbackServer") as mock_server_class:
            mock_server_class.return_value = mock_server

            await handler.handle_callback()

            # Verify state is still consistent
            assert handler.callback_port == 5050
            assert handler.timeout == 150
