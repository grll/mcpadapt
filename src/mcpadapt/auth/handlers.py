"""Default OAuth callback and redirect handlers."""

import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


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
        """Start the callback server in a background thread."""
        handler_class = self._create_handler_with_data()
        self.server = HTTPServer(("localhost", self.port), handler_class)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

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
            Exception: If timeout occurs or OAuth error is received
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.callback_data["authorization_code"]:
                return self.callback_data["authorization_code"]
            elif self.callback_data["error"]:
                raise Exception(f"OAuth error: {self.callback_data['error']}")
            time.sleep(0.1)
        raise Exception("Timeout waiting for OAuth callback")

    def get_state(self) -> str | None:
        """Get the received state parameter.
        
        Returns:
            OAuth state parameter or None
        """
        return self.callback_data["state"]


async def default_redirect_handler(authorization_url: str) -> None:
    """Default redirect handler that opens the URL in a browser.
    
    Args:
        authorization_url: OAuth authorization URL to open
    """
    webbrowser.open(authorization_url)


async def default_callback_handler() -> tuple[str, str | None]:
    """Default callback handler that starts local server and waits for OAuth callback.
    
    Returns:
        Tuple of (authorization_code, state)
    """
    callback_server = LocalCallbackServer(port=3030)
    callback_server.start()
    
    try:
        auth_code = callback_server.wait_for_callback(timeout=300)
        state = callback_server.get_state()
        return auth_code, state
    finally:
        callback_server.stop()
