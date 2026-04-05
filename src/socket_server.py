import socket
import threading
from typing import Callable

HOST = "127.0.0.1"
PORT = 47832
BUFFER_SIZE = 65536


class SocketServer:
    def __init__(self, on_text_received: Callable[[str], None]):
        self._on_text = on_text_received
        self._server: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((HOST, PORT))
        self._server.listen(5)
        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        while self._running:
            try:
                self._server.settimeout(1.0)
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle(self, conn: socket.socket):
        with conn:
            data = b""
            while chunk := conn.recv(BUFFER_SIZE):
                data += chunk
            text = data.decode("utf-8", errors="replace").strip()
            if text:
                self._on_text(text)

    def stop(self):
        self._running = False
        if self._server:
            self._server.close()


def send_text(text: str) -> bool:
    """Send text to a running Autoreader instance. Returns True on success."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect((HOST, PORT))
            s.sendall(text.encode("utf-8"))
        return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False
