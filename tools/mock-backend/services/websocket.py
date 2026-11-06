"""Minimal RFC 6455 WebSocket server side on top of http.server (stdlib only)."""

import base64
import hashlib
import struct
import threading

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocket:
    def __init__(self, handler):
        self.rfile = handler.rfile
        self.wfile = handler.wfile
        self.write_lock = threading.Lock()
        self.closed = False

    @staticmethod
    def handshake(handler):
        key = handler.headers.get("Sec-WebSocket-Key")
        if not key or "websocket" not in (handler.headers.get("Upgrade") or "").lower():
            return None
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        handler.send_response(101, "Switching Protocols")
        handler.send_header("Upgrade", "websocket")
        handler.send_header("Connection", "Upgrade")
        handler.send_header("Sec-WebSocket-Accept", accept)
        handler.end_headers()
        handler.wfile.flush()
        return WebSocket(handler)

    def _read_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.rfile.read(n - len(data))
            if not chunk:
                raise ConnectionError("closed")
            data += chunk
        return data

    def recv(self):
        """Returns a text message, or None when the connection is closed."""
        message = b""
        while True:
            try:
                b1, b2 = self._read_exact(2)
            except (ConnectionError, OSError, ValueError):
                self.closed = True
                return None
            fin, opcode = b1 & 0x80, b1 & 0x0F
            masked, length = b2 & 0x80, b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length) if length else b""
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:  # close
                self._send_frame(0x8, payload[:2])
                self.closed = True
                return None
            if opcode == 0x9:  # ping
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:  # pong
                continue
            message += payload
            if fin:
                return message.decode("utf-8", errors="replace")

    def _send_frame(self, opcode, payload):
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([n])
        elif n < 65536:
            header += bytes([126]) + struct.pack(">H", n)
        else:
            header += bytes([127]) + struct.pack(">Q", n)
        with self.write_lock:
            self.wfile.write(header + payload)
            self.wfile.flush()

    def send(self, text):
        if self.closed:
            return False
        try:
            self._send_frame(0x1, text.encode("utf-8"))
            return True
        except OSError:
            self.closed = True
            return False
