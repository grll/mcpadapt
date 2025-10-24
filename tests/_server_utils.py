import os
import socket
import subprocess
import time
from typing import Tuple


def _reserve_port() -> int:
    """Reserve an available localhost TCP port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            # Allow the port to be reused immediately after closing
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return sock.getsockname()[1]
    except OSError as exc:
        raise RuntimeError(f"Unable to reserve local TCP port: {exc}") from exc


def launch_mcp_server(script: str) -> Tuple[subprocess.Popen[str], int]:
    """Launch an MCP server subprocess and return the process and bound port.

    Raises:
        RuntimeError: If the subprocess exits before becoming ready.
    """
    port = _reserve_port()
    env = {**os.environ, "MCP_TEST_PORT": str(port)}

    process = subprocess.Popen(  # noqa: S603
        ["python", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    # Give the server a moment to bind and report startup issues
    time.sleep(1)

    if process.poll() is not None:
        stdout, stderr = process.communicate()
        raise RuntimeError(
            "Failed to start MCP server subprocess. "
            f"Exit code: {process.returncode}\nStdout:\n{stdout}\nStderr:\n{stderr}"
        )

    for attempt in range(3):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError as exc:
            if attempt == 2:
                stdout, stderr = terminate_mcp_server(process)
                raise RuntimeError(
                    "MCP server subprocess is not accepting connections. "
                    f"Attempted to connect to 127.0.0.1:{port} but received: {exc}\n"
                    f"Stdout:\n{stdout}\nStderr:\n{stderr}"
                ) from exc
            time.sleep(0.2)

    return process, port


def terminate_mcp_server(process: subprocess.Popen[str]) -> Tuple[str, str]:
    """Terminate the subprocess and return captured stdout/stderr."""
    if process.poll() is None:
        process.kill()

    stdout, stderr = process.communicate()

    return stdout, stderr
