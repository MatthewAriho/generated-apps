"""Network connectivity checker using a socket probe."""
import socket


def is_online(host: str = "8.8.8.8", port: int = 53, timeout: float = 3.0) -> bool:
    """Return True if the device can reach the internet."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except OSError:
        return False
