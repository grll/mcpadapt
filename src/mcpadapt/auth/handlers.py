"""OAuth handlers for managing authentication flows."""

import threading
import time
import webbrowser
from abc import ABC, abstractmethod
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from typing import List, Tuple, Optional

from pydantic import AnyUrl
from mcp.shared.auth import OAuthClientMetadata as MCPOAuthClientMetadata
from .oauth import OAuthClientMetadata
from .exceptions import (
    OAuthCallbackError,
    OAuthCancellationError,
    OAuthNetworkError,
    OAuthServerError,
    OAuthTimeoutError,
)


class CallbackHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler to capture OAuth callback."""

    def __init__(self, request, client_address, server, callback_data):
        """Initialize with callback data storage."""
        self.callback_data = callback_data
        super().__init__(request, client_address, server)

    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)

        if "code" in query_params:
            self.callback_data["authorization_code"] = query_params["code"][0]
            self.callback_data["state"] = query_params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body>
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <script>setTimeout(() => window.close(), 2000);</script>
            </body>
            </html>
            """)
        elif "error" in query_params:
            self.callback_data["error"] = query_params["error"][0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"""
            <html>
            <body>
                <h1>Authorization Failed</h1>
                <p>Error: {query_params["error"][0]}</p>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """.encode()
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class LocalCallbackServer:
    """Simple server to handle OAuth callbacks."""

    def __init__(self, port: int = 3030):
        """Initialize callback server.

        Args:
            port: Port to listen on for OAuth callbacks
        """
        self.port = port
        self.server = None
        self.thread = None
        self.callback_data = {"authorization_code": None, "state": None, "error": None}

    def _create_handler_with_data(self):
        """Create a handler class with access to callback data."""
        callback_data = self.callback_data

        class DataCallbackHandler(CallbackHandler):
            def __init__(self, request, client_address, server):
                super().__init__(request, client_address, server, callback_data)

        return DataCallbackHandler

    def start(self) -> None:
        """Start the callback server in a background thread.

        Raises:
            OAuthCallbackError: If server cannot be started
        """
        try:
            handler_class = self._create_handler_with_data()
            self.server = HTTPServer(("localhost", self.port), handler_class)
            self.thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.thread.start()
        except OSError as e:
            if e.errno == 48:  # Address already in use
                raise OAuthCallbackError(
                    f"Port {self.port} is already in use. Try using a different port or check if another OAuth flow is running.",
                    context={"port": self.port, "original_error": str(e)},
                )
            else:
                raise OAuthCallbackError(
                    f"Failed to start OAuth callback server on port {self.port}: {str(e)}",
                    context={"port": self.port, "original_error": str(e)},
                )
        except Exception as e:
            raise OAuthCallbackError(
                f"Unexpected error starting OAuth callback server: {str(e)}",
                context={"port": self.port, "original_error": str(e)},
            )

    def stop(self) -> None:
        """Stop the callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1)

    def wait_for_callback(self, timeout: int = 300) -> str:
        """Wait for OAuth callback with timeout.

        Args:
            timeout: Maximum time to wait for callback in seconds

        Returns:
            Authorization code from OAuth callback

        Raises:
            OAuthTimeoutError: If timeout occurs
            OAuthCancellationError: If user cancels authorization
            OAuthServerError: If OAuth server returns an error
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.callback_data["authorization_code"]:
                return self.callback_data["authorization_code"]
            elif self.callback_data["error"]:
                error = self.callback_data["error"]
                context = {"port": self.port, "timeout": timeout}

                # Map common OAuth error codes to specific exceptions
                if error in ["access_denied", "user_cancelled"]:
                    raise OAuthCancellationError(error_details=error, context=context)
                else:
                    # Generic server error for other OAuth errors
                    raise OAuthServerError(server_error=error, context=context)
            time.sleep(0.1)

        raise OAuthTimeoutError(timeout_seconds=timeout, context={"port": self.port})

    def get_state(self) -> str | None:
        """Get the received state parameter.

        Returns:
            OAuth state parameter or None
        """
        return self.callback_data["state"]


class BaseOAuthHandler(ABC):
    """Base class for OAuth authentication handlers.

    Subclasses should implement both the redirect flow (opening authorization URL)
    and callback flow (receiving authorization code).
    """
    
    def __init__(self, client_metadata: OAuthClientMetadata):
        """Initialize handler with OAuth client metadata.
        
        Args:
            client_metadata: OAuth client metadata configuration
        """
        self.client_metadata = client_metadata

    @abstractmethod
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Get redirect URIs for this handler.
        
        Returns:
            List of redirect URIs that this handler can process
        """
        pass
    
    def get_client_metadata(self) -> MCPOAuthClientMetadata:
        """Get complete OAuth client metadata with redirect URIs populated.
        
        Returns:
            Complete OAuth client metadata for MCP usage
        """
        return MCPOAuthClientMetadata(
            client_name=self.client_metadata.client_name,
            redirect_uris=self.get_redirect_uris(),
            grant_types=self.client_metadata.grant_types,
            response_types=self.client_metadata.response_types,
            token_endpoint_auth_method=self.client_metadata.token_endpoint_auth_method,
            scope=self.client_metadata.scope,
            client_uri=self.client_metadata.client_uri,
            logo_uri=self.client_metadata.logo_uri,
            tos_uri=self.client_metadata.tos_uri,
            policy_uri=self.client_metadata.policy_uri,
        )

    @abstractmethod
    async def handle_redirect(self, authorization_url: str) -> None:
        """Handle OAuth redirect to authorization URL.

        Args:
            authorization_url: The OAuth authorization URL to redirect the user to
        """
        pass

    @abstractmethod
    async def handle_callback(self) -> tuple[str, str | None]:
        """Handle OAuth callback and return authorization code and state.

        Returns:
            Tuple of (authorization_code, state) received from OAuth provider

        Raises:
            Exception: If OAuth flow fails or times out
        """
        pass


class LocalBrowserOAuthHandler(BaseOAuthHandler):
    """Default OAuth handler using local browser and callback server.

    Opens authorization URL in the user's default browser and starts a local
    HTTP server to receive the OAuth callback. This is the most user-friendly
    approach for desktop applications.
    """

    def __init__(self, client_metadata: OAuthClientMetadata, callback_port: int = 3030, timeout: int = 300):
        """Initialize the local browser OAuth handler.

        Args:
            client_metadata: OAuth client metadata configuration
            callback_port: Port to run the local callback server on
            timeout: Maximum time to wait for OAuth callback in seconds
        """
        super().__init__(client_metadata)
        self.callback_port = callback_port
        self.timeout = timeout
        self.callback_server: LocalCallbackServer | None = None
    
    def get_redirect_uris(self) -> List[AnyUrl]:
        """Get redirect URIs for this handler.
        
        Returns:
            List of redirect URIs based on callback port
        """
        return [AnyUrl(f"http://localhost:{self.callback_port}/callback")]

    async def handle_redirect(self, authorization_url: str) -> None:
        """Open authorization URL in the user's default browser.

        Args:
            authorization_url: OAuth authorization URL to open

        Raises:
            OAuthNetworkError: If browser cannot be opened
        """
        print(f"Opening OAuth authorization URL: {authorization_url}")

        try:
            success = webbrowser.open(authorization_url)
            if not success:
                print(
                    "Failed to automatically open browser. Please manually open the URL above."
                )
                raise OAuthNetworkError(
                    Exception("Failed to open browser - no suitable browser found"),
                    context={"authorization_url": authorization_url},
                )
        except Exception as e:
            if isinstance(e, OAuthNetworkError):
                raise
            print(
                "Failed to automatically open browser. Please manually open the URL above."
            )
            raise OAuthNetworkError(e, context={"authorization_url": authorization_url})

    async def handle_callback(self) -> tuple[str, str | None]:
        """Start local server and wait for OAuth callback.

        Returns:
            Tuple of (authorization_code, state) from OAuth callback

        Raises:
            OAuthCallbackError: If callback server cannot be started
            OAuthTimeoutError: If callback doesn't arrive within timeout
            OAuthCancellationError: If user cancels authorization
            OAuthServerError: If OAuth server returns an error
        """
        try:
            self.callback_server = LocalCallbackServer(port=self.callback_port)
            self.callback_server.start()

            auth_code = self.callback_server.wait_for_callback(timeout=self.timeout)
            state = self.callback_server.get_state()
            return auth_code, state

        except (
            OAuthTimeoutError,
            OAuthCancellationError,
            OAuthServerError,
            OAuthCallbackError,
        ):
            # Re-raise OAuth-specific exceptions as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise OAuthCallbackError(
                f"Unexpected error during OAuth callback handling: {str(e)}",
                context={
                    "port": self.callback_port,
                    "timeout": self.timeout,
                    "original_error": str(e),
                },
            )
        finally:
            if self.callback_server:
                self.callback_server.stop()
