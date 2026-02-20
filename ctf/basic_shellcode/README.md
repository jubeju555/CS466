# Basic Shellcode Challenge

Stack-based buffer overflow with shellcode injection.

## Quick Start

```bash
python3 exploit.py
```

## Challenge Details

- **Type:** Buffer Overflow + Shellcode Injection
- **Architecture:** 32-bit x86
- **Protections:** NX disabled (executable stack), no ASLR
- **Server:** moa6.eecs.utk.edu:6022
- **Binary:** `shellcode`

## Solution Summary

1. Buffer overflow in `gets()` function
2. Stack is executable (RWE)
3. Leaked buffer address: `0xffffdbbc`
4. Offset to return address: 40 bytes
5. Inject shellcode that executes `/bin/sh`
6. Overwrite return address to jump back to buffer
7. Send commands to spawned shell to get flag

## Files

- `shellcode` - Challenge binary
- `exploit.py` - Working exploit script
- `walkthrough.md` - Detailed solution walkthrough

## Flag

```
cosc466-flag-{auCe5uaQCQxuqn}
```

For a detailed walkthrough, see [walkthrough.md](walkthrough.md).
